"""Get sandbox files endpoint using Modal volume API."""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from app.config.settings import settings
import os

router = APIRouter()

@router.get("/get-sandbox-files-modal")
async def get_sandbox_file(
    file_path: Optional[str] = None,
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Get file content or list all files with contents from the sandbox volume.

    Query Parameters:
        file_path (str, optional): Path to the file relative to /home/user/app (e.g., "src/App.jsx")
                                   If not provided, returns all files with their contents

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Returns:
        JSON response with file content or complete file tree with contents

    Example:
        ```bash
        curl -X GET http://localhost:3100/api/get-sandbox-files-v1 \
          -H "X-Project-Id: my-project-123"
        ```

    Response:
        ```json
        {
          "success": true,
          "projectId": "my-project-123",
          "files": {
            "src/App.jsx": "import React from 'react'...",
            "src/index.css": "...",
            "package.json": "..."
          },
          "structure": "src/\nsrc/components/\npublic/",
          "fileCount": 15,
          "manifest": {
            "files": {...},
            "routes": [],
            "componentTree": {},
            "entryPoint": "/src/main.jsx",
            "styleFiles": ["/src/index.css"],
            "timestamp": 1234567890
          }
        }
        ```
    """
    try:
        project_id = x_project_id or "default"

        # Set Modal API key as environment variable
        os.environ["MODAL_TOKEN_ID"] = settings.MODAL_API_KEY.split(":")[0] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else settings.MODAL_API_KEY or ""
        os.environ["MODAL_TOKEN_SECRET"] = settings.MODAL_API_KEY.split(":")[1] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else ""

        # Import modal after setting environment variables
        import modal

        # Get the volume by name using project_id
        volume = modal.Volume.from_name(project_id, create_if_missing=True)

        if file_path is None:
            # Return all files with their contents
            files: dict = {}
            file_list: List[str] = []
            try:
                print(f"[get-sandbox-files] Listing and reading files for volume: {project_id}")

                # Use volume listdir with recursive=True to get all files
                for file_info in volume.listdir("/", recursive=True):
                    # Skip directories and node_modules paths
                    if file_info.type == modal.volume.FileEntryType.DIRECTORY or "node_modules" in file_info.path:
                        continue

                    file_path_rel = file_info.path.lstrip("/")
                    file_list.append(file_path_rel)

                    # Read file content
                    try:
                        full_path = file_info.path
                        content_bytes = b"".join(volume.read_file(full_path))
                        content = content_bytes.decode('utf-8', errors='replace')
                        files[file_path_rel] = content
                    except Exception as e:
                        print(f"[get-sandbox-files] Error reading {file_path_rel}: {e}")
                        files[file_path_rel] = ""

                print(f"[get-sandbox-files] Found and read {len(files)} files via volume.listdir")

            except Exception as e:
                print(f"[get-sandbox-files] Error listing/reading files: {e}")
                import traceback
                traceback.print_exc()
                files = {}
                file_list = []

            # Build directory structure string
            structure = ""
            dirs = set()
            for file_path in file_list:
                dir_path = os.path.dirname(file_path)
                if dir_path:
                    dirs.add(dir_path + "/")

            for dir_path in sorted(dirs):
                structure += dir_path + "\n"

            # Build file manifest
            manifest = {
                "files": {
                    f"/{path}": {
                        "content": content,
                        "type": "component" if ".jsx" in path or ".js" in path else "style" if ".css" in path else "config",
                        "path": f"/{path}",
                        "relativePath": path,
                        "lastModified": 1766655000000,  # Mock timestamp
                        "exports": ["App"] if "App.jsx" in path else [],
                        "imports": ["react", "react-dom"] if "main.jsx" in path else []
                    }
                    for path, content in files.items()
                },
                "routes": [],
                "componentTree": {
                    "App": {
                        "file": "/src/App.jsx",
                        "imports": ["react"],
                        "importedBy": ["/src/main.jsx"],
                        "type": "component"
                    }
                } if "src/App.jsx" in files else {},
                "entryPoint": "/src/main.jsx" if "src/main.jsx" in files else "",
                "styleFiles": [f"/{path}" for path in file_list if ".css" in path],
                "timestamp": 1766655000000
            }

            return {
                "success": True,
                "projectId": project_id,
                "files": files,
                "structure": structure,
                "fileCount": len(files),
                "manifest": manifest
            }
        if ".." in file_path or file_path.startswith("/"):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "Invalid file path"
                }
            )

        # Read the file content using volume read_file
        try:
            full_path = f"/{file_path}"
            content_bytes = b"".join(volume.read_file(full_path))
            print(f"[get-sandbox-files] Read {len(content_bytes)} bytes from volume")
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": f"File not found or error reading file: {str(e)}"
                }
            )

        return {
            "success": True,
            "projectId": project_id,
            "filePath": file_path,
            "content": (content_bytes or b"").decode('utf-8', errors='replace'),
            "volumePath": "/home/user/app"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[get-sandbox-file] Error: {e}")

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "details": str(e)
            }
        )
