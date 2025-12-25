"""Apply AI-generated code streaming endpoint."""

import json
import logging
from typing import AsyncGenerator, Dict, Set
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.api_models import ApplyCodeRequest, ApplyCodeResults
from app.utils.code_parser import (
    parse_ai_response,
    extract_packages_from_code,
    normalize_file_path,
    strip_css_imports,
    fix_tailwind_classes
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/apply-ai-code-stream")
async def apply_ai_code_stream(request_data: ApplyCodeRequest):
    """
    Apply AI-generated code to files with streaming progress.

    This endpoint parses AI-generated code, extracts files and packages,
    and provides real-time progress updates via Server-Sent Events.

    Note: This is a simplified version that parses and validates the code
    without actual file writing (no sandbox integration yet).

    Request Body:
        - response (str): AI-generated response containing file blocks
        - isEdit (bool, optional): Enable Morph Fast Apply mode
        - packages (list, optional): Additional packages to install
        - sandboxId (str, optional): Specific sandbox ID to use

    Response:
        Server-Sent Events stream with progress updates

    Example:
        ```python
        import requests
        import json

        response = requests.post(
            'http://localhost:3100/api/apply-ai-code-stream',
            json={
                'response': '<file path="src/App.jsx">...</file>',
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
        # Validate request
        if not request_data.response or not request_data.response.strip():
            raise HTTPException(status_code=400, detail="response is required and cannot be empty")

        # Create event generator
        async def event_generator() -> AsyncGenerator[dict, None]:
            """Generate SSE events for code application."""
            try:
                # Initialize results
                results = ApplyCodeResults()

                # Send start event
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "start",
                        "message": "Starting code application...",
                        "totalSteps": 3
                    })
                }

                # STEP 1: Parse AI response
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "status",
                        "message": "Parsing AI response..."
                    })
                }

                parsed = parse_ai_response(request_data.response)

                logger.info(f"Parsed {len(parsed.files)} files, {len(parsed.packages)} packages, {len(parsed.commands)} commands")

                # STEP 2: Extract and deduplicate packages
                all_packages: Set[str] = set()

                # Add packages from request
                if request_data.packages:
                    all_packages.update(request_data.packages)

                # Add packages from parsed response
                all_packages.update(parsed.packages)

                # Add packages from file imports
                for file in parsed.files:
                    file_packages = extract_packages_from_code(file.content)
                    all_packages.update(file_packages)

                # Remove empty strings and built-ins
                unique_packages = sorted([
                    pkg for pkg in all_packages
                    if pkg and pkg not in ('react', 'react-dom')
                ])

                # Send package detection event
                if unique_packages:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "step",
                            "step": 1,
                            "message": f"Detected {len(unique_packages)} packages",
                            "packages": unique_packages
                        })
                    }

                    # Note: Actual installation would happen here with sandbox integration
                    results.packages_installed = unique_packages
                else:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "info",
                            "message": "No packages to install"
                        })
                    }

                # STEP 3: Process files
                if parsed.files:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "step",
                            "step": 2,
                            "message": f"Processing {len(parsed.files)} files..."
                        })
                    }

                    for idx, file in enumerate(parsed.files, 1):
                        # Normalize path
                        normalized_path = normalize_file_path(file.path)

                        # Send file progress
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "file-progress",
                                "current": idx,
                                "total": len(parsed.files),
                                "fileName": normalized_path,
                                "action": "processing"
                            })
                        }

                        # Process content
                        content = file.content
                        content = strip_css_imports(content, normalized_path)
                        content = fix_tailwind_classes(content)

                        # Check if file is truncated
                        if not file.is_complete:
                            results.errors.append(f"Warning: {normalized_path} appears to be truncated")

                        # Track as created (would check if exists in real implementation)
                        results.files_created.append(normalized_path)

                        # Send file complete
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "file-complete",
                                "fileName": normalized_path,
                                "action": "created"
                            })
                        }

                        # Keepalive
                        if idx % 5 == 0:
                            yield {"event": "ping", "data": ""}

                # STEP 4: Process commands
                if parsed.commands:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "step",
                            "step": 3,
                            "message": f"Found {len(parsed.commands)} commands (not executed in this version)"
                        })
                    }

                    # Note: Actual command execution would happen with sandbox integration
                    results.commands_executed = parsed.commands

                # Send completion event
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "complete",
                        "results": results.dict(by_alias=True),
                        "message": f"Successfully processed {len(parsed.files)} files"
                    })
                }

            except HTTPException as he:
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "error",
                        "error": he.detail
                    })
                }

            except Exception as e:
                logger.error(f"Code application failed: {e}", exc_info=True)
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "error",
                        "error": f"Code application failed: {str(e)}"
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
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
