"""
Generate AI Code Stream Endpoint
Generates code from prompts using streaming AI models
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncIterator
import json

from app.models.api_models import GenerateCodeRequest
from app.core.ai_provider import ai_provider
from app.core.app_state_manager import app_state_manager
from app.utils.project_utils import get_project_id
from app.models.conversation import Message
from app.utils.code_parser import detect_packages_from_code
from datetime import datetime

router = APIRouter()


async def generate_stream(
    request: GenerateCodeRequest,
    project_id: str
) -> AsyncIterator[str]:
    """
    Generate code with Server-Sent Events streaming

    Yields SSE formatted events with code generation progress
    """
    try:
        # Get project context
        context = app_state_manager.for_project(project_id)
        conversation_state = context.get_conversation_state()

        # Add user message to conversation
        user_message = Message(
            role="user",
            content=request.prompt,
            timestamp=datetime.now()
        )
        conversation_state.messages.append(user_message)

        # Build context for AI
        ai_context = request.context or {}
        if conversation_state.messages:
            # Include last few messages for context
            recent_messages = conversation_state.messages[-5:]
            ai_context["conversation_history"] = [
                {"role": msg.role, "content": msg.content}
                for msg in recent_messages
            ]

        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'message': 'Generating code...'})}\n\n"

        # Stream code generation from AI
        full_response = ""
        async for chunk in ai_provider.generate_code_stream(
            prompt=request.prompt,
            model=request.model,
            context=ai_context
        ):
            full_response += chunk

            # Send chunk event
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        # Parse the response to detect files and packages
        files = {}
        # Simple detection: look for code blocks
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', full_response, re.DOTALL)
        if code_blocks:
            # For simplicity, treat first code block as main file
            files["src/generated.jsx"] = code_blocks[0]

        # Detect packages from generated code
        packages = detect_packages_from_code(files)

        # Add assistant message to conversation
        assistant_message = Message(
            role="assistant",
            content=full_response,
            timestamp=datetime.now(),
            packages_installed=packages
        )
        conversation_state.messages.append(assistant_message)

        # Send packages detected event
        if packages:
            yield f"data: {json.dumps({'type': 'packages', 'packages': packages})}\n\n"

        # Send completion event
        yield f"data: {json.dumps({'type': 'complete', 'response': full_response})}\n\n"

    except Exception as e:
        error_data = {
            'type': 'error',
            'error': str(e),
            'message': 'Code generation failed'
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post(
    "/generate-ai-code-stream",
    summary="Generate AI Code (Streaming)",
    description="""
    Generate code from prompts using streaming AI models.

    **Features:**
    - Supports multiple AI providers (Anthropic, OpenAI, Google, Groq)
    - Real-time streaming of generated code
    - Automatic package detection from imports
    - Conversation context tracking

    **Request Headers:**
    - `X-Project-Id`: Required project identifier

    **Response:**
    Server-Sent Events stream with:
    - `start`: Generation started
    - `chunk`: Code chunk generated
    - `packages`: Detected packages
    - `complete`: Generation completed
    - `error`: Error occurred
    """
)
async def generate_ai_code_stream(
    request: GenerateCodeRequest,
    project_id: str = Depends(get_project_id)
):
    """Generate code with streaming response"""
    return StreamingResponse(
        generate_stream(request, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
