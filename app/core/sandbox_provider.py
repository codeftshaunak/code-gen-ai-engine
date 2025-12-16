"""
Sandbox Provider Interface and Implementations
Supports E2B and Vercel sandboxes
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncIterator
import asyncio
import json


class SandboxProvider(ABC):
    """Abstract sandbox provider interface"""

    def __init__(self, sandbox_id: str):
        self.sandbox_id = sandbox_id
        self.is_terminated = False

    @abstractmethod
    async def setup_vite_app(self) -> None:
        """Setup Vite development environment"""
        pass

    @abstractmethod
    async def write_file(self, path: str, content: str) -> None:
        """Write file to sandbox"""
        pass

    @abstractmethod
    async def read_file(self, path: str) -> str:
        """Read file from sandbox"""
        pass

    @abstractmethod
    async def list_files(self, path: str = ".") -> List[str]:
        """List files in sandbox"""
        pass

    @abstractmethod
    async def run_command(self, command: str, timeout: int = 60) -> AsyncIterator[str]:
        """Run command and stream output"""
        pass

    @abstractmethod
    async def install_packages(self, packages: List[str]) -> AsyncIterator[str]:
        """Install npm packages with streaming output"""
        pass

    @abstractmethod
    async def restart_vite_server(self) -> AsyncIterator[str]:
        """Restart Vite development server"""
        pass

    @abstractmethod
    async def terminate(self) -> None:
        """Terminate the sandbox"""
        pass


class E2BSandboxProvider(SandboxProvider):
    """E2B Code Interpreter sandbox provider"""

    def __init__(self, sandbox_id: str, api_key: str, timeout_minutes: int = 20):
        super().__init__(sandbox_id)
        self.api_key = api_key
        self.timeout_minutes = timeout_minutes
        self.vite_process = None
        # Note: In production, use e2b_code_interpreter library
        # from e2b_code_interpreter import Sandbox
        # self.sandbox = Sandbox(api_key=api_key, timeout=timeout_minutes * 60)

    async def setup_vite_app(self) -> None:
        """Setup Vite app in E2B sandbox"""
        commands = [
            "npm create vite@latest . -- --template react",
            "npm install",
        ]
        for cmd in commands:
            async for _ in self.run_command(cmd):
                pass

    async def write_file(self, path: str, content: str) -> None:
        """Write file to E2B sandbox"""
        # Implementation with e2b library
        # self.sandbox.filesystem.write(path, content)
        pass

    async def read_file(self, path: str) -> str:
        """Read file from E2B sandbox"""
        # return self.sandbox.filesystem.read(path)
        return ""

    async def list_files(self, path: str = ".") -> List[str]:
        """List files in E2B sandbox"""
        # return self.sandbox.filesystem.list(path)
        return []

    async def run_command(self, command: str, timeout: int = 60) -> AsyncIterator[str]:
        """Run command in E2B sandbox with streaming"""
        # execution = self.sandbox.run_code(command)
        # for chunk in execution:
        #     yield chunk.text
        yield f"Running: {command}\n"

    async def install_packages(self, packages: List[str]) -> AsyncIterator[str]:
        """Install npm packages in E2B sandbox"""
        if not packages:
            yield "No packages to install\n"
            return

        pkg_list = " ".join(packages)
        cmd = f"npm install {pkg_list} --legacy-peer-deps"

        async for output in self.run_command(cmd, timeout=120):
            yield output

    async def restart_vite_server(self) -> AsyncIterator[str]:
        """Restart Vite server in E2B sandbox"""
        if self.vite_process:
            yield "Stopping Vite server...\n"
            # Stop existing process

        yield "Starting Vite server...\n"
        cmd = "npm run dev -- --host 0.0.0.0 --port 5173"
        async for output in self.run_command(cmd):
            yield output

    async def terminate(self) -> None:
        """Terminate E2B sandbox"""
        if not self.is_terminated:
            # self.sandbox.close()
            self.is_terminated = True


class VercelSandboxProvider(SandboxProvider):
    """Vercel sandbox provider"""

    def __init__(self, sandbox_id: str, token: str, team_id: Optional[str] = None,
                 timeout_minutes: int = 20):
        super().__init__(sandbox_id)
        self.token = token
        self.team_id = team_id
        self.timeout_minutes = timeout_minutes
        # Note: In production, use @vercel/sandbox library
        # from vercel_sandbox import Sandbox
        # self.sandbox = Sandbox(token=token, team_id=team_id)

    async def setup_vite_app(self) -> None:
        """Setup Vite app in Vercel sandbox"""
        commands = [
            "npm create vite@latest . -- --template react",
            "npm install",
        ]
        for cmd in commands:
            async for _ in self.run_command(cmd):
                pass

    async def write_file(self, path: str, content: str) -> None:
        """Write file to Vercel sandbox"""
        pass

    async def read_file(self, path: str) -> str:
        """Read file from Vercel sandbox"""
        return ""

    async def list_files(self, path: str = ".") -> List[str]:
        """List files in Vercel sandbox"""
        return []

    async def run_command(self, command: str, timeout: int = 60) -> AsyncIterator[str]:
        """Run command in Vercel sandbox"""
        yield f"Running: {command}\n"

    async def install_packages(self, packages: List[str]) -> AsyncIterator[str]:
        """Install npm packages in Vercel sandbox"""
        if not packages:
            yield "No packages to install\n"
            return

        pkg_list = " ".join(packages)
        cmd = f"npm install {pkg_list} --legacy-peer-deps"

        async for output in self.run_command(cmd, timeout=120):
            yield output

    async def restart_vite_server(self) -> AsyncIterator[str]:
        """Restart Vite server in Vercel sandbox"""
        yield "Restarting Vite server...\n"
        cmd = "npm run dev"
        async for output in self.run_command(cmd):
            yield output

    async def terminate(self) -> None:
        """Terminate Vercel sandbox"""
        if not self.is_terminated:
            self.is_terminated = True
