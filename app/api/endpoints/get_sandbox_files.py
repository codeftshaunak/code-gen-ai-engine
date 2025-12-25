"""Get sandbox files endpoint."""

from typing import Dict
from fastapi import APIRouter, HTTPException, Header


router = APIRouter()


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

        # Simulate sandbox file retrieval
        # In a real implementation, this would:
        # 1. Connect to the sandbox provider
        # 2. Run find command to list all files
        # 3. Read content of each file
        # 4. Parse JavaScript files for imports/exports
        # 5. Build component tree and route manifest

        # Mock file structure for Vite React app
        files: Dict[str, str] = {
            "src/main.jsx": """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)""",
            "src/App.jsx": """import { useState } from 'react'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="App">
      <h1>Vite + React</h1>
      <button onClick={() => setCount(count + 1)}>
        count is {count}
      </button>
    </div>
  )
}

export default App""",
            "src/index.css": """body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto';
}""",
            "src/App.css": """.App {
  text-align: center;
}""",
            "package.json": """{
  "name": "vite-react-app",
  "version": "0.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "vite": "^4.4.5"
  }
}""",
            "index.html": """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + React</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>"""
        }

        structure = """src/
src/components/
public/"""

        # Build file manifest
        manifest = {
            "files": {
                f"/{path}": {
                    "content": content,
                    "type": "component" if ".jsx" in path else "style" if ".css" in path else "config",
                    "path": f"/{path}",
                    "relativePath": path,
                    "lastModified": 1766655000000,
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
            },
            "entryPoint": "/src/main.jsx",
            "styleFiles": ["/src/index.css", "/src/App.css"],
            "timestamp": 1766655000000
        }

        print(f"[get-sandbox-files] Found {len(files)} files")

        return {
            "success": True,
            "projectId": project_id,
            "files": files,
            "structure": structure,
            "fileCount": len(files),
            "manifest": manifest
        }

    except Exception as e:
        print(f"[get-sandbox-files] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
