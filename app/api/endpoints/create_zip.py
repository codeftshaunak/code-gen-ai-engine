"""
Create Zip Endpoint
Creates a zip archive of sandbox files
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import io
import zipfile
import asyncio

from app.core.app_state_manager import app_state_manager
from app.utils.project_utils import get_project_id

router = APIRouter()


class CreateZipRequest(BaseModel):
    """Create zip request"""
    files: Optional[List[str]] = None  # Specific files to include, or None for all
    sandbox_id: Optional[str] = None


@router.post(
    "/create-zip",
    summary="Create Zip Archive",
    description="""
    Create a downloadable zip archive of sandbox files.

    **Features:**
    - Include all files or specific files
    - Streams zip file for efficient download
    - Preserves directory structure

    **Request Headers:**
    - `X-Project-Id`: Required project identifier

    **Request Body:**
    - `files`: List of specific file paths to include (optional, defaults to all files)
    - `sandbox_id`: Specific sandbox ID (optional)

    **Response:**
    Streaming zip file download
    """
)
async def create_zip(
    request: CreateZipRequest,
    project_id: str = Depends(get_project_id)
):
    """Create zip archive of sandbox files"""
    try:
        context = app_state_manager.for_project(project_id)
        provider = context.get_sandbox_provider(request.sandbox_id)

        if not provider:
            raise HTTPException(
                status_code=404,
                detail="Sandbox not found. Please create a sandbox first."
            )

        # Create in-memory zip file
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Determine which files to include
            files_to_zip = request.files

            if not files_to_zip:
                # Get all files from sandbox
                files_to_zip = await provider.list_files(".")

            # Add each file to zip
            for file_path in files_to_zip:
                try:
                    # Read file content from sandbox
                    content = await provider.read_file(file_path)

                    # Add to zip with proper path
                    zip_file.writestr(file_path, content)

                except Exception as e:
                    # Skip files that can't be read
                    print(f"Skipping file {file_path}: {e}")
                    continue

        # Seek to beginning of buffer
        zip_buffer.seek(0)

        # Return as streaming response
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={project_id}-sandbox.zip"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create zip: {str(e)}"
        )
