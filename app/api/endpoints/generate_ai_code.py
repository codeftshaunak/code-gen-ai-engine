"""Generate AI code streaming endpoint."""

import json
import logging
import time
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Request, Header
from sse_starlette.sse import EventSourceResponse

from app.models.api_models import GenerateCodeRequest, StreamEvent, ErrorResponse, SupabaseProjectInfo
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
from app.utils.supabase_provisioner import supabase_provisioner
from app.utils.project_type_detector import detect_project_type
from app.utils.code_parser import extract_sql_migrations


# Initialize logger
logger = logging.getLogger(__name__)

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

        # Detect project type if not explicitly specified
        is_fullstack = request_data.is_fullstack
        supabase_config = None
        
        # In edit mode, retrieve fullstack status and config from conversation state
        if request_data.is_edit:
            # Check if stored in conversation context
            if conversation_state.context.is_fullstack and conversation_state.context.supabase_config:
                is_fullstack = True
                supabase_config = conversation_state.context.supabase_config
                logger.info(f"Edit mode: Retrieved Supabase config from conversation state for project {supabase_config.get('project_id')}")
            # Fallback to request data if available
            elif request_data.supabase_config:
                supabase_config = request_data.supabase_config.dict(by_alias=True)
                is_fullstack = True
                logger.info(f"Edit mode: Using Supabase config from request")
            else:
                logger.info("Edit mode: No Supabase config found, treating as frontend-only")
        elif not is_fullstack:
            # Auto-detect project type for new projects (only in non-edit mode)
            try:
                detection_result = await detect_project_type(request_data.prompt)
                is_fullstack = detection_result.get("type") == "fullstack"
                
                if is_fullstack:
                    logger.info(f"Detected full-stack project: {detection_result.get('reasoning')}")
            except Exception as e:
                logger.error(f"Project type detection failed: {str(e)}")
                # Default to frontend-only on error
                is_fullstack = False

        # Create event generator
        async def event_generator() -> AsyncGenerator[dict, None]:
            """Generate SSE events for code generation."""
            nonlocal is_fullstack, supabase_config
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

                # Provision Supabase project if full-stack
                if is_fullstack and not supabase_config:
                    try:
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "status",
                                "message": "Setting up Supabase backend..."
                            })
                        }

                        # Get organization
                        orgs = await supabase_provisioner.get_organizations()
                        if not orgs:
                            raise Exception("No Supabase organizations found")
                        
                        org_id = orgs[0].get("id")
                        logger.info(f"Using Supabase organization: {org_id}")

                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "status",
                                "message": "Creating Supabase project..."
                            })
                        }

                        # Create project (use sanitized prompt as name)
                        project_name = f"upfounder-{project_id}"
                        supabase_project = await supabase_provisioner.create_project(
                            org_id=org_id,
                            name=project_name
                        )

                        project_ref = supabase_project.get("id") or supabase_project.get("ref")
                        logger.info(f"Created Supabase project: {project_ref}")

                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "status",
                                "message": "Retrieving Supabase API keys..."
                            })
                        }

                        # Get API keys
                        keys = await supabase_provisioner.get_api_keys(project_ref)
                        
                        supabase_config = {
                            "project_id": project_ref,
                            "api_url": f"https://{project_ref}.supabase.co",
                            "anon_key": keys.get("anon") or keys.get("publishable", ""),
                            "publishable_key": keys.get("publishable") or keys.get("anon", "")
                        }

                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "supabase_setup",
                                "message": f"Supabase project created: {project_ref}",
                                "supabaseConfig": supabase_config
                            })
                        }
                        
                        # Store fullstack metadata in conversation state for future edits
                        conversation_state.context.is_fullstack = True
                        conversation_state.context.supabase_config = supabase_config
                        conversation_manager.update(project_id, conversation_state)
                        logger.info("Stored fullstack metadata in conversation state")

                    except Exception as supabase_error:
                        logger.error(f"Supabase provisioning failed: {str(supabase_error)}")
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "warning",
                                "message": f"Supabase setup failed: {str(supabase_error)}. Continuing with frontend-only."
                            })
                        }
                        # Fall back to frontend-only
                        is_fullstack = False
                        supabase_config = None

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
                    user_preferences=user_preferences,
                    is_fullstack=is_fullstack,
                    supabase_config=supabase_config
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
                chunk_count = 0

                try:
                    async for chunk in ai_provider.stream_with_retry(
                        model=model,
                        system_prompt=system_prompt,
                        user_prompt=request_data.prompt
                    ):
                        # Accumulate generated code and response
                        generated_code += chunk
                        assistant_response += chunk
                        chunk_count += 1

                        # Send stream event
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "stream",
                                "text": chunk,
                                "raw": True
                            })
                        }

                        # Send keepalive to prevent timeout (every 500 chars)
                        if len(generated_code) % 500 == 0:
                            yield {"event": "ping", "data": ""}

                    # Log successful streaming
                    logger.info(f"Streaming completed: {chunk_count} chunks, {len(generated_code)} chars")

                except Exception as stream_error:
                    logger.error(f"Streaming error: {str(stream_error)}", exc_info=True)
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "error",
                            "error": f"Streaming failed: {str(stream_error)}"
                        })
                    }
                    raise

                # Parse generated code for files and packages
                files_generated = generated_code.count("<file path=")
                packages = _extract_packages(generated_code)
                
                # Execute SQL migrations if full-stack (works in both edit and new generation modes)
                sql_migrations = []
                if is_fullstack and supabase_config:
                    try:
                        sql_migrations = extract_sql_migrations(generated_code)
                        
                        if sql_migrations:
                            mode_label = "edit" if request_data.is_edit else "new"
                            logger.info(f"Found {len(sql_migrations)} SQL migration(s) to execute (mode: {mode_label})")
                            
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "status",
                                    "message": f"📊 Executing {len(sql_migrations)} SQL migration(s)..."
                                })
                            }
                            
                            for idx, migration in enumerate(sql_migrations, 1):
                                try:
                                    logger.info(f"Executing migration {idx}/{len(sql_migrations)}: {migration['filename']}")
                                    
                                    # Execute SQL on Supabase
                                    result = await supabase_provisioner.execute_sql(
                                        project_id=supabase_config["project_id"],
                                        sql_query=migration["content"]
                                    )
                                    
                                    logger.info(f"Migration executed successfully: {migration['filename']}")
                                    
                                    # Save migration file to project (will be handled by apply_ai_code)
                                    # Add migration file to generated code for persistence
                                    migration_path = f"src/supabase/migrations/{migration['filename']}"
                                    migration_file_tag = f'<file path="{migration_path}">{migration["content"]}</file>'
                                    generated_code += "\n" + migration_file_tag
                                    files_generated += 1
                                    
                                    yield {
                                        "event": "message",
                                        "data": json.dumps({
                                            "type": "status",
                                            "message": f"✅ Executed & saved migration: {migration['filename']}"
                                        })
                                    }
                                except Exception as sql_error:
                                    logger.error(f"SQL migration failed for {migration['filename']}: {str(sql_error)}")
                                    yield {
                                        "event": "message",
                                        "data": json.dumps({
                                            "type": "warning",
                                            "message": f"⚠️ Migration {migration['filename']} failed: {str(sql_error)}"
                                        })
                                    }
                        else:
                            logger.info("No SQL migrations found in generated code")
                    except Exception as e:
                        logger.error(f"SQL migration extraction failed: {str(e)}")
                elif is_fullstack and not supabase_config:
                    logger.warning("Full-stack project detected but no Supabase config available - SQL migrations skipped")
                elif not is_fullstack:
                    logger.debug("Frontend-only project detected - no SQL migrations to execute")
                
                # Add @supabase/supabase-js if full-stack
                if is_fullstack and "@supabase/supabase-js" not in packages:
                    packages.append("@supabase/supabase-js")

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
                completion_data = {
                    "type": "complete",
                    "generatedCode": generated_code,
                    "explanation": "Code generated successfully!",
                    "files": files_generated,
                    "model": model,
                    "packagesToInstall": packages,
                    "warnings": []
                }
                
                # Add Supabase info if full-stack
                if is_fullstack and supabase_config:
                    completion_data["supabaseConfig"] = supabase_config
                    completion_data["sqlMigrations"] = len(sql_migrations)
                    completion_data["isFullstack"] = True
                
                yield {
                    "event": "message",
                    "data": json.dumps(completion_data)
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

        # Return SSE response with proper headers
        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Content-Encoding": "none",  # Prevent compression
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Project-Id"
            },
            ping=15  # Send ping every 15 seconds to keep connection alive
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
