"""Create AI sandbox endpoint (v2)."""

import uuid
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional


router = APIRouter()


class SandboxResponse(BaseModel):
    """Response model for sandbox creation."""

    success: bool
    project_id: str
    sandbox_id: str
    url: str
    provider: str
    message: str
    error: Optional[str] = None
    details: Optional[str] = None


@router.post("/create-ai-sandbox-v2")
async def create_ai_sandbox_v2(
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Create a new AI sandbox for code execution and preview.

    This endpoint creates an isolated sandbox environment where generated code
    can be executed safely. The sandbox is pre-configured with Vite + React.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Returns:
        JSON response with sandbox details including URL and sandbox ID

    Example:
        ```bash
        curl -X POST http://localhost:3100/api/create-ai-sandbox-v2 \
          -H "X-Project-Id: my-project-123"
        ```

    Response:
        ```json
        {
          "success": true,
          "projectId": "my-project-123",
          "sandboxId": "sb-abc123",
          "url": "https://sandbox.example.com/sb-abc123",
          "provider": "local",
          "message": "Sandbox created and Vite React app initialized"
        }
        ```

    Note:
        This is a simplified implementation. In production, this would integrate
        with sandbox providers like E2B or Vercel to create actual isolated
        execution environments.
    """
    try:
        project_id = x_project_id or "default"

        print(f"[create-ai-sandbox-v2] Creating sandbox for project: {project_id}")

        # Generate unique sandbox ID
        sandbox_id = f"sb-{uuid.uuid4().hex[:12]}"

        # In a real implementation, this would:
        # 1. Clean up existing sandboxes for this project
        # 2. Create new sandbox using provider (E2B, Vercel, etc.)
        # 3. Setup Vite React app in the sandbox
        # 4. Register sandbox with project state

        # For now, return mock data
        sandbox_url = f"http://localhost:5173"  # Default Vite dev server port

        print(f"[create-ai-sandbox-v2] Sandbox ready for project {project_id}")
        print(f"[create-ai-sandbox-v2] Sandbox ID: {sandbox_id}")
        print(f"[create-ai-sandbox-v2] URL: {sandbox_url}")

        return {
            "success": True,
            "projectId": project_id,
            "sandboxId": sandbox_id,
            "url": sandbox_url,
            "provider": "local",
            "message": "Sandbox created and Vite React app initialized"
        }

    except Exception as e:
        print(f"[create-ai-sandbox-v2] Error: {e}")

        # Cleanup on error (if needed)
        try:
            project_id = x_project_id or "default"
            print(f"[create-ai-sandbox-v2] Cleanup attempted for project {project_id}")
        except Exception:
            print("[create-ai-sandbox-v2] Could not extract projectId for cleanup")

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e) if isinstance(e, Exception) else "Failed to create sandbox",
                "details": getattr(e, "__traceback__", None)
            }
        )
