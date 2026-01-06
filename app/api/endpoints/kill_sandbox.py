"""Kill sandbox endpoint."""

from fastapi import APIRouter, HTTPException, Header
from app.api.endpoints.create_ai_sandbox_v2 import _sandboxes
from app.utils.project_state import project_state_manager


router = APIRouter()


@router.post("/kill-sandbox")
async def kill_sandbox(
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Stop and clean up the sandbox environment.

    This endpoint terminates the sandbox container/environment for the specified
    project and cleans up all associated state.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Returns:
        JSON response confirming sandbox cleanup

    Example:
        ```bash
        curl -X POST http://localhost:3100/api/kill-sandbox \
          -H "X-Project-Id: my-project-123"
        ```

    Response:
        ```json
        {
          "success": true,
          "projectId": "my-project-123",
          "sandboxKilled": true,
          "message": "Sandbox cleaned up successfully"
        }
        ```
    """
    try:
        project_id = x_project_id or "default"

        print(f"[kill-sandbox] Stopping sandbox for project: {project_id}")

        # Get the sandbox instance for the project
        sandbox = _sandboxes.get(project_id)

        # Terminate the sandbox if it exists
        if sandbox:
            try:
                sandbox.kill()
                print(f"[kill-sandbox] Sandbox terminated for project: {project_id}")
            except Exception as sandbox_error:
                print(f"[kill-sandbox] Warning: Failed to terminate sandbox: {sandbox_error}")

            # Remove from global storage
            del _sandboxes[project_id]

        # Clean up project state
        project_state_manager.clear_project(project_id)

        print(f"[kill-sandbox] Sandbox stopped and state cleaned up successfully for project: {project_id}")

        return {
            "success": True,
            "projectId": project_id,
            "sandboxKilled": True,
            "message": "Sandbox cleaned up successfully"
        }

    except Exception as e:
        print(f"[kill-sandbox] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
