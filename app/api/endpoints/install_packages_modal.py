"""Install packages endpoint for Modal sandbox."""

import json
import asyncio
import os
from typing import List, AsyncGenerator, Dict
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from app.config.settings import settings
import modal

# Import global sandbox storage
from app.api.endpoints.create_modal_sandbox import _sandboxes

router = APIRouter()


class InstallPackagesRequest(BaseModel):
    """Request model for package installation."""

    packages: List[str]


@router.post("/install-packages-modal")
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

        # Get sandbox from storage
        if project_id not in _sandboxes:
            raise HTTPException(
                status_code=400,
                detail="No active sandbox provider available"
            )

        sandbox_info = _sandboxes[project_id]
        sandbox = sandbox_info.get("sandbox")
        
        if not sandbox:
            raise HTTPException(
                status_code=400,
                detail="No active sandbox provider available"
            )

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

                # Stop dev server
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "status",
                        "message": "Stopping development server..."
                    })
                }

                await asyncio.sleep(0.5)

                try:
                    # Try to kill any running dev server processes
                    kill_process = sandbox.exec("bash", "-c", "pkill -f vite", timeout=10)
                    kill_process.wait()
                    await asyncio.sleep(1)
                except Exception as kill_error:
                    # It's OK if no process is found
                    print(f"[install-packages] No existing dev server found: {kill_error}")

                # Check installed packages
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "status",
                        "message": "Checking installed packages..."
                    })
                }

                await asyncio.sleep(0.5)

                # Read package.json to check existing dependencies
                packages_to_install = valid_packages
                already_installed = []

                try:
                    # Read package.json from Modal sandbox
                    read_process = sandbox.exec(
                        "bash", "-c",
                        "cat /home/user/app/package.json",
                        timeout=10
                    )
                    package_json_content = read_process.stdout.read()

                    if package_json_content:
                        package_json = json.loads(package_json_content)
                        dependencies = package_json.get("dependencies", {})
                        dev_dependencies = package_json.get("devDependencies", {})
                        all_deps = {**dependencies, **dev_dependencies}

                        need_install = []
                        for pkg in valid_packages:
                            # Handle scoped packages and version specifications
                            pkg_name = pkg.split("@")[0] if not pkg.startswith("@") else "@" + pkg.split("@")[1]
                            
                            if pkg_name in all_deps:
                                already_installed.append(pkg_name)
                            else:
                                need_install.append(pkg)

                        packages_to_install = need_install

                        if already_installed:
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "info",
                                    "message": f"Already installed: {', '.join(already_installed)}"
                                })
                            }
                except Exception as error:
                    print(f"[install-packages] Error checking existing packages: {error}")
                    # If we can't check, just try to install all packages
                    packages_to_install = valid_packages

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

                    # Restart Vite server
                    try:
                        start_cmd = "cd /home/user/app && npm run dev -- --host --port 5173"
                        sandbox.exec("bash", "-lc", start_cmd)
                        await asyncio.sleep(2)
                    except Exception as restart_error:
                        print(f"[install-packages] Error restarting dev server: {restart_error}")

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

                # Execute npm install using Modal sandbox exec
                install_cmd = f"cd /home/user/app && npm install {' '.join(packages_to_install)} --legacy-peer-deps"
                print(f"[install-packages] Running: {install_cmd}")

                try:
                    install_process = sandbox.exec("bash", "-c", install_cmd, timeout=180)
                    
                    # Wait for process to complete
                    install_process.wait()
                    
                    # Get stdout and stderr
                    stdout = install_process.stdout.read() or ""
                    stderr = install_process.stderr.read() or ""

                    # Parse and send output
                    if stdout:
                        lines = stdout.split("\n")
                        for line in lines:
                            line = line.strip()
                            if line:
                                if "npm WARN" in line:
                                    yield {
                                        "event": "message",
                                        "data": json.dumps({
                                            "type": "warning",
                                            "message": line
                                        })
                                    }
                                elif line.startswith("+"):
                                    # Package installed line
                                    yield {
                                        "event": "message",
                                        "data": json.dumps({
                                            "type": "output",
                                            "message": line
                                        })
                                    }
                                    await asyncio.sleep(0.1)
                                elif line:
                                    yield {
                                        "event": "message",
                                        "data": json.dumps({
                                            "type": "output",
                                            "message": line
                                        })
                                    }

                    if stderr:
                        error_lines = stderr.split("\n")
                        for line in error_lines:
                            line = line.strip()
                            if line:
                                if "ERESOLVE" in line:
                                    yield {
                                        "event": "message",
                                        "data": json.dumps({
                                            "type": "warning",
                                            "message": f"Dependency conflict resolved with --legacy-peer-deps: {line}"
                                        })
                                    }
                                else:
                                    yield {
                                        "event": "message",
                                        "data": json.dumps({
                                            "type": "error",
                                            "message": line
                                        })
                                    }

                    # Check exit code
                    return_code = install_process.returncode
                    if return_code == 0:
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "success",
                                "message": f"Successfully installed: {', '.join(packages_to_install)}",
                                "installedPackages": packages_to_install
                            })
                        }
                    else:
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "error",
                                "message": "Package installation failed"
                            })
                        }

                except Exception as install_error:
                    error_message = str(install_error)
                    print(f"[install-packages] Installation error: {error_message}")
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "error",
                            "message": f"Installation error: {error_message}"
                        })
                    }
                    return

                # Restart development server
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "status",
                        "message": "Restarting development server..."
                    })
                }

                try:
                    # Kill existing dev server
                    try:
                        kill_process = sandbox.exec("bash", "-c", "pkill -f vite", timeout=10)
                        kill_process.wait()
                        await asyncio.sleep(1)
                    except:
                        pass

                    # Start Vite dev server
                    start_cmd = "cd /home/user/app && npm run dev -- --host --port 5173"
                    sandbox.exec("bash", "-lc", start_cmd)
                    
                    # Wait for server to start
                    await asyncio.sleep(3)

                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "complete",
                            "message": "Package installation complete and dev server restarted!",
                            "installedPackages": packages_to_install
                        })
                    }
                except Exception as restart_error:
                    error_message = str(restart_error)
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "error",
                            "message": f"Failed to restart dev server: {error_message}"
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
