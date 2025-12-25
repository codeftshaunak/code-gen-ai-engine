"""Sandbox status endpoint."""

from fastapi import APIRouter, HTTPException, Header
from datetime import datetime


router = APIRouter()


@router.get("/sandbox-status")
async def sandbox_status(
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Check the status and health of the sandbox environment.

    This endpoint checks if a sandbox exists for the project, verifies its health,
    and returns detailed status information.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Returns:
        JSON response with sandbox status, health, and metadata

    Example:
        ```bash
        curl -X GET http://localhost:3100/api/sandbox-status \
          -H "X-Project-Id: my-project-123"
        ```

    Response (active sandbox):
        ```json
        {
          "success": true,
          "projectId": "my-project-123",
          "active": true,
          "healthy": true,
          "sandboxData": {
            "sandboxId": "sb-abc123",
            "url": "http://localhost:5173",
            "filesTracked": ["src/App.jsx", "src/main.jsx"],
            "lastHealthCheck": "2025-12-25T09:45:00.000Z"
          },
          "message": "Sandbox is active and healthy"
        }
        ```

    Response (no sandbox):
        ```json
        {
          "success": true,
          "projectId": "my-project-123",
          "active": false,
          "healthy": false,
          "sandboxData": null,
          "message": "No active sandbox"
        }
        ```
    """
    try:
        project_id = x_project_id or "default"

        # In a real implementation, this would:
        # 1. Get the sandbox provider from project state
        # 2. Check if provider exists and is healthy
        # 3. Get sandbox metadata (ID, URL, files tracked)
        # 4. Verify sandbox is responding to health checks

        # Simulate sandbox status check
        # For demo purposes, return active=False (no sandbox)
        sandbox_exists = False
        sandbox_healthy = False
        sandbox_info = None

        print(f"[sandbox-status] Detailed check: projectId={project_id}, providerExists={sandbox_exists}")

        if sandbox_exists:
            sandbox_info = {
                "sandboxId": "sb-example123",
                "url": "http://localhost:5173",
                "filesTracked": ["src/App.jsx", "src/main.jsx", "src/index.css"],
                "lastHealthCheck": datetime.utcnow().isoformat()
            }
            sandbox_healthy = True

        message = (
            "Sandbox is active and healthy" if sandbox_healthy
            else "Sandbox exists but is not responding" if sandbox_exists
            else "No active sandbox"
        )

        return {
            "success": True,
            "projectId": project_id,
            "active": sandbox_exists,
            "healthy": sandbox_healthy,
            "sandboxData": sandbox_info,
            "message": message
        }

    except Exception as e:
        print(f"[sandbox-status] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "projectId": x_project_id or "unknown",
                "active": False,
                "error": str(e)
            }
        )
