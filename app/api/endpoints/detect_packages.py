"""
Detect and Install Packages Endpoint
Automatically detects and installs packages from file imports
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Set, List

from app.models.api_models import DetectPackagesRequest, DetectPackagesResponse
from app.core.app_state_manager import app_state_manager
from app.utils.project_utils import get_project_id
from app.utils.code_parser import detect_packages_from_code

router = APIRouter()


@router.post(
    "/detect-and-install-packages",
    response_model=DetectPackagesResponse,
    summary="Detect and Install Packages",
    description="""
    Automatically detect and install packages from file imports.

    **Features:**
    - Parses ES6 imports and CommonJS requires
    - Filters out relative imports and built-in Node modules
    - Extracts scoped package names (@scope/package)
    - Checks which packages are already installed
    - Returns list of packages that need installation
    - Smart handling of subpaths in package imports

    **Supported Import Formats:**
    - `import X from 'package'`
    - `import { X } from 'package'`
    - `import 'package'` (side-effect)
    - `const X = require('package')`
    - `@scope/package` (scoped packages)
    - `package/subpath` → extracts `package`

    **Request Headers:**
    - `X-Project-Id`: Required project identifier

    **Response:**
    - `packages_installed`: List of newly installed packages
    - `packages_already_installed`: List of packages already present
    - `success`: Operation status
    - `message`: Status message
    """
)
async def detect_and_install_packages(
    request: DetectPackagesRequest,
    project_id: str = Depends(get_project_id)
) -> DetectPackagesResponse:
    """Detect packages from file imports and check installation status"""
    try:
        # Get project context
        context = app_state_manager.for_project(project_id)
        sandbox = context.get_sandbox_provider()

        if not sandbox:
            raise HTTPException(
                status_code=400,
                detail="No sandbox found. Please create a sandbox first."
            )

        # Detect packages from code
        detected_packages = detect_packages_from_code(request.files)

        if not detected_packages:
            return DetectPackagesResponse(
                success=True,
                packages_installed=[],
                packages_already_installed=[],
                message="No packages detected in provided files"
            )

        # Check which packages are already installed
        already_installed: Set[str] = set()
        need_installation: List[str] = []

        try:
            package_json_content = await sandbox.read_file("package.json")
            import json
            package_json = json.loads(package_json_content)

            existing_deps = set(package_json.get("dependencies", {}).keys())
            existing_dev_deps = set(package_json.get("devDependencies", {}).keys())
            all_existing = existing_deps | existing_dev_deps

            for pkg in detected_packages:
                if pkg in all_existing:
                    already_installed.add(pkg)
                else:
                    need_installation.append(pkg)

        except Exception:
            # If package.json doesn't exist, all packages need installation
            need_installation = detected_packages

        return DetectPackagesResponse(
            success=True,
            packages_installed=need_installation,
            packages_already_installed=list(already_installed),
            message=f"Detected {len(detected_packages)} packages. {len(need_installation)} need installation."
        )

    except Exception as e:
        return DetectPackagesResponse(
            success=False,
            packages_installed=[],
            packages_already_installed=[],
            message=f"Failed to detect packages: {str(e)}"
        )
