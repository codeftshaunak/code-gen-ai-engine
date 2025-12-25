"""Update sandbox session time endpoint."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel


router = APIRouter()


class UpdateTimeoutRequest(BaseModel):
    """Request model for updating sandbox timeout."""

    timeout: int


@router.post("/update-sandbox-session-time")
async def update_sandbox_session_time(
    request: UpdateTimeoutRequest,
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Update the session timeout for an active sandbox.

    This endpoint extends or modifies the timeout duration for sandbox environments
    to prevent premature termination during active development.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Request Body:
        - timeout (int): Timeout duration in seconds

    Returns:
        JSON response confirming timeout update

    Example:
        ```bash
        curl -X POST http://localhost:3100/api/update-sandbox-session-time \
          -H "Content-Type: application/json" \
          -H "X-Project-Id: my-project-123" \
          -d '{"timeout": 1800}'
        ```

    Response:
        ```json
        {
          "success": true,
          "message": "Sandbox timeout updated to 1800 seconds",
          "projectId": "my-project-123",
          "provider": "local"
        }
        ```
    """
    try:
        project_id = x_project_id or "default"

        # In a real implementation, this would:
        # 1. Get the sandbox provider for the project
        # 2. Check if provider exists
        # 3. Get sandbox info (E2B, Vercel, etc.)
        # 4. Call provider-specific timeout update method
        #    - E2B: sandbox.setTimeout(timeout)
        #    - Vercel: sandbox.extendTimeout(timeout)

        # Simulate provider check
        provider_exists = False

        if not provider_exists:
            raise HTTPException(
                status_code=404,
                detail="No active sandbox provider found"
            )

        # For demonstration, simulate successful timeout update
        provider_type = "local"

        print(f"[update-sandbox-session-time] Timeout updated for project: {project_id}")

        return {
            "success": True,
            "message": f"Sandbox timeout updated to {request.timeout} seconds",
            "projectId": project_id,
            "provider": provider_type
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"[update-sandbox-session-time] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
