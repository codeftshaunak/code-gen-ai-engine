"""Create AI sandbox endpoint (v2) with E2B SDK integration."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict
from app.config.settings import settings
from e2b_code_interpreter import Sandbox
import asyncio

# Import project state manager for tracking files
from app.utils.project_state import project_state_manager


router = APIRouter()

# Global sandbox storage shared across endpoints (keyed by project_id)
_sandboxes: Dict[str, Sandbox] = {}


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


async def create_e2b_sandbox_with_vite(project_id: str = "default") -> dict:
    """Create E2B sandbox and setup Vite React app using SDK."""

    import os
    # Set E2B API key as environment variable
    os.environ["E2B_API_KEY"] = settings.E2B_API_KEY

    # Create E2B sandbox (timeout in seconds, 600000ms = 600s = 10min)
    sandbox = Sandbox.create(timeout=600)

    # Get sandbox ID and host URL
    sandbox_id = sandbox.sandbox_id
    host = sandbox.get_host(5173)  # Port 5173 for Vite
    url = f"https://{host}"

    print(f"[E2B] Sandbox created: {sandbox_id}")
    print(f"[E2B] Host URL: {url}")

    # Setup Vite React app with Tailwind
    setup_script = """
import os
import json

print('Setting up React app with Vite and Tailwind...')

# Create directory structure
os.makedirs('/home/user/app/src', exist_ok=True)

# Package.json
package_json = {
    "name": "sandbox-app",
    "version": "1.0.0",
    "type": "module",
    "scripts": {
        "dev": "vite --host",
        "build": "vite build",
        "preview": "vite preview"
    },
    "dependencies": {
        "react": "^18.2.0",
        "react-dom": "^18.2.0"
    },
    "devDependencies": {
        "@vitejs/plugin-react": "^4.0.0",
        "vite": "^4.3.9",
        "tailwindcss": "^3.3.0",
        "postcss": "^8.4.31",
        "autoprefixer": "^10.4.16"
    }
}

with open('/home/user/app/package.json', 'w') as f:
    json.dump(package_json, f, indent=2)
print('✓ package.json')

# Vite config
vite_config = \"\"\"import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    hmr: false,
    allowedHosts: ['.e2b.app', '.e2b.dev', '.vercel.run', 'localhost', '127.0.0.1']
  }
})\"\"\"

with open('/home/user/app/vite.config.js', 'w') as f:
    f.write(vite_config)
print('✓ vite.config.js')

# Tailwind config
tailwind_config = \"\"\"/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}\"\"\"

with open('/home/user/app/tailwind.config.js', 'w') as f:
    f.write(tailwind_config)
print('✓ tailwind.config.js')

# PostCSS config
postcss_config = \"\"\"export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}\"\"\"

with open('/home/user/app/postcss.config.js', 'w') as f:
    f.write(postcss_config)
print('✓ postcss.config.js')

# Index.html
index_html = \"\"\"<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Sandbox App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>\"\"\"

with open('/home/user/app/index.html', 'w') as f:
    f.write(index_html)
print('✓ index.html')

# Main.jsx
main_jsx = \"\"\"import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)\"\"\"

with open('/home/user/app/src/main.jsx', 'w') as f:
    f.write(main_jsx)
print('✓ src/main.jsx')

# App.jsx
app_jsx = \"\"\"function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center p-4">
      <div className="text-center max-w-2xl">
        <p className="text-lg text-gray-400">
          Sandbox Ready<br/>
          Start building your React app with Vite and Tailwind CSS!
        </p>
      </div>
    </div>
  )
}

export default App\"\"\"

with open('/home/user/app/src/App.jsx', 'w') as f:
    f.write(app_jsx)
print('✓ src/App.jsx')

# Index.css
index_css = \"\"\"@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background-color: rgb(17 24 39);
}\"\"\"

with open('/home/user/app/src/index.css', 'w') as f:
    f.write(index_css)
print('✓ src/index.css')

