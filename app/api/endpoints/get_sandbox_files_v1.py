"""Get sandbox files endpoint using Modal filesystem API."""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, Dict, List
from app.config.settings import settings
import os

# Import shared sandbox storage from create_sandbox_v1
from app.api.endpoints.create_sandbox_v1 import _sandboxes

router = APIRouter()

def list_volume_files_recursive(volume, path: str = "/", exclude_patterns: List[str] = None) -> List[str]:
    """Recursively list all files in a Modal volume."""
    if exclude_patterns is None:
        exclude_patterns = ["node_modules", ".git", ".cache", "__pycache__"]

    all_files = []
    try:
        items = volume.listdir(path)
        for item in items:
            # Check if item should be excluded
            should_exclude = any(pattern in item for pattern in exclude_patterns)
            if should_exclude:
                continue

            full_path = f"{path}/{item}".replace("//", "/")

            # Check if it's a directory by trying to list it
            try:
                volume.listdir(full_path)
                # It's a directory, recurse
                all_files.extend(list_volume_files_recursive(volume, full_path, exclude_patterns))
            except:
                # It's a file
                all_files.append(full_path)
    except Exception as e:
        print(f"[list_volume_files_recursive] Error listing {path}: {e}")

    return all_files

@router.get("/get-sandbox-files-v1")
async def get_sandbox_file(
    file_path: Optional[str] = None,
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Get file content or list files from the sandbox volume.

    Query Parameters:
        file_path (str, optional): Path to the file relative to /home/user/app (e.g., "src/App.jsx")
                                   If not provided, returns list of all files

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Returns:
        JSON response with file content or file list
    """
    try:
        project_id = x_project_id or "default"

        # Set Modal API key as environment variable
        os.environ["MODAL_TOKEN_ID"] = settings.MODAL_API_KEY.split(":")[0] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else settings.MODAL_API_KEY or ""
        os.environ["MODAL_TOKEN_SECRET"] = settings.MODAL_API_KEY.split(":")[1] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else ""

        # Import modal after setting environment variables
        import modal

        # Get the volume by name
        volume_name = f"sandbox-volume-{project_id}"
        volume = modal.Volume.from_name(volume_name, create_if_missing=True)

        # Try to reuse existing sandbox for the project (live filesystem)
        sandbox_entry = _sandboxes.get(project_id)
        sandbox = sandbox_entry["sandbox"] if sandbox_entry and sandbox_entry.get("sandbox") else None

        if file_path is None:
            # Return list of files - use volume.listdir recursively for reliability
            files: List[str] = []
            try:
                print(f"[get-sandbox-files] Listing files for volume: {volume_name}")

                # Method 1: Use recursive volume listing (most reliable)
                raw_files = list_volume_files_recursive(volume, "/")
                # Strip leading slash and filter
                files = [f.lstrip("/") for f in raw_files if f and f != "/"]
                print(f"[get-sandbox-files] Found {len(files)} files via volume.listdir")

                # Method 2: If volume listing returns nothing, try sandbox exec (fallback)
                if not files and sandbox:
                    print("[get-sandbox-files] Volume empty, trying sandbox exec...")
                    find_cmd = "find /home/user/app -type f -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null | head -200"
                    proc = sandbox.exec("sh", "-c", find_cmd)
                    out = (proc.stdout.read() or b"").decode("utf-8", errors="replace").strip()
                    files = [p.replace("/home/user/app/", "") for p in out.split("\n") if p.strip() and p.startswith("/home/user/app/")]
                    print(f"[get-sandbox-files] Found {len(files)} files via sandbox exec")

                # Method 3: If still empty, try a temp sandbox mount (last resort)
                if not files:
                    print("[get-sandbox-files] Trying temp sandbox mount...")
                    temp = modal.Sandbox.create(
                        image=modal.Image.debian_slim(),
                        timeout=60,
                        volumes={"/mnt/vol": volume},
                    )
                    find_cmd = "find /mnt/vol -type f 2>/dev/null | head -200"
                    proc = temp.exec("sh", "-c", find_cmd)
                    out = (proc.stdout.read() or b"").decode("utf-8", errors="replace").strip()
                    files = [p.replace("/mnt/vol/", "") for p in out.split("\n") if p.strip() and p.startswith("/mnt/vol/")]
                    temp.terminate()
                    print(f"[get-sandbox-files] Found {len(files)} files via temp sandbox")

            except Exception as e:
                print(f"[get-sandbox-files] Error listing files: {e}")
                import traceback
                traceback.print_exc()
                files = []

            return {
                "success": True,
                "projectId": project_id,
                "files": files,
                "volumePath": "/home/user/app",
                "volumeName": volume_name,
            }
        if ".." in file_path or file_path.startswith("/"):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "Invalid file path"
                }
            )

        # Read the file content using live sandbox when available, else volume
        try:
            content_bytes: bytes = b""
            if sandbox:
                # Prefer reading live content inside sandbox
                cat_cmd = f"cat /home/user/app/{file_path}"
                proc = sandbox.exec("sh", "-c", cat_cmd)
                content_bytes = proc.stdout.read() or b""
                if not content_bytes:
                    # Fallback to volume if empty
                    full_path = f"/{file_path}"
                    content_bytes = b"".join(volume.read_file(full_path))
            else:
                # No sandbox available; read from volume directly
                full_path = f"/{file_path}"
                content_bytes = b"".join(volume.read_file(full_path))
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
