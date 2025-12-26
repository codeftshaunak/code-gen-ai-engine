"""Project state management for tracking files and context."""

from typing import Dict, Set
from e2b_code_interpreter import Sandbox


class ProjectState:
    """Stores state for a single project."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.existing_files: Set[str] = set()
        self.file_contents: Dict[str, str] = {}  # path -> content
        self.created_at: float = 0
        self.last_accessed: float = 0


class ProjectStateManager:
    """Manages state across all projects."""

    def __init__(self):
        self._projects: Dict[str, ProjectState] = {}

    def get_project(self, project_id: str) -> ProjectState:
        """Get or create project state."""
        if project_id not in self._projects:
            self._projects[project_id] = ProjectState(project_id)
        return self._projects[project_id]

    def add_file(self, project_id: str, file_path: str, content: str = ""):
        """Track a file as existing in the project."""
        project = self.get_project(project_id)
        project.existing_files.add(file_path)
        if content:
            project.file_contents[file_path] = content

    def has_file(self, project_id: str, file_path: str) -> bool:
        """Check if file exists in project."""
        project = self.get_project(project_id)
        return file_path in project.existing_files

    def get_file_content(self, project_id: str, file_path: str) -> str:
        """Get cached file content."""
        project = self.get_project(project_id)
        return project.file_contents.get(file_path, "")

    def get_all_files(self, project_id: str) -> Dict[str, str]:
        """Get all files and their contents."""
        project = self.get_project(project_id)
        return project.file_contents.copy()

    def clear_project(self, project_id: str):
        """Clear all state for a project."""
        if project_id in self._projects:
            del self._projects[project_id]


# Global instance
project_state_manager = ProjectStateManager()
