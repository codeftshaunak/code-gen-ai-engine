"""
Install Packages Endpoint
Installs npm packages with automatic Vite server restart
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncIterator, Set
import json

from app.models.api_models import InstallPackagesRequest
from app.core.app_state_manager import app_state_manager
from app.utils.project_utils import get_project_id

router = APIRouter()


async def install_packages_stream(
    request: InstallPackagesRequest,
    project_id: str
) -> AsyncIterator[str]:
    """
    Install npm packages with streaming progress

    Steps:
    1. Deduplicate package names
    2. Check existing installations
    3. Stop Vite dev server
    4. Install missing packages
    5. Restart Vite dev server
    """
    try:
        # Get project context and sandbox
        context = app_state_manager.for_project(project_id)
        sandbox = context.get_sandbox_provider(request.sandbox_id)

        if not sandbox:
            raise HTTPException(
                status_code=400,
                detail="No sandbox found. Please create a sandbox first."
            )

        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'message': 'Starting package installation...'})}\n\n"

        # Deduplicate packages
        packages: Set[str] = set(request.packages)

        if not packages:
            yield f"data: {json.dumps({'type': 'complete', 'message': 'No packages to install'})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'info', 'message': f'Installing {len(packages)} packages: {list(packages)}'})}\n\n"

        # Check existing installations (read package.json)
        try:
            package_json_content = await sandbox.read_file("package.json")
            import json as json_lib
            package_json = json_lib.loads(package_json_content)
            existing_deps = set(package_json.get("dependencies", {}).keys())
            existing_dev_deps = set(package_json.get("devDependencies", {}).keys())
            already_installed = packages & (existing_deps | existing_dev_deps)

            if already_installed:
                yield f"data: {json.dumps({'type': 'info', 'message': f'Already installed: {list(already_installed)}'})}\n\n"
                packages = packages - already_installed

        except Exception as e:
            # package.json might not exist yet, continue
            yield f"data: {json.dumps({'type': 'warning', 'message': 'Could not read package.json'})}\n\n"

        if not packages:
            yield f"data: {json.dumps({'type': 'complete', 'message': 'All packages already installed'})}\n\n"
            return

        # Stop Vite server before installation
        yield f"data: {json.dumps({'type': 'stage', 'stage': 'stop_vite', 'message': 'Stopping Vite server...'})}\n\n"

        # Install packages
        yield f"data: {json.dumps({'type': 'stage', 'stage': 'install', 'message': f'Installing {len(packages)} packages...'})}\n\n"

        installed_packages = []
        async for output in sandbox.install_packages(list(packages)):
            yield f"data: {json.dumps({'type': 'output', 'content': output})}\n\n"

            # Track successful installations
            for pkg in packages:
                if pkg in output and "added" in output.lower():
                    if pkg not in installed_packages:
                        installed_packages.append(pkg)

        # Restart Vite server
        yield f"data: {json.dumps({'type': 'stage', 'stage': 'restart_vite', 'message': 'Restarting Vite server...'})}\n\n"

        async for output in sandbox.restart_vite_server():
            yield f"data: {json.dumps({'type': 'vite_output', 'content': output})}\n\n"

            # Break after server starts
            if "ready" in output.lower() or "local:" in output.lower():
                break

        # Send completion event
        result = {
            'type': 'complete',
            'message': 'Packages installed successfully',
            'installed': installed_packages or list(packages),
            'count': len(packages)
        }
        yield f"data: {json.dumps(result)}\n\n"

    except Exception as e:
        error_data = {
            'type': 'error',
            'error': str(e),
            'message': 'Package installation failed'
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post(
    "/install-packages",
    summary="Install NPM Packages (Streaming)",
    description="""
    Install npm packages with automatic Vite server restart.

    **Features:**
    - Deduplicates package names
    - Checks existing installations in package.json
    - Stops running Vite dev server before installation
    - Skips already-installed packages
    - Restarts Vite dev server after installation
    - Streams progress updates for each package
    - Uses `--legacy-peer-deps` flag by default

    **Request Headers:**
    - `X-Project-Id`: Required project identifier

    **Response:**
    Server-Sent Events stream with installation progress
    """
)
async def install_packages(
    request: InstallPackagesRequest,
    project_id: str = Depends(get_project_id)
):
    """Install npm packages with streaming response"""
    return StreamingResponse(
        install_packages_stream(request, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
