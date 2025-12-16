"""
Apply AI Code Stream Endpoint
Applies AI-generated code to sandbox with real-time streaming
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncIterator
import json

from app.models.api_models import ApplyCodeRequest
from app.core.app_state_manager import app_state_manager
from app.utils.project_utils import get_project_id
from app.utils.code_parser import parse_ai_response, normalize_file_path
from app.models.conversation import EditHistory
from datetime import datetime

router = APIRouter()


async def apply_code_stream(
    request: ApplyCodeRequest,
    project_id: str
) -> AsyncIterator[str]:
    """
    Apply AI-generated code to sandbox with SSE streaming

    Steps:
    1. Parse AI response to extract files, packages, commands
    2. Install packages
    3. Create/update files
    4. Execute commands
    5. Update conversation state
    """
    try:
        # Get project context
        context = app_state_manager.for_project(project_id)
        sandbox = context.get_sandbox_provider(request.sandbox_id)

        if not sandbox:
            raise HTTPException(
                status_code=400,
                detail="No sandbox found. Please create a sandbox first."
            )

        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'message': 'Applying code changes...'})}\n\n"

        # Parse AI response
        parsed = parse_ai_response(request.response)
        files = parsed["files"]
        packages = list(set(parsed["packages"] + request.packages))
        commands = parsed["commands"]

        yield f"data: {json.dumps({'type': 'parsed', 'fileCount': len(files), 'packageCount': len(packages), 'commandCount': len(commands)})}\n\n"

        # Step 1: Install packages
        if packages:
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'packages', 'message': f'Installing {len(packages)} packages...'})}\n\n"

            installed_packages = []
            async for output in sandbox.install_packages(packages):
                yield f"data: {json.dumps({'type': 'package_output', 'output': output})}\n\n"
                # Track installed packages
                for pkg in packages:
                    if pkg in output and pkg not in installed_packages:
                        installed_packages.append(pkg)

            yield f"data: {json.dumps({'type': 'packages_complete', 'installed': installed_packages})}\n\n"

        # Step 2: Create/update files
        if files:
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'files', 'message': f'Creating {len(files)} files...'})}\n\n"

            files_created = []
            for file_path, content in files.items():
                # Normalize file path
                normalized_path = normalize_file_path(file_path)

                try:
                    # Write file to sandbox
                    await sandbox.write_file(normalized_path, content)

                    # Update file cache
                    context.update_file_cache(normalized_path, content)

                    files_created.append(normalized_path)

                    yield f"data: {json.dumps({'type': 'file_created', 'path': normalized_path})}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'type': 'file_error', 'path': normalized_path, 'error': str(e)})}\n\n"

            yield f"data: {json.dumps({'type': 'files_complete', 'created': files_created})}\n\n"

        # Step 3: Execute commands
        if commands:
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'commands', 'message': f'Executing {len(commands)} commands...'})}\n\n"

            for cmd in commands:
                yield f"data: {json.dumps({'type': 'command_start', 'command': cmd})}\n\n"

                try:
                    async for output in sandbox.run_command(cmd):
                        yield f"data: {json.dumps({'type': 'command_output', 'output': output})}\n\n"

                    yield f"data: {json.dumps({'type': 'command_complete', 'command': cmd})}\n\n"

                except Exception as e:
                    yield f"data: {json.dumps({'type': 'command_error', 'command': cmd, 'error': str(e)})}\n\n"

        # Step 4: Update conversation state
        conversation_state = context.get_conversation_state()

        edit_history = EditHistory(
            timestamp=datetime.now(),
            files_modified=list(files.keys()),
            edit_type="apply" if request.is_edit else "create",
            prompt="Applied AI-generated code",
            outcome="success"
        )
        conversation_state.edit_history.append(edit_history)

        # Send completion event
        result = {
            'type': 'complete',
            'message': 'Code applied successfully',
            'files_created': len(files),
            'packages_installed': len(packages),
            'commands_executed': len(commands)
        }
        yield f"data: {json.dumps(result)}\n\n"

    except Exception as e:
        error_data = {
            'type': 'error',
            'error': str(e),
            'message': 'Failed to apply code'
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post(
    "/apply-ai-code-stream",
    summary="Apply AI Code (Streaming)",
    description="""
    Apply AI-generated code to the sandbox with real-time streaming updates.

    **Features:**
    - Parses AI response (XML/Markdown formats)
    - Installs packages automatically
    - Creates/updates files with normalization
    - Executes shell commands
    - Streams progress updates via SSE
    - Tracks file changes in conversation state

    **Supported AI Response Formats:**
    - XML tags: `<file path="...">...</file>`, `<package>...</package>`, `<command>...</command>`
    - Markdown code blocks with file paths: ` ```jsx:src/App.jsx `

    **Request Headers:**
    - `X-Project-Id`: Required project identifier

    **Response:**
    Server-Sent Events stream with progress updates
    """
)
async def apply_ai_code_stream(
    request: ApplyCodeRequest,
    project_id: str = Depends(get_project_id)
):
    """Apply AI-generated code with streaming response"""
    return StreamingResponse(
        apply_code_stream(request, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
