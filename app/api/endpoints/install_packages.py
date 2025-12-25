"""Install packages endpoint."""

import json
import asyncio
from typing import List, AsyncGenerator
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse


router = APIRouter()


class InstallPackagesRequest(BaseModel):
    """Request model for package installation."""

    packages: List[str]


@router.post("/install-packages")
async def install_packages(
    request: InstallPackagesRequest,
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Install npm packages in the sandbox environment.

    This endpoint installs specified npm packages, checking for already installed
    packages, handling dependencies, and restarting the development server.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Request Body:
        - packages (List[str]): Array of package names to install
          Examples: ["lucide-react", "@radix-ui/react-dialog", "framer-motion"]

    Response:
        Server-Sent Events stream with the following event types:
        - start: Installation started
        - status: Progress updates
        - info: Information messages
        - output: Installation output
        - warning: Warning messages
        - success: Successful package installation
        - error: Error messages
        - complete: Installation complete

    Example:
        ```bash
        curl -X POST http://localhost:3100/api/install-packages \
          -H "Content-Type: application/json" \
          -H "X-Project-Id: my-project" \
          -d '{"packages": ["lucide-react", "framer-motion"]}'
        ```

    Response Stream:
        ```
        data: {"type":"start","message":"Installing 2 packages...","packages":["lucide-react","framer-motion"]}

        data: {"type":"status","message":"Stopping development server..."}

        data: {"type":"status","message":"Checking installed packages..."}

        data: {"type":"info","message":"Installing 2 new package(s): lucide-react, framer-motion"}

        data: {"type":"success","message":"Successfully installed: lucide-react, framer-motion","installedPackages":["lucide-react","framer-motion"]}

        data: {"type":"status","message":"Restarting development server..."}

        data: {"type":"complete","message":"Package installation complete and dev server restarted!","installedPackages":["lucide-react","framer-motion"]}
        ```

    Note:
        This is a simplified implementation that simulates package installation.
        In production, this would integrate with actual sandbox providers to
        execute npm install commands in isolated environments.
    """
    try:
        project_id = x_project_id or "default"

        # Validate packages
        if not request.packages or len(request.packages) == 0:
            raise HTTPException(
                status_code=400,
                detail="Packages array is required"
            )

        # Validate and deduplicate package names
        valid_packages = list(set([
            pkg.strip()
            for pkg in request.packages
            if pkg and isinstance(pkg, str) and pkg.strip()
        ]))

        if len(valid_packages) == 0:
            raise HTTPException(
                status_code=400,
                detail="No valid package names provided"
            )

        # Log if duplicates were found
        if len(request.packages) != len(valid_packages):
            removed_count = len(request.packages) - len(valid_packages)
            print(f"[install-packages] Cleaned packages for project {project_id}: removed {removed_count} invalid/duplicate entries")
            print(f"[install-packages] Original: {request.packages}")
            print(f"[install-packages] Cleaned: {valid_packages}")

        print(f"[install-packages] Installing packages: {valid_packages}")

        # Create event generator
        async def event_generator() -> AsyncGenerator[dict, None]:
            """Generate SSE events for package installation."""
            try:
                # Send start event
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "start",
                        "message": f"Installing {len(valid_packages)} package{'s' if len(valid_packages) > 1 else ''}...",
                        "packages": valid_packages
                    })
                }

                # Simulate stopping dev server
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "status",
                        "message": "Stopping development server..."
                    })
                }

                await asyncio.sleep(0.5)

                # Check installed packages
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "status",
                        "message": "Checking installed packages..."
                    })
                }

                await asyncio.sleep(0.5)

                # Simulate checking package.json
                # In a real implementation, this would read package.json from the sandbox
                already_installed = []
                packages_to_install = valid_packages

                # Common pre-installed packages in Vite React projects
                common_deps = ["react", "react-dom", "vite"]
                already_installed = [pkg for pkg in valid_packages if pkg in common_deps]
                packages_to_install = [pkg for pkg in valid_packages if pkg not in common_deps]

                if already_installed:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "info",
                            "message": f"Already installed: {', '.join(already_installed)}"
                        })
                    }

                if len(packages_to_install) == 0:
                    # All packages already installed
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "success",
                            "message": "All packages are already installed",
                            "installedPackages": [],
                            "alreadyInstalled": valid_packages
                        })
                    }

                    # Restart dev server
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "status",
                            "message": "Restarting development server..."
                        })
                    }

                    await asyncio.sleep(1)

                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "complete",
                            "message": "Dev server restarted!",
                            "installedPackages": []
                        })
                    }

                    return

                # Install new packages
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "info",
                        "message": f"Installing {len(packages_to_install)} new package(s): {', '.join(packages_to_install)}"
                    })
                }

                await asyncio.sleep(1)

                # Simulate npm install output
                for pkg in packages_to_install:
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "output",
                            "message": f"+ {pkg}"
                        })
                    }
                    await asyncio.sleep(0.3)

                # Success message
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "success",
                        "message": f"Successfully installed: {', '.join(packages_to_install)}",
                        "installedPackages": packages_to_install
                    })
                }

                # Restart development server
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "status",
                        "message": "Restarting development server..."
                    })
                }

                await asyncio.sleep(2)

                # Complete
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "complete",
                        "message": "Package installation complete and dev server restarted!",
                        "installedPackages": packages_to_install
                    })
                }

            except Exception as e:
                error_message = str(e) if str(e) != "undefined" else "Installation failed"
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "error",
                        "message": error_message
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

    except HTTPException:
        raise

    except Exception as e:
        print(f"[install-packages] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
