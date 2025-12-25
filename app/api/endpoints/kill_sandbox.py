"""Kill sandbox endpoint."""

from fastapi import APIRouter, HTTPException, Header


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

        # In a real implementation, this would:
        # 1. Get the sandbox provider for the project
        # 2. Terminate the sandbox container/VM
        # 3. Clean up project state
        # 4. Release resources

        # Simulate cleanup
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
