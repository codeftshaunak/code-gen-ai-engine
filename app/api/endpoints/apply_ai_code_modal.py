"""Apply AI-generated code streaming endpoint with Modal SDK integration."""

import json
import logging
import re
import os
import base64
from typing import AsyncGenerator, Dict, List
from fastapi import APIRouter, HTTPException, Header
from sse_starlette.sse import EventSourceResponse

from app.models.api_models import ApplyCodeRequest
from app.config.settings import settings

# Import shared sandbox storage from create_modal_sandbox
from app.api.endpoints.create_modal_sandbox import _sandboxes

# Import project state manager for tracking files
from app.utils.project_state import project_state_manager

router = APIRouter()
logger = logging.getLogger(__name__)


def parse_ai_response(response: str) -> dict:
    """Parse AI response to extract files, packages, and commands."""
    files = []
    packages = []
    commands = []

    # Parse file sections
    file_map = {}
    file_regex = re.compile(r'<file path="([^"]+)">([\s\S]*?)(?:</file>|$)')

    for match in file_regex.finditer(response):
        file_path = match.group(1)
        content = match.group(2).strip()
        has_closing_tag = '</file>' in response[match.start():match.end()]

        # Check if file already exists in map
        existing = file_map.get(file_path)

        should_replace = False
        if not existing:
            should_replace = True
        elif not existing.get('is_complete') and has_closing_tag:
            should_replace = True
            logger.info(f"Replacing incomplete {file_path} with complete version")
        elif (existing.get('is_complete') and has_closing_tag and
              len(content) > len(existing['content'])):
            should_replace = True
            logger.info(f"Replacing {file_path} with longer complete version")

        if should_replace:
            file_map[file_path] = {
                'content': content,
                'is_complete': has_closing_tag
            }

    # Convert map to list
    for path, data in file_map.items():
        files.append({
            'path': path,
            'content': data['content'],
            'is_complete': data['is_complete']
        })

        # Extract packages from file content
        file_packages = extract_packages_from_imports(data['content'])
        packages.extend(file_packages)

    # Parse command sections
    cmd_regex = re.compile(r'<command>(.*?)</command>')
    commands = [match.group(1).strip() for match in cmd_regex.finditer(response)]

    # Parse package sections
    pkg_regex = re.compile(r'<package>(.*?)</package>')
    packages.extend([match.group(1).strip() for match in pkg_regex.finditer(response)])

    return {
        'files': files,
        'packages': list(set(packages)),  # Deduplicate
        'commands': commands
    }


def extract_packages_from_imports(content: str) -> List[str]:
    """Extract package names from import statements."""
    packages = []

    # Match ES6 imports
    import_regex = re.compile(
        r"import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)(?:\s*,\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+))*\s+from\s+)?['\"]([^'\"]+)['\"]"
    )

    for match in import_regex.finditer(content):
        import_path = match.group(1)

        # Skip relative imports and built-ins
        if (not import_path.startswith('.') and
            not import_path.startswith('/') and
            import_path not in ('react', 'react-dom') and
            not import_path.startswith('@/')):

            # Extract package name (handle scoped packages)
            if import_path.startswith('@'):
                package_name = '/'.join(import_path.split('/')[:2])
            else:
                package_name = import_path.split('/')[0]

            if package_name not in packages:
                packages.append(package_name)

    return packages


def normalize_file_path(path: str) -> str:
    """Normalize file path for consistency."""
    # Remove leading slash
    if path.startswith('/'):
        path = path[1:]

    # Config files and env files that shouldn't have src/ prefix
    config_files = [
        'tailwind.config.js', 'vite.config.js', 'package.json',
        'package-lock.json', 'tsconfig.json', 'postcss.config.js',
        '.env', '.env.local', '.env.development', '.env.production'
    ]

    filename = path.split('/')[-1]

    # Add src/ prefix if needed
    if (not path.startswith('src/') and
        not path.startswith('public/') and
        path != 'index.html' and
        filename not in config_files):
        path = f'src/{path}'

    return path


