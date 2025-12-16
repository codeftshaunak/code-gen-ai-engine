"""
Sandbox Management Endpoints
Create, manage, and monitor sandboxes
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime

from app.core.app_state_manager import app_state_manager
from app.utils.project_utils import get_project_id
from app.config.settings import settings

router = APIRouter()


class CreateSandboxRequest(BaseModel):
    """Create sandbox request"""
    provider: Optional[str] = None  # e2b or vercel
    template: Optional[str] = "react-vite"


class CreateSandboxResponse(BaseModel):
    """Create sandbox response"""
    success: bool
    sandbox_id: str
    provider: str
    message: str
    url: Optional[str] = None


class SandboxStatusResponse(BaseModel):
    """Sandbox status response"""
    success: bool
    sandbox_id: str
    status: str
    uptime_seconds: Optional[float] = None
    provider: str
    is_running: bool


class KillSandboxRequest(BaseModel):
    """Kill sandbox request"""
    sandbox_id: Optional[str] = None


class GetFilesResponse(BaseModel):
    """Get sandbox files response"""
    success: bool
    files: List[str]
    total_count: int


@router.post(
    "/create-ai-sandbox-v2",
    response_model=CreateSandboxResponse,
    summary="Create AI Sandbox",
    description="""
    Create a new isolated sandbox environment for running code.

    **Features:**
    - Supports E2B and Vercel sandbox providers
    - Automatic Vite React app setup
    - Isolated environment per project
    - Configurable timeout

    **Request Headers:**
    - `X-Project-Id`: Required project identifier

    **Response:**
    - `sandbox_id`: Unique sandbox identifier
    - `provider`: Sandbox provider used (e2b or vercel)
    - `url`: Sandbox preview URL (if available)
    """
)
async def create_ai_sandbox_v2(
    request: CreateSandboxRequest,
    project_id: str = Depends(get_project_id)
) -> CreateSandboxResponse:
    """Create a new AI sandbox"""
    try:
        # Determine provider
        provider_type = request.provider or settings.SANDBOX_PROVIDER

        # Generate sandbox ID
        from nanoid import generate
        sandbox_id = f"sbx_{generate(size=12)}"

        # Create sandbox via app state manager
        provider = await app_state_manager.create_sandbox(
            project_id=project_id,
            sandbox_id=sandbox_id,
            provider_type=provider_type
        )

        # Setup Vite app
        await provider.setup_vite_app()

        # Determine preview URL based on provider
        preview_url = None
        if provider_type == "e2b":
            preview_url = f"https://{sandbox_id}.e2b.dev"
        elif provider_type == "vercel":
            preview_url = f"https://{sandbox_id}.vercel.app"

        return CreateSandboxResponse(
            success=True,
            sandbox_id=sandbox_id,
            provider=provider_type,
            message=f"Sandbox created successfully with {provider_type}",
            url=preview_url
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create sandbox: {str(e)}"
        )


@router.post(
    "/sandbox-status",
    response_model=SandboxStatusResponse,
    summary="Get Sandbox Status",
    description="""
    Get the current status of a sandbox.

    **Returns:**
    - Sandbox running state
    - Uptime information
    - Provider details

    **Request Headers:**
    - `X-Project-Id`: Required project identifier
    """
)
async def get_sandbox_status(
    sandbox_id: Optional[str] = None,
    project_id: str = Depends(get_project_id)
) -> SandboxStatusResponse:
    """Get sandbox status"""
    try:
        context = app_state_manager.for_project(project_id)
        provider = context.get_sandbox_provider(sandbox_id)

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Sandbox not found"
            )

        # Calculate uptime
        uptime = None
        if hasattr(context, 'created_at'):
            uptime = (datetime.now() - context.created_at).total_seconds()

        return SandboxStatusResponse(
            success=True,
            sandbox_id=provider.sandbox_id,
            status="running" if not provider.is_terminated else "terminated",
            uptime_seconds=uptime,
            provider=settings.SANDBOX_PROVIDER,
            is_running=not provider.is_terminated
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sandbox status: {str(e)}"
        )


@router.post(
    "/kill-sandbox",
    summary="Terminate Sandbox",
    description="""
    Terminate and cleanup a sandbox.

    **Request Headers:**
    - `X-Project-Id`: Required project identifier
    """
)
async def kill_sandbox(
    request: KillSandboxRequest,
    project_id: str = Depends(get_project_id)
):
    """Terminate a sandbox"""
    try:
        context = app_state_manager.for_project(project_id)
        provider = context.get_sandbox_provider(request.sandbox_id)

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Sandbox not found"
            )

        # Terminate the sandbox
        await provider.terminate()

        # Remove from context
        if request.sandbox_id and request.sandbox_id in context.sandbox_providers:
            del context.sandbox_providers[request.sandbox_id]

        return {
            "success": True,
            "message": "Sandbox terminated successfully",
            "sandbox_id": provider.sandbox_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to terminate sandbox: {str(e)}"
        )


@router.get(
    "/get-sandbox-files",
    response_model=GetFilesResponse,
    summary="List Sandbox Files",
    description="""
    List all files in the sandbox.

    **Query Parameters:**
    - `path`: Directory path to list (default: ".")
    - `sandbox_id`: Specific sandbox ID (optional)

    **Request Headers:**
    - `X-Project-Id`: Required project identifier
    """
)
async def get_sandbox_files(
    path: str = ".",
    sandbox_id: Optional[str] = None,
    project_id: str = Depends(get_project_id)
) -> GetFilesResponse:
    """List files in sandbox"""
    try:
        context = app_state_manager.for_project(project_id)
        provider = context.get_sandbox_provider(sandbox_id)

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Sandbox not found. Please create a sandbox first."
            )

        # List files
        files = await provider.list_files(path)

        return GetFilesResponse(
            success=True,
            files=files,
            total_count=len(files)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )
