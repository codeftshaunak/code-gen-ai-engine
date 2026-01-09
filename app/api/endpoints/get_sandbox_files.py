"""Get sandbox files endpoint."""

import re
import json
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Header
from app.api.endpoints.create_ai_sandbox_v2 import _sandboxes
from app.utils.project_state import project_state_manager


router = APIRouter()


def parse_javascript_file(content: str, file_path: str) -> dict:
    """Parse JavaScript/JSX file to extract component info."""
    file_info = {
        "type": "utility",
        "exports": [],
        "imports": []
    }

    # Extract exports
    export_pattern = r'export\s+(?:default\s+)?(?:function|const|class|let|var)?\s+(\w+)'
    exports = re.findall(export_pattern, content)
    file_info["exports"] = list(set(exports))

    # Identify component type
    if "export default" in content or exports:
        file_info["type"] = "component"

    # Extract imports - ES6 style
    import_pattern = r"import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)(?:\s*,\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+))*\s+from\s+)?['\"]([^'\"]+)['\"]"
    imports = []

    for match in re.finditer(import_pattern, content):
        import_path = match.group(1)

        # Skip relative imports and absolute paths
        if not import_path.startswith('.') and not import_path.startswith('/'):
            imports.append(import_path)

    file_info["imports"] = imports

    return file_info


def build_component_tree(files: Dict[str, dict]) -> dict:
    """Build component tree from file manifest."""
    component_tree = {}

    for file_path, file_info in files.items():
        if file_info.get("type") == "component" and file_info.get("exports"):
            for export_name in file_info["exports"]:
                component_tree[export_name] = {
                    "file": file_path,
                    "imports": file_info.get("imports", []),
                    "importedBy": [],
                    "type": "component"
                }

    # Build importedBy relationships
    for file_path, file_info in files.items():
        for import_name in file_info.get("imports", []):
            for comp_name, comp_info in component_tree.items():
                if comp_name in import_name or import_name in comp_name:
                    if file_path not in comp_info.get("importedBy", []):
                        comp_info["importedBy"].append(file_path)

    return component_tree


def extract_routes(files: Dict[str, dict]) -> List[dict]:
    """Extract route definitions from files."""
    routes = []

    for file_path, file_info in files.items():
        content = file_info.get("content", "")

        # Look for React Router usage
        if "<Route" in content or "createBrowserRouter" in content:
            # Extract route definitions
            route_pattern = r'path=["\'](.*?)["\']'
            route_matches = re.findall(route_pattern, content)

            for route_path in route_matches:
                if route_path and route_path not in [r.get("path") for r in routes]:
                    routes.append({
                        "path": route_path,
                        "component": file_path
                    })

        # Check for Next.js style pages
        if "/pages/" in file_path:
            # Extract route from file path
            route_path = (
                "/" + file_info.get("relativePath", "")
                .replace("pages/", "")
                .replace(".jsx", "")
                .replace(".js", "")
                .replace(".tsx", "")
                .replace(".ts", "")
                .replace("index", "")
            )

            if route_path not in [r.get("path") for r in routes]:
                routes.append({
                    "path": route_path or "/",
                    "component": file_path
                })

    return routes