@router.post("/apply-ai-code-stream-modal")
async def apply_ai_code_modal_stream(
    request_data: ApplyCodeRequest,
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Apply AI-generated code to Modal sandbox with streaming progress.

    This endpoint parses AI-generated code, writes files to the Modal volume,
    installs packages, and provides real-time progress updates via SSE.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Body:
        response (str): AI-generated response containing files, packages, and commands
        packages (list): Additional packages to install (optional)

    Returns:
        SSE stream with progress updates and results

    Example:
        ```bash
        curl -X POST http://localhost:3100/api/apply-ai-code-modal-stream \
          -H "Content-Type: application/json" \
          -H "X-Project-Id: my-project-123" \
          -d '{
            "response": "<file path=\\"src/App.jsx\\">...</file>",
            "packages": ["axios"]
          }'
        ```
    """
    try:
        project_id = x_project_id or "default"

        # Validate request
        if not request_data.response or not request_data.response.strip():
            raise HTTPException(
                status_code=400,
                detail="response is required and cannot be empty"
            )

        logger.info(f"[apply-ai-code-modal] Using project: {project_id}")
        logger.info(f"[apply-ai-code-modal] Response length: {len(request_data.response)}")

        # Parse AI response
        parsed = parse_ai_response(request_data.response)
        logger.info(f"[apply-ai-code-modal] Parsed {len(parsed['files'])} files")

        # Create event generator
        async def event_generator() -> AsyncGenerator[dict, None]:
            """Generate SSE events for code application."""
            try:
                results = {
                    'filesCreated': [],
                    'filesUpdated': [],
                    'packagesInstalled': [],
                    'commandsExecuted': [],
                    'errors': []
                }
                
                # Track if Vite has been restarted to avoid multiple restarts
                vite_restarted = False

                # Send start event
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "start",
                        "message": "Starting code application...",
                        "totalSteps": 3
                    })
                }

                # Get Modal sandbox and volume
                sandbox_data = _sandboxes.get(project_id)

                if not sandbox_data:
                    error_msg = "No active Modal sandbox found. Please create a sandbox first using /create-sandbox-v1"
                    logger.error(f"[apply-ai-code-modal] {error_msg}")
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "error",
                            "error": error_msg
                        })
                    }
                    return

                sandbox = sandbox_data["sandbox"]
                volume = sandbox_data["volume"]
                sandbox_id = sandbox_data["sandbox_id"]

                logger.info(f"[apply-ai-code-modal] Using existing sandbox: {sandbox_id}")
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "info",
                        "message": f"Using Modal sandbox: {sandbox_id}"
                    })
                }

                # Set Modal API key for volume operations
                os.environ["MODAL_TOKEN_ID"] = settings.MODAL_API_KEY.split(":")[0] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else settings.MODAL_API_KEY or ""
                os.environ["MODAL_TOKEN_SECRET"] = settings.MODAL_API_KEY.split(":")[1] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else ""

                # STEP 1: Install packages
                all_packages = set(request_data.packages or [])
                all_packages.update(parsed['packages'])

                # Remove built-ins
                unique_packages = sorted([
                    pkg for pkg in all_packages
                    if pkg and pkg not in ('react', 'react-dom')
                ])

                if unique_packages:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "step",
                            "step": 1,
                            "message": f"Installing {len(unique_packages)} packages...",
                            "packages": unique_packages
                        })
                    }

                    try:
                        # Install packages using Modal sandbox exec
                        install_cmd = f"cd /home/user/app && npm install {' '.join(unique_packages)}"
                        logger.info(f"[apply-ai-code-modal] Running: {install_cmd}")

                        install_process = sandbox.exec("bash", "-c", install_cmd, timeout=180)
                        install_output = install_process.stdout.read()

                        logger.info(f"[apply-ai-code-modal] Package install output: {install_output}")
                        results['packagesInstalled'] = unique_packages

                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "package-complete",
                                "packages": unique_packages
                            })
                        }
                    except Exception as e:
                        logger.error(f"Package installation failed: {e}")
                        results['errors'].append(f"Package installation failed: {str(e)}")
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "warning",
                                "message": f"Package installation failed: {str(e)}"
                            })
                        }
                else:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "step",
                            "step": 1,
                            "message": "No additional packages to install"
                        })
                    }

                # STEP 2: Write files to Modal volume
                files_to_write = parsed['files']

                # Filter out config files
                config_files = [
                    'tailwind.config.js', 'vite.config.js', 'package.json',
                    'package-lock.json', 'tsconfig.json', 'postcss.config.js'
                ]

                filtered_files = [
                    f for f in files_to_write
                    if f['path'].split('/')[-1] not in config_files
                ]

                if filtered_files:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "step",
                            "step": 2,
                            "message": f"Creating {len(filtered_files)} files..."
                        })
                    }

                    for idx, file in enumerate(filtered_files, 1):
                        try:
                            normalized_path = normalize_file_path(file['path'])

                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "file-progress",
                                    "current": idx,
                                    "total": len(filtered_files),
                                    "fileName": normalized_path,
                                    "action": "creating"
                                })
                            }

                            # Write file to Modal volume via sandbox
                            full_path = f"/home/user/app/{normalized_path}"
                            content = file['content']

                            # Remove CSS imports from JS/JSX files
                            if normalized_path.endswith(('.jsx', '.js', '.tsx', '.ts')):
                                content = re.sub(
                                    r"import\s+['\"]\.\/[^'\"]+\.css['\"];?\s*\n?",
                                    '',
                                    content
                                )

                            # Create directory if needed
                            dir_path = '/'.join(full_path.split('/')[:-1])
                            if dir_path:
                                mkdir_process = sandbox.exec(
                                    "bash", "-c",
                                    f"mkdir -p {dir_path}",
                                    timeout=10
                                )
                                mkdir_process.wait()

                            # Write file using sandbox exec (escaping content for bash)
                            # Use base64 encoding to avoid shell escaping issues
                            content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')

                            write_cmd = f"echo '{content_b64}' | base64 -d > {full_path}"
                            write_process = sandbox.exec("bash", "-c", write_cmd, timeout=30)
                            write_process.wait()

                            logger.info(f"[apply-ai-code-modal] Written: {full_path}")

                            results['filesCreated'].append(normalized_path)

                            # Track file in project state
                            project_state_manager.add_file(project_id, normalized_path, content)
                            
                            # If this is a .env file, restart Vite to reload environment variables
                            if normalized_path.endswith(('.env', '.env.local', '.env.development', '.env.production')):
                                if not vite_restarted:
                                    logger.info(f"[apply-ai-code-modal] Restarting Vite dev server to load new environment variables...")
                                    
                                    yield {
                                        "event": "message",
                                        "data": json.dumps({
                                            "type": "status",
                                            "message": "Restarting dev server to load environment variables..."
                                        })
                                    }
                                    
                                    try:
                                        # Kill existing Vite process
                                        kill_process = sandbox.exec("bash", "-c", "pkill -f vite", timeout=10)
                                        kill_process.wait()
                                        
                                        logger.info("[apply-ai-code-modal] Killed existing Vite process")
                                        
                                        # Wait for process to terminate
                                        import time
                                        time.sleep(1)
                                        
                                        # Restart Vite dev server
                                        restart_process = sandbox.exec(
                                            "bash", "-c",
                                            "cd /home/user/app && npm run dev",
                                            timeout=60
                                        )
                                        
                                        logger.info("[apply-ai-code-modal] Restarted Vite dev server")
                                        
                                        # Wait for Vite to be ready
                                        import asyncio
                                        await asyncio.sleep(3)
                                        
                                        vite_restarted = True
                                        
                                        yield {
                                            "event": "message",
                                            "data": json.dumps({
                                                "type": "status",
                                                "message": "Dev server restarted successfully! Environment variables loaded."
                                            })
                                        }
                                        
                                        logger.info("[apply-ai-code-modal] Vite dev server ready with new environment variables")
                                        
                                    except Exception as restart_error:
                                        logger.error(f"[apply-ai-code-modal] Error restarting dev server: {restart_error}")
                                        yield {
                                            "event": "message",
                                            "data": json.dumps({
                                                "type": "warning",
                                                "message": f"Warning: Dev server restart - {str(restart_error)}"
                                            })
                                        }

                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "file-complete",
                                    "fileName": normalized_path,
                                    "action": "created"
                                })
                            }

                        except Exception as e:
                            logger.error(f"Failed to create {file['path']}: {e}")
                            results['errors'].append(f"Failed to create {file['path']}: {str(e)}")
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "file-error",
                                    "fileName": file['path'],
                                    "error": str(e)
                                })
                            }

                    # Commit volume changes - volume is already mounted and auto-commits
                    # No explicit commit needed as volume is mounted in the sandbox
                    try:
                        logger.info("[apply-ai-code-modal] Files written to mounted volume (auto-persisted)")

                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "info",
                                "message": "Files written to persistent storage"
                            })
                        }
                    except Exception as e:
                        logger.warning(f"Volume info logging error: {e}")

                # STEP 3: Execute commands
                if parsed['commands']:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "step",
                            "step": 3,
                            "message": f"Executing {len(parsed['commands'])} commands..."
                        })
                    }

                    for idx, cmd in enumerate(parsed['commands'], 1):
                        try:
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "command-progress",
                                    "current": idx,
                                    "total": len(parsed['commands']),
                                    "command": cmd,
                                    "action": "executing"
                                })
                            }

                            # Execute command in Modal sandbox
                            full_cmd = f"cd /home/user/app && {cmd}"
                            logger.info(f"[apply-ai-code-modal] Executing: {full_cmd}")

                            cmd_process = sandbox.exec("bash", "-c", full_cmd, timeout=60)
                            cmd_output = cmd_process.stdout.read()

                            logger.info(f"[apply-ai-code-modal] Command output: {cmd_output}")
                            results['commandsExecuted'].append(cmd)

                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "command-complete",
                                    "command": cmd,
                                    "output": cmd_output or ""
                                })
                            }

                        except Exception as e:
                            logger.error(f"Command execution failed for {cmd}: {e}")
                            results['errors'].append(f"Command {cmd} failed: {str(e)}")
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "command-error",
                                    "command": cmd,
                                    "error": str(e)
                                })
                            }

                # Send completion event
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "complete",
                        "results": results,
                        "message": f"Successfully applied {len(results['filesCreated'])} files",
                        "sandboxId": sandbox_id
                    })
                }

            except Exception as e:
                logger.error(f"Code application failed: {e}", exc_info=True)
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "error",
                        "error": str(e)
                    })
                }

        # Return SSE response
        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