print('\\nAll files created successfully!')
"""

    print("[E2B] Creating Vite app files...")
    result = sandbox.run_code(setup_script)
    print(f"[E2B] Setup output: {result.logs.stdout}")

    # Install dependencies
    print("[E2B] Installing npm packages...")
    install_result = sandbox.run_code("""
import subprocess

print('Installing npm packages...')
result = subprocess.run(
    ['npm', 'install'],
    cwd='/home/user/app',
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print('✓ Dependencies installed successfully')
else:
    print(f'⚠ Warning: npm install had issues: {result.stderr}')
""")
    print(f"[E2B] Install output: {install_result.logs.stdout}")

    # Start Vite dev server
    print("[E2B] Starting Vite dev server...")
    start_result = sandbox.run_code("""
import subprocess
import os
import time

os.chdir('/home/user/app')

# Kill any existing Vite processes
subprocess.run(['pkill', '-f', 'vite'], capture_output=True)
time.sleep(1)

# Start Vite dev server
env = os.environ.copy()
env['FORCE_COLOR'] = '0'

process = subprocess.Popen(
    ['npm', 'run', 'dev'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env
)

print(f'✓ Vite dev server started with PID: {process.pid}')
print('Waiting for server to be ready...')
""")
    print(f"[E2B] Vite start output: {start_result.logs.stdout}")

    # Wait for Vite to be ready
    await asyncio.sleep(5)

    # Track initial files in project state
    initial_app_jsx = """function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center p-4">
      <div className="text-center max-w-2xl">
        <p className="text-lg text-gray-400">
          Sandbox Ready<br/>
          Start building your React app with Vite and Tailwind CSS!
        </p>
      </div>
    </div>
  )
}

export default App"""

    initial_main_jsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""

    initial_index_css = """@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background-color: rgb(17 24 39);
}"""

    # Track all initial files
    project_state_manager.add_file(project_id, "src/App.jsx", initial_app_jsx)
    project_state_manager.add_file(project_id, "src/main.jsx", initial_main_jsx)
    project_state_manager.add_file(project_id, "src/index.css", initial_index_css)

    return {
        "sandbox_id": sandbox_id,
        "url": url,
        "sandbox": sandbox
    }


@router.post("/create-ai-sandbox-v2")
async def create_ai_sandbox_v2(
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Create a new AI sandbox for code execution and preview using E2B.

    This endpoint creates an E2B sandbox environment with Vite React app.

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
          "url": "https://sb-abc123-5173.e2b.dev",
          "provider": "e2b",
          "message": "E2B Sandbox created and Vite React app initialized"
        }
        ```
    """
    try:
        project_id = x_project_id or "default"

        print(f"[create-ai-sandbox-v2] Creating E2B sandbox for project: {project_id}")

        # Check if E2B API key is configured
        if not settings.E2B_API_KEY:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "E2B_API_KEY not configured",
                    "details": "Please set E2B_API_KEY in your .env file"
                }
            )

        # Create E2B sandbox with Vite app
        print(f"[create-ai-sandbox-v2] Creating sandbox with Vite app...")
        result = await create_e2b_sandbox_with_vite(project_id)

        sandbox_id = result["sandbox_id"]
        sandbox_url = result["url"]
        sandbox = result["sandbox"]

        # Store sandbox globally for other endpoints to use
        _sandboxes[project_id] = sandbox

        print(f"[create-ai-sandbox-v2] E2B sandbox created successfully")
        print(f"[create-ai-sandbox-v2] Sandbox ID: {sandbox_id}")
        print(f"[create-ai-sandbox-v2] URL: {sandbox_url}")
        print(f"[create-ai-sandbox-v2] Stored sandbox for project: {project_id}")

        return {
            "success": True,
            "projectId": project_id,
            "sandboxId": sandbox_id,
            "url": sandbox_url,
            "provider": "e2b",
            "message": "E2B Sandbox created and Vite React app initialized"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[create-ai-sandbox-v2] Error: {e}")

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e) if isinstance(e, Exception) else "Failed to create E2B sandbox",
                "details": str(e)
            }
        )
