"""Run commands in Modal sandbox endpoint."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import os
import modal
import logging

from app.config.settings import settings

# Suppress hpack debug logs
logging.getLogger('hpack.hpack').setLevel(logging.WARNING)

router = APIRouter()

MODAL_APP_NAME = "vite-preview-platform"


class RunCommandRequest(BaseModel):
    """Request model for running commands in sandbox."""
    command: str
    timeout: Optional[int] = 60


class RunCommandResponse(BaseModel):
    """Response model for command execution."""
    success: bool
    projectId: str
    output: Optional[str] = None
    exitCode: Optional[int] = None
    message: str
    error: Optional[str] = None


@router.post("/run-command-modal")
async def run_command(
    payload: RunCommandRequest,
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Run a command in an existing Modal sandbox.

    This endpoint executes a command (like 'npm run build') in an already-created sandbox.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Request Body:
        command (str): The command to execute (e.g., 'npm run build', 'npm run dev')
        timeout (int): Timeout in seconds (default: 60)

    Returns:
        JSON response with command output and exit code

    Example:
        ```bash
        curl -X POST http://localhost:3100/api/run-command-modal \
          -H "X-Project-Id: my-project-123" \
          -H "Content-Type: application/json" \
          -d '{
            "command": "npm run build",
            "timeout": 120
          }'
        ```

    Response:
        ```json
        {
          "success": true,
          "projectId": "my-project-123",
          "output": "STDOUT:\\n\\n> sandbox-app@1.0.0 build\\n> vite build\\n...\\n\\nExit code: 0",
          "exitCode": 0,
          "message": "Command executed successfully"
        }
        ```
    """
    try:
        project_id = x_project_id or "default"
        command = payload.command
        timeout = payload.timeout or 60

        print(f"[run-command] Executing command for project: {project_id}")
        print(f"[run-command] Command: {command}")

        # Check if Modal API key is configured
        if not settings.MODAL_API_KEY:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "MODAL_API_KEY not configured",
                    "details": "Please set MODAL_API_KEY in your .env file"
                }
            )

        # Set Modal API key as environment variable
        os.environ["MODAL_TOKEN_ID"] = settings.MODAL_API_KEY.split(":")[0] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else settings.MODAL_API_KEY or ""
        os.environ["MODAL_TOKEN_SECRET"] = settings.MODAL_API_KEY.split(":")[1] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else ""


        # Lookup existing sandbox by project ID
        print(f"[run-command] Looking up sandbox for project: {project_id}")
        try:
            sandbox = modal.Sandbox.from_name(MODAL_APP_NAME, project_id)

            if sandbox is None:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "success": False,
                        "error": "Sandbox not found",
                        "details": f"No active sandbox found for project {project_id}. Please create a sandbox first using /create-sandbox-modal"
                    }
                )

            sandbox_id = sandbox.object_id
            print(f"[run-command] Found sandbox: {sandbox_id}")

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "does not exist" in error_msg:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "success": False,
                        "error": "Sandbox not found",
                        "details": f"No active sandbox found for project {project_id}. Please create a sandbox first using /create-sandbox-modal"
                    }
                )
            else:
                print(f"[run-command] Error looking up sandbox: {e}")
                raise

        # Execute command in sandbox
        print(f"[run-command] Executing command in sandbox...")
        try:
            # Execute the command in the app directory
            process = sandbox.exec(
                "bash",
                "-lc",
                f"cd /home/user/app && {command}",
                timeout=timeout
            )

            # Get output
            stdout = process.stdout.read() if process.stdout else ""
            stderr = process.stderr.read() if process.stderr else ""

            # Wait for process to complete and get exit code
            exit_code = process.wait()

            # Format output like the expected response
            stdout_str = stdout.decode('utf-8', errors='replace') if isinstance(stdout, bytes) else (stdout or "")
            stderr_str = stderr.decode('utf-8', errors='replace') if isinstance(stderr, bytes) else (stderr or "")

            # Combine output with STDOUT prefix and exit code suffix
            combined_output = f"STDOUT:\n\n{stdout_str}"
            if stderr_str:
                combined_output += f"\n\nSTDERR:\n{stderr_str}"
            combined_output += f"\n\nExit code: {exit_code}"

            print(f"[run-command] Command executed successfully")
            print(f"[run-command] Output length: {len(combined_output)} bytes")

            return {
                "success": True,
                "projectId": project_id,
                "output": combined_output,
                "exitCode": exit_code,
                "message": "Command executed successfully"
            }

        except Exception as e:
            error_str = str(e)
            print(f"[run-command] Command execution error: {error_str}")

            # Check if it's a timeout error
            if "timeout" in error_str.lower():
                raise HTTPException(
                    status_code=504,
                    detail={
                        "success": False,
                        "error": "Command timeout",
                        "details": f"Command '{command}' exceeded timeout of {timeout} seconds"
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "error": "Command execution failed",
                        "details": error_str
                    }
                )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[run-command] Unexpected error: {e}")

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Unexpected error",
                "details": str(e)
            }
        )
