"""Apply AI-generated code streaming endpoint with E2B sandbox integration."""

import json
import logging
import re
from typing import AsyncGenerator, Dict, Set, List
from fastapi import APIRouter, HTTPException, Header
from sse_starlette.sse import EventSourceResponse
from e2b_code_interpreter import Sandbox
import os

from app.models.api_models import ApplyCodeRequest, ApplyCodeResults
from app.config.settings import settings

# Import shared sandbox storage from create_ai_sandbox_v2
from app.api.endpoints.create_ai_sandbox_v2 import _sandboxes

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


@router.post("/apply-ai-code-stream")
async def apply_ai_code_stream(
    request_data: ApplyCodeRequest,
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Apply AI-generated code to E2B sandbox with streaming progress.

    This endpoint parses AI-generated code, writes files to the E2B sandbox,
    installs packages, and provides real-time progress updates via SSE.
    """
    try:
        project_id = x_project_id or "default"

        # Validate request
        if not request_data.response or not request_data.response.strip():
            raise HTTPException(
                status_code=400,
                detail="response is required and cannot be empty"
            )

        logger.info(f"[apply-ai-code-stream] Using project: {project_id}")
        logger.info(f"[apply-ai-code-stream] Response length: {len(request_data.response)}")

        # Parse AI response
        parsed = parse_ai_response(request_data.response)
        logger.info(f"[apply-ai-code-stream] Parsed {len(parsed['files'])} files")

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

                # Send start event
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "start",
                        "message": "Starting code application...",
                        "totalSteps": 3
                    })
                }

                # Get or create E2B sandbox
                sandbox = _sandboxes.get(project_id)

                if sandbox:
                    logger.info(f"[apply-ai-code-stream] Using existing sandbox: {sandbox.sandbox_id}")
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "info",
                            "message": f"Using existing sandbox: {sandbox.sandbox_id}"
                        })
                    }
                else:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "info",
                            "message": "No active sandbox, creating new one..."
                        })
                    }

                    # Set E2B API key
                    os.environ["E2B_API_KEY"] = settings.E2B_API_KEY
                    sandbox = Sandbox.create(timeout=600)
                    _sandboxes[project_id] = sandbox

                    logger.info(f"[apply-ai-code-stream] Created new sandbox: {sandbox.sandbox_id}")

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
                        # Install packages in sandbox
                        install_cmd = f"cd /home/user/app && npm install {' '.join(unique_packages)}"
                        result = sandbox.run_code(f"""
import subprocess
result = subprocess.run(
    ['bash', '-c', '{install_cmd}'],
    capture_output=True,
    text=True
)
print(result.stdout)
if result.stderr:
    print(result.stderr)
""")

                        logger.info(f"[apply-ai-code-stream] Package install output: {result.logs.stdout}")
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

                # STEP 2: Write files
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

                            # Write file to sandbox
                            full_path = f"/home/user/app/{normalized_path}"

                            # Create directory if needed
                            dir_path = '/'.join(full_path.split('/')[:-1])
                            if dir_path:
                                sandbox.run_code(f"""
import os
os.makedirs('{dir_path}', exist_ok=True)
""")

                            # Write file content
                            content = file['content']
                            # Remove CSS imports from JS/JSX files
                            if normalized_path.endswith(('.jsx', '.js', '.tsx', '.ts')):
                                content = re.sub(
                                    r"import\s+['\"]\.\/[^'\"]+\.css['\"];?\s*\n?",
                                    '',
                                    content
                                )

                            sandbox.run_code(f"""
with open('{full_path}', 'w') as f:
    f.write({json.dumps(content)})
print('✓ Written: {full_path}')
""")

                            results['filesCreated'].append(normalized_path)

                            # Track file in project state
                            project_state_manager.add_file(project_id, normalized_path, content)

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

                            result = sandbox.run_code(f"""
import subprocess
result = subprocess.run(
    ['bash', '-c', 'cd /home/user/app && {cmd}'],
    capture_output=True,
    text=True
)
print(result.stdout)
if result.stderr:
    print(result.stderr)
""")

                            results['commandsExecuted'].append(cmd)

                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "command-complete",
                                    "command": cmd,
                                    "output": ''.join(result.logs.stdout)
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
                        "message": f"Successfully applied {len(results['filesCreated'])} files"
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