@router.get("/get-sandbox-files")
async def get_sandbox_files(
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Retrieve all files from the sandbox environment.

    This endpoint fetches all relevant files from the sandbox, analyzes their
    structure, builds a file manifest with component relationships, and returns
    the complete file tree.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Returns:
        JSON response with files, directory structure, file count, and manifest

    Example:
        ```bash
        curl -X GET http://localhost:3100/api/get-sandbox-files \
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
          "structure": "src/\\nsrc/components/\\npublic/",
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
        print(f"[get-sandbox-files] Using project: {project_id}")

        # Get sandbox instance
        sandbox = _sandboxes.get(project_id)

        if not sandbox:
            return {
                "success": False,
                "projectId": project_id,
                "error": "No active sandbox"
            }, 404

        print("[get-sandbox-files] Fetching and analyzing file structure...")

        # Get list of all relevant files (exclude node_modules, .git, dist, build)
        find_cmd = "find . \\( -name node_modules -o -name .git -o -name dist -o -name build \\) -prune -o -type f \\( -name '*.jsx' -o -name '*.js' -o -name '*.tsx' -o -name '*.ts' -o -name '*.css' -o -name '*.json' -o -name '*.html' \\) -print"

        # Run find command in sandbox
        result = sandbox.run_code(f"""
import subprocess
import os
import json

os.chdir('/home/user/app')
proc = subprocess.run(['bash', '-lc', {repr(find_cmd)}], capture_output=True, text=True)
print(json.dumps({{'stdout': proc.stdout, 'stderr': proc.stderr, 'returncode': proc.returncode}}))
""")

        # Parse the JSON output
        raw_stdout = ''.join(result.logs.stdout) if hasattr(result.logs, 'stdout') else str(result)
        
        try:
            cmd_result = json.loads(raw_stdout)
            output = cmd_result.get('stdout', '')
        except:
            output = raw_stdout

        file_list = [f.strip() for f in output.split('\n') if f.strip()]

        print(f"[get-sandbox-files] Found {len(file_list)} files")

        # Read content of each file (limit to reasonable sizes)
        files_content: Dict[str, str] = {}

        for file_path in file_list:
            try:
                # Check file size first
                stat_cmd = f"stat -c %s \"{file_path}\""
                size_result = sandbox.run_code(f"""
import subprocess
import os
import json

os.chdir('/home/user/app')
proc = subprocess.run(['bash', '-lc', {repr(stat_cmd)}], capture_output=True, text=True)
print(json.dumps({{'stdout': proc.stdout, 'stderr': proc.stderr, 'returncode': proc.returncode}}))
""")

                # Parse result
                raw_stdout = ''.join(size_result.logs.stdout) if hasattr(size_result.logs, 'stdout') else str(size_result)
                
                try:
                    cmd_result = json.loads(raw_stdout)
                    size_output = cmd_result.get('stdout', '').strip()
                    exit_code = cmd_result.get('returncode', 1)
                except:
                    size_output = raw_stdout.strip()
                    exit_code = 1

                if exit_code != 0:
                    continue

                file_size = 0
                try:
                    file_size = int(size_output)
                except:
                    continue

                # Only read files smaller than 10KB
                if file_size < 10000:
                    cat_cmd = f"cat \"{file_path}\""
                    cat_result = sandbox.run_code(f"""
import subprocess
import os
import json

os.chdir('/home/user/app')
proc = subprocess.run(['bash', '-lc', {repr(cat_cmd)}], capture_output=True, text=True)
print(json.dumps({{'stdout': proc.stdout, 'stderr': proc.stderr, 'returncode': proc.returncode}}))
""")

                    # Parse result
                    raw_stdout = ''.join(cat_result.logs.stdout) if hasattr(cat_result.logs, 'stdout') else str(cat_result)
                    
                    try:
                        cmd_result = json.loads(raw_stdout)
                        content = cmd_result.get('stdout', '')
                        exit_code = cmd_result.get('returncode', 1)
                    except:
                        content = raw_stdout
                        exit_code = 1

                    if exit_code == 0:
                        # Remove leading './' from path
                        relative_path = file_path.replace('./', '')
                        files_content[relative_path] = content

            except Exception as e:
                print(f"[get-sandbox-files] Error reading {file_path}: {e}")
                continue

        # Get directory structure
        tree_cmd = "find . -type d -not -path '*/node_modules*' -not -path '*/.git*'"
        tree_result = sandbox.run_code(f"""
import subprocess
import os
import json

os.chdir('/home/user/app')
proc = subprocess.run(['bash', '-lc', {repr(tree_cmd)}], capture_output=True, text=True)
print(json.dumps({{'stdout': proc.stdout, 'stderr': proc.stderr, 'returncode': proc.returncode}}))
""")

        # Parse result
        raw_stdout = ''.join(tree_result.logs.stdout) if hasattr(tree_result.logs, 'stdout') else str(tree_result)
        
        try:
            cmd_result = json.loads(raw_stdout)
            tree_output = cmd_result.get('stdout', '')
        except:
            tree_output = raw_stdout

        # Limit to 50 lines
        dirs = [d for d in tree_output.split('\n') if d.strip()]
        structure = '\n'.join(dirs[:50])

        # Build enhanced file manifest
        file_manifest = {
            "files": {},
            "routes": [],
            "componentTree": {},
            "entryPoint": "",
            "styleFiles": [],
            "timestamp": 0
        }

        # Process each file
        for relative_path, content in files_content.items():
            full_path = f"/{relative_path}"

            # Create base file info
            file_info = {
                "content": content,
                "type": "utility",
                "path": full_path,
                "relativePath": relative_path,
                "lastModified": 0
            }

            # Parse JavaScript/JSX files
            if relative_path.endswith(('.jsx', '.js', '.tsx', '.ts')):
                parse_result = parse_javascript_file(content, full_path)
                file_info.update(parse_result)

                # Identify entry point
                if relative_path in ("src/main.jsx", "src/index.jsx", "src/main.tsx"):
                    file_manifest["entryPoint"] = full_path

                # Identify App.jsx
                if relative_path in ("src/App.jsx", "App.jsx", "src/App.tsx"):
                    if not file_manifest["entryPoint"]:
                        file_manifest["entryPoint"] = full_path

            # Track style files
            if relative_path.endswith('.css'):
                file_manifest["styleFiles"].append(full_path)
                file_info["type"] = "style"

            file_manifest["files"][full_path] = file_info

        # Build component tree
        file_manifest["componentTree"] = build_component_tree(file_manifest["files"])

        # Extract routes
        file_manifest["routes"] = extract_routes(file_manifest["files"])

        # Set timestamp
        import time
        file_manifest["timestamp"] = int(time.time() * 1000)

        # Update project state
        project_state_manager.get_project(project_id)

        print(f"[get-sandbox-files] Successfully retrieved {len(files_content)} files")

        return {
            "success": True,
            "projectId": project_id,
            "files": files_content,
            "structure": structure,
            "fileCount": len(files_content),
            "manifest": file_manifest
        }

    except Exception as e:
        print(f"[get-sandbox-files] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
