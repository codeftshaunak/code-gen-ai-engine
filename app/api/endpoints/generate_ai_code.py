"""Generate AI code streaming endpoint."""

import json
import time
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Request, Header
from sse_starlette.sse import EventSourceResponse

from app.models.api_models import GenerateCodeRequest, StreamEvent, ErrorResponse
from app.models.conversation import (
    conversation_manager,
    ConversationMessage,
    ConversationEdit,
    ProjectEvolution
)
from app.core.ai_provider import ai_provider
from app.core.prompt_builder import prompt_builder
from app.utils.user_preferences import analyze_user_preferences
from app.config.settings import settings
from app.utils.project_state import project_state_manager


router = APIRouter()


@router.post("/generate-ai-code-stream")
async def generate_ai_code_stream(
    request: Request,
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Stream AI-generated code based on user prompt.

    This endpoint streams code generation in real-time using Server-Sent Events (SSE).
    It supports multiple AI providers and handles retries for transient failures.

    Request Body:
        - prompt (str): User's request describing what code to generate
        - model (str, optional): AI model to use (e.g., 'anthropic/claude-4.5-sonnet')
        - context (RequestContext, optional): Current application context
        - isEdit (bool, optional): Whether this is an edit to existing code

    Response:
        Server-Sent Events stream with the following event types:
        - status: Progress updates
        - stream: Raw AI output chunks
        - conversation: AI explanations and comments
        - component: Component creation notifications
        - package: Package detection notifications
        - warning: Warning messages
        - complete: Final summary with generated code
        - error: Error information

    Example:
        ```python
        import requests

        response = requests.post(
            'http://localhost:3100/api/generate-ai-code-stream',
            json={
                'prompt': 'Create a hero section with dark background',
                'model': 'anthropic/claude-3-5-sonnet-20241022',
                'isEdit': False
            },
            stream=True
        )

        for line in response.iter_lines():
            if line.startswith(b'data: '):
                event = json.loads(line[6:])
                print(event)
        ```
    """
    try:
        # Parse request body
        body = await request.json()
        request_data = GenerateCodeRequest(**body)

        # Validate prompt
        if not request_data.prompt or not request_data.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt is required and cannot be empty")

        # Get or create conversation state for this project
        project_id = x_project_id or "default"
        conversation_state = conversation_manager.get_or_create(project_id)

        # Add user message to conversation history
        user_message = ConversationMessage(
            id=f"msg-{int(time.time() * 1000)}",
            role="user",
            content=request_data.prompt,
            timestamp=int(time.time() * 1000),
            metadata={"sandboxId": request_data.context.sandbox_id if request_data.context else None}
        )
        conversation_state.context.messages.append(user_message)

        # Clean up old messages (keep last 15 of 20)
        conversation_manager.cleanup_messages(project_id, max_messages=20, keep_last=15)

        # Clean up old edits (keep last 8 of 10)
        conversation_manager.cleanup_edits(project_id, max_edits=10, keep_last=8)

        # Analyze user preferences from conversation history
        user_preferences = analyze_user_preferences(conversation_state.context.messages)
        conversation_state.context.user_preferences = user_preferences

        # Update conversation state
        conversation_manager.update(project_id, conversation_state)

        # Get model (use default if not specified)
        model = request_data.model or settings.DEFAULT_AI_MODEL

        # Create event generator
        async def event_generator() -> AsyncGenerator[dict, None]:
            """Generate SSE events for code generation."""
            assistant_response = ""
            try:
                # Send initial status
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "status",
                        "message": "Initializing AI code generation..."
                    })
                }

                # Get existing files from project state
                existing_files = project_state_manager.get_all_files(project_id)

                # Merge with any files from request context
                if request_data.context and request_data.context.current_files:
                    # Merge request context files with existing files from state
                    existing_files.update(request_data.context.current_files)

                # Update request context with complete file list
                if request_data.context:
                    request_data.context.current_files = existing_files
                else:
                    # Create context if it doesn't exist
                    from app.models.api_models import RequestContext
                    request_data.context = RequestContext(current_files=existing_files)

                # Build system prompt with conversation context
                system_prompt = prompt_builder.build_system_prompt(
                    user_prompt=request_data.prompt,
                    is_edit=request_data.is_edit,
                    context=request_data.context,
                    conversation_state=conversation_state,
                    user_preferences=user_preferences
                )

                # Send status update
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "status",
                        "message": f"Connecting to {model.split('/')[0]} AI provider..."
                    })
                }

                # Stream AI response
                generated_code = ""
                async for chunk in ai_provider.stream_with_retry(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=request_data.prompt
                ):
                    # Accumulate generated code and response
                    generated_code += chunk
                    assistant_response += chunk

                    # Send stream event
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "stream",
                            "text": chunk,
                            "raw": True
                        })
                    }

                    # Send keepalive to prevent timeout
                    if len(generated_code) % 500 == 0:  # Every ~500 characters
                        yield {"event": "ping", "data": ""}

                # Parse generated code for files and packages
                files_generated = generated_code.count("<file path=")
                packages = _extract_packages(generated_code)

                # Record this interaction in conversation state
                assistant_message = ConversationMessage(
                    id=f"msg-{int(time.time() * 1000)}",
                    role="assistant",
                    content=assistant_response,
                    timestamp=int(time.time() * 1000),
                    metadata={
                        "model": model,
                        "filesGenerated": files_generated,
                        "packagesDetected": packages
                    }
                )
                conversation_state.context.messages.append(assistant_message)

                # Record edit if this was an edit operation
                if request_data.is_edit:
                    target_files = _extract_file_paths(generated_code)
                    edit_type = "targeted" if user_preferences.edit_style == "targeted" else "comprehensive"

                    edit_record = ConversationEdit(
                        timestamp=int(time.time() * 1000),
                        userRequest=request_data.prompt,
                        editType=edit_type,
                        targetFiles=target_files,
                        confidence=1.0,
                        outcome="success"
                    )
                    conversation_state.context.edits.append(edit_record)

                # Update conversation state
                conversation_manager.update(project_id, conversation_state)

                # Send completion event
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "complete",
                        "generatedCode": generated_code,
                        "explanation": "Code generated successfully!",
                        "files": files_generated,
                        "model": model,
                        "packagesToInstall": packages,
                        "warnings": []
                    })
                }

            except HTTPException as he:
                # HTTP exceptions are already formatted
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "error",
                        "error": he.detail
                    })
                }

            except Exception as e:
                # Log the error (in production, use proper logging)
                error_message = f"Code generation failed: {str(e)}"

                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "error",
                        "error": error_message
                    })
                }

        # Return SSE response
        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )

    except ValueError as ve:
        # Pydantic validation errors
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _extract_packages(generated_code: str) -> list[str]:
    """
    Extract npm packages from generated code.

    Looks for import statements and extracts package names.

    Args:
        generated_code: The generated code string

    Returns:
        List of package names to install
    """
    packages = set()

    # Common packages that might be imported
    lines = generated_code.split('\n')
    for line in lines:
        line = line.strip()

        # Check for import statements
        if line.startswith('import ') and 'from ' in line:
            # Extract package name from: import X from 'package-name'
            try:
                parts = line.split("from ")
                if len(parts) > 1:
                    package_part = parts[1].strip().strip(';').strip('"').strip("'")

                    # Skip relative imports
                    if not package_part.startswith('.') and not package_part.startswith('/'):
                        # Handle scoped packages and subpaths
                        if package_part.startswith('@'):
                            # @scope/package or @scope/package/subpath
                            parts = package_part.split('/')
                            if len(parts) >= 2:
                                packages.add(f"{parts[0]}/{parts[1]}")
                        else:
                            # Regular package or package/subpath
                            package_name = package_part.split('/')[0]
                            # Skip built-in modules
                            if package_name not in ['react', 'react-dom']:
                                packages.add(package_name)
            except Exception:
                # Skip malformed imports
                continue

    return sorted(list(packages))


def _extract_file_paths(generated_code: str) -> list[str]:
    """
    Extract file paths from generated code.

    Looks for <file path="..."> tags.

    Args:
        generated_code: The generated code string

    Returns:
        List of file paths
    """
    import re

    file_paths = []
    pattern = r'<file path="([^"]+)">'
    matches = re.findall(pattern, generated_code)

    for match in matches:
        file_paths.append(match)

    return file_paths
