"""
Application State Manager
Manages state for multiple concurrent projects
"""
from typing import Dict, Optional, Set
from datetime import datetime
import asyncio

from app.models.conversation import ConversationState
from app.core.sandbox_provider import SandboxProvider, E2BSandboxProvider, VercelSandboxProvider
from app.config.settings import settings


class ProjectContext:
    """Project-scoped context for managing sandbox and conversation state"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.sandbox_providers: Dict[str, SandboxProvider] = {}
        self.conversation_state: Optional[ConversationState] = None
        self.file_cache: Dict[str, str] = {}
        self.existing_files: Set[str] = set()
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()

    def get_sandbox_provider(self, sandbox_id: Optional[str] = None) -> Optional[SandboxProvider]:
        """Get sandbox provider by ID or return the first one"""
        self.last_accessed = datetime.now()

        if sandbox_id and sandbox_id in self.sandbox_providers:
            return self.sandbox_providers[sandbox_id]

        # Return first available sandbox
        if self.sandbox_providers:
            return next(iter(self.sandbox_providers.values()))

        return None

    def register_sandbox(self, sandbox_id: str, provider: SandboxProvider) -> None:
        """Register a new sandbox provider"""
        self.sandbox_providers[sandbox_id] = provider
        self.last_accessed = datetime.now()

    def get_conversation_state(self) -> ConversationState:
        """Get or create conversation state"""
        if not self.conversation_state:
            self.conversation_state = ConversationState(project_id=self.project_id)

        self.last_accessed = datetime.now()
        return self.conversation_state

    def update_file_cache(self, file_path: str, content: str) -> None:
        """Update file cache"""
        self.file_cache[file_path] = content
        self.existing_files.add(file_path)
        self.last_accessed = datetime.now()

    async def cleanup(self) -> None:
        """Cleanup all sandboxes for this project"""
        for sandbox_id, provider in self.sandbox_providers.items():
            try:
                await provider.terminate()
            except Exception as e:
                print(f"Error terminating sandbox {sandbox_id}: {e}")
        self.sandbox_providers.clear()


class AppStateManager:
    """Global application state manager for multi-project support"""

    def __init__(self):
        self._projects: Dict[str, ProjectContext] = {}
        self._lock = asyncio.Lock()

    def for_project(self, project_id: str) -> ProjectContext:
        """Get or create project context"""
        if project_id not in self._projects:
            self._projects[project_id] = ProjectContext(project_id)

        return self._projects[project_id]

    async def create_sandbox(self, project_id: str, sandbox_id: str,
                            provider_type: Optional[str] = None) -> SandboxProvider:
        """Create a new sandbox for a project"""
        async with self._lock:
            context = self.for_project(project_id)

            provider_type = provider_type or settings.SANDBOX_PROVIDER

            if provider_type == "e2b":
                if not settings.E2B_API_KEY:
                    raise ValueError("E2B_API_KEY not configured")

                provider = E2BSandboxProvider(
                    sandbox_id=sandbox_id,
                    api_key=settings.E2B_API_KEY,
                    timeout_minutes=settings.E2B_TIMEOUT_MINUTES
                )
            elif provider_type == "vercel":
                if not settings.VERCEL_TOKEN:
                    raise ValueError("VERCEL_TOKEN not configured")

                provider = VercelSandboxProvider(
                    sandbox_id=sandbox_id,
                    token=settings.VERCEL_TOKEN,
                    team_id=settings.VERCEL_TEAM_ID,
                    timeout_minutes=settings.VERCEL_TIMEOUT_MINUTES
                )
            else:
                raise ValueError(f"Unknown sandbox provider: {provider_type}")

            context.register_sandbox(sandbox_id, provider)
            return provider

    async def cleanup_project(self, project_id: str) -> None:
        """Cleanup a specific project"""
        if project_id in self._projects:
            await self._projects[project_id].cleanup()
            del self._projects[project_id]

    async def cleanup_all(self) -> None:
        """Cleanup all projects"""
        for project_id in list(self._projects.keys()):
            await self.cleanup_project(project_id)


# Global app state manager instance
app_state_manager = AppStateManager()
