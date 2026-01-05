"""Create sandbox endpoint with Modal SDK integration."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict
from app.config.settings import settings
import asyncio
import os
import modal
import logging

# Import project state manager for tracking files
from app.utils.project_state import project_state_manager

# Suppress hpack debug logs
logging.getLogger('hpack.hpack').setLevel(logging.WARNING)

# Global sandbox storage shared across endpoints (keyed by project_id)
_sandboxes: Dict[str, Dict[str, any]] = {}


router = APIRouter()


class SandboxResponse(BaseModel):
    """Response model for sandbox creation."""

    success: bool
    project_id: str
    sandbox_id: str
    url: str
    provider: str
    message: str
    access_instructions: Optional[str] = None
    volume_path: Optional[str] = None
    error: Optional[str] = None
    details: Optional[str] = None


MODAL_APP_NAME = "vite-preview-platform"

VITE_IMAGE = modal.Image.from_registry("node:20-slim")

async def create_modal_sandbox_with_vite(project_id: str = "default") -> dict:
    """Create Modal sandbox and setup Vite React app using SDK."""

    # Set Modal API key as environment variable
    os.environ["MODAL_TOKEN_ID"] = settings.MODAL_API_KEY.split(":")[0] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else settings.MODAL_API_KEY or ""
    os.environ["MODAL_TOKEN_SECRET"] = settings.MODAL_API_KEY.split(":")[1] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else ""

    # Create or lookup Modal app
    modal_app = modal.App.lookup(MODAL_APP_NAME, create_if_missing=True)

    # Create a volume for persistent file storage (one per project)
    volume_name = f"{project_id}"
    volume = modal.Volume.from_name(volume_name, create_if_missing=True)


    # Create sandbox with timeout of 10 minutes (600 seconds)
    print(f"[Modal] Creating sandbox for project: {project_id}")

    # Note: This function should only be called when no active sandbox exists
    # The endpoint already checks for existing sandboxes before calling this function

    # Create new sandbox
    sandbox = modal.Sandbox.create(
        app=modal_app,
        name=project_id,
        image=VITE_IMAGE,
        timeout=6000,
        workdir="/home/user/app",
        volumes={
            "/home/user/app": volume,  # Mount volume for entire app directory for persistence
        },
        encrypted_ports=[5173],  # Expose port 5173 with HTTPS tunnel
    )

    # Get sandbox ID
    sandbox_id = sandbox.object_id

    print(f"[Modal] Sandbox created: {sandbox_id}")

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
        "dev": "vite --host --port 5173",
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
    allowedHosts: ['.modal.host', '.modal.run', '.modal.sh', 'localhost', '127.0.0.1']
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
    <title>Upfounder AI App</title>
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
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="text-center max-w-md w-full">
        <div className="mb-6">
          <svg className="w-16 h-16 mx-auto text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Environment Ready</h1>
        <p className="text-gray-600 mb-4">
          Your development environment is set up and running. Start building your React application with Vite and Tailwind CSS.
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
  background-color: #f8fafc;
}\"\"\"

with open('/home/user/app/src/index.css', 'w') as f:
    f.write(index_css)
print('✓ src/index.css')

print('\\nAll files created successfully!')
"""

    print("[Modal] Creating Vite app files...")
    process = sandbox.exec("python", "-c", setup_script, timeout=30)
    stdout = process.stdout.read()
    print(f"[Modal] Setup output: {stdout}")

    # Install dependencies
    print("[Modal] Installing npm packages...")
    install_process = sandbox.exec(
        "bash", "-c",
        "cd /home/user/app && npm install",
        timeout=180
    )
    install_output = install_process.stdout.read()
    print(f"[Modal] Install output: {install_output}")

    # Start Vite dev server as a long-running process to keep the sandbox active
    print("[Modal] Starting Vite dev server (long-running exec)...")
    start_cmd = "cd /home/user/app && npm run dev -- --host --port 5173"
    # Do not set a short timeout; we want this to keep running
    vite_proc = sandbox.exec("bash", "-lc", start_cmd)
    print("[Modal] Vite dev server process started")

    # Wait longer for Vite to be ready
    await asyncio.sleep(8)

    # Get the tunnel URL for accessing the Vite dev server
    print("[Modal] Getting tunnel URL for port 5173...")
    tunnel_url = None
    try:
        tunnels = sandbox.tunnels()
        if 5173 in tunnels:
            tunnel = tunnels[5173]
            tunnel_url = tunnel.url
            print(f"[Modal] Tunnel URL: {tunnel_url}")

            # Verify the server is responding from inside the sandbox
            print("[Modal] Verifying Vite server is running...")
            verify_process = sandbox.exec("bash", "-lc", "curl -s -o /dev/null -w '%{http_code}' http://localhost:5173", timeout=10)
            status_code = (verify_process.stdout.read() or "").strip()
            print(f"[Modal] Vite server status: {status_code}")
        else:
            tunnel_url = ""
            print("[Modal] Warning: No tunnel available for port 5173")
    except Exception as e:
        tunnel_url = ""
        print(f"[Modal] Error getting tunnel: {e}")

    # Commit volume to persist files
    print("[Modal] Committing volume to persist files...")
    try:
        volume.commit()
        print("[Modal] Volume committed successfully")
    except Exception as e:
        print(f"[Modal] Warning: Could not commit volume: {e}")

    # Track initial files in project state
    initial_app_jsx = """function App() {
  return (
    <div className="min-h-screen bg-blue-50 flex items-center justify-center p-4">
      <div className="text-center max-w-md w-full">
        <div className="mb-6">
          <svg className="w-16 h-16 mx-auto text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Sandbox Ready</h1>
        <p className="text-gray-600 mb-4">
          Your development environment is set up and running. Start building your React application with Vite and Tailwind CSS.
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
  background-color: #f8fafc;
}"""

    # Track all initial files
    # project_state_manager.add_file(project_id, "src/App.jsx", initial_app_jsx)
    # project_state_manager.add_file(project_id, "src/main.jsx", initial_main_jsx)
    # project_state_manager.add_file(project_id, "src/index.css", initial_index_css)

    return {
        "sandbox_id": sandbox_id,
        "url": tunnel_url,
        "sandbox": sandbox,
        "volume": volume,
        "volume_name": volume_name
    }


@router.post("/create-sandbox-modal")
async def create_sandbox(
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Create a new sandbox for code execution and preview using Modal.

    This endpoint creates a Modal sandbox environment with Vite React app.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Returns:
        JSON response with sandbox details including URL and sandbox ID

    Example:
        ```bash
        curl -X POST http://localhost:3100/api/create-sandbox \
          -H "X-Project-Id: my-project-123"
        ```

    Response:
        ```json
        {
          "success": true,
          "projectId": "my-project-123",
          "sandboxId": "sb-abc123",
          "url": "https://randomurl.modal.host",
          "provider": "modal",
          "message": "Sandbox created and Vite React app initialized"
        }
        ```
    """
    try:
        project_id = x_project_id or "default"

        print(f"[create-sandbox] Checking for existing sandbox for project: {project_id}")

        # Check if Modal API key is configured
        if not settings.MODAL_API_KEY:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "MODAL_API_KEY not configured",
                    "details": "Please set MODAL_API_KEY in your .env file"
                }
            )

        # Set Modal API key as environment variable
        os.environ["MODAL_TOKEN_ID"] = settings.MODAL_API_KEY.split(":")[0] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else settings.MODAL_API_KEY or ""
        os.environ["MODAL_TOKEN_SECRET"] = settings.MODAL_API_KEY.split(":")[1] if settings.MODAL_API_KEY and ":" in settings.MODAL_API_KEY else ""

        # Always check Modal service directly for existing active sandbox
        print(f"[create-sandbox] Querying Modal service for active sandbox...")
        existing_sandbox = None
        should_create_new = False

        try:
            # Lookup sandbox by name from Modal service
            existing_sandbox = modal.Sandbox.from_name(MODAL_APP_NAME, project_id)

            if existing_sandbox is not None:
                print(f"[create-sandbox] Found sandbox in Modal: {existing_sandbox.object_id}")

                # Verify the sandbox is actually running by checking its tunnels
                # This communicates directly with Modal service to verify active state
                try:
                    tunnels = existing_sandbox.tunnels()

                    if tunnels and 5173 in tunnels:
                        existing_url = tunnels[5173].url
                        sandbox_id = existing_sandbox.object_id

                        print(f"[create-sandbox] Sandbox is active with tunnel URL: {existing_url}")

                        # Store in memory for other endpoints to access
                        volume_name = f"{project_id}"
                        try:
                            volume = modal.Volume.from_name(volume_name, create_if_missing=False)
                        except:
                            volume = modal.Volume.from_name(volume_name, create_if_missing=True)

                        _sandboxes[project_id] = {
                            "sandbox": existing_sandbox,
                            "volume": volume,
                            "volume_name": volume_name,
                            "sandbox_id": sandbox_id
                        }

                        return {
                            "success": True,
                            "projectId": project_id,
                            "sandboxId": sandbox_id,
                            "url": existing_url,
                            "provider": "modal",
                            "message": "Active sandbox already exists"
                        }
                    else:
                        print(f"[create-sandbox] Sandbox exists but no active tunnels found, will create new sandbox")
                        should_create_new = True
                except Exception as e:
                    print(f"[create-sandbox] Could not get tunnels for existing sandbox: {e}, will create new sandbox")
                    should_create_new = True
            else:
                print(f"[create-sandbox] from_name returned None, no existing sandbox")
                should_create_new = True

        except Exception as e:
            error_msg = str(e).lower()
            # If sandbox is not found, that's expected - we'll create a new one
            if "not found" in error_msg or "does not exist" in error_msg:
                print(f"[create-sandbox] No existing sandbox found in Modal service (expected)")
                should_create_new = True
            else:
                # Other errors (auth, network, etc.) should be raised
                print(f"[create-sandbox] Error checking for existing sandbox: {e}")
                raise

        # No active sandbox exists, create a new one
        print(f"[create-sandbox] Creating new Modal sandbox for project: {project_id}")
        print(f"[create-sandbox] Creating sandbox with Vite app...")
        result = await create_modal_sandbox_with_vite(project_id)

        # Store sandbox and volume for later file access
        _sandboxes[project_id] = {
            "sandbox": result["sandbox"],
            "volume": result["volume"],
            "volume_name": result["volume_name"],
            "sandbox_id": result["sandbox_id"]
        }

        sandbox_id = result["sandbox_id"]
        sandbox_url = result["url"]

        print(f"[create-sandbox] Modal sandbox created successfully")
        print(f"[create-sandbox] Sandbox ID: {sandbox_id}")
        print(f"[create-sandbox] URL: {sandbox_url}")
        print(f"[create-sandbox] Stored sandbox for project: {project_id}")

        return {
          "success": True,
          "projectId": project_id,
          "sandboxId": sandbox_id,
          "url": sandbox_url,
          "provider": "modal",
          "message": "Sandbox created and Vite React app initialized"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[create-sandbox] Error: {e}")

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e) if isinstance(e, Exception) else "Failed to create Modal sandbox",
                "details": str(e)
            }
        )


