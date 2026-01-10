"""Conversation state models for tracking chat history and edits."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from dataclasses import dataclass, field


class ConversationMessage(BaseModel):
    """A single message in the conversation."""

    id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: int
    metadata: Optional[Dict[str, Any]] = None


class ConversationEdit(BaseModel):
    """A record of an edit operation."""

    timestamp: int
    user_request: str = Field(..., alias="userRequest")
    edit_type: str = Field(..., alias="editType")
    target_files: List[str] = Field(default_factory=list, alias="targetFiles")
    confidence: float = 1.0
    outcome: Literal["success", "partial", "failed"] = "success"


class ProjectEvolution(BaseModel):
    """Major changes in project development."""

    timestamp: int
    description: str
    files_affected: List[str] = Field(default_factory=list, alias="filesAffected")


class UserPreferences(BaseModel):
    """User preferences learned from conversation."""

    edit_style: Literal["targeted", "comprehensive"] = Field("targeted", alias="editStyle")
    common_patterns: List[str] = Field(default_factory=list, alias="commonPatterns")


class ConversationContext(BaseModel):
    """Context for the conversation."""

    messages: List[ConversationMessage] = Field(default_factory=list)
    edits: List[ConversationEdit] = Field(default_factory=list)
    project_evolution: List[ProjectEvolution] = Field(default_factory=list, alias="projectEvolution")
    user_preferences: UserPreferences = Field(default_factory=UserPreferences, alias="userPreferences")
    current_topic: Optional[str] = Field(None, alias="currentTopic")
    # Project metadata for full-stack projects
    is_fullstack: bool = Field(default=False, alias="isFullstack", description="Whether this is a full-stack project with Supabase")
    supabase_config: Optional[Dict[str, Any]] = Field(default=None, alias="supabaseConfig", description="Supabase project configuration")


class ConversationState(BaseModel):
    """Complete conversation state for a project."""

    project_id: str = Field(..., alias="projectId")
    context: ConversationContext = Field(default_factory=ConversationContext)
    created_at: int = Field(..., alias="createdAt")
    updated_at: int = Field(..., alias="updatedAt")


@dataclass
class ConversationStateManager:
    """Manages conversation state for multiple projects."""

    _states: Dict[str, ConversationState] = field(default_factory=dict)

    def get_or_create(self, project_id: str) -> ConversationState:
        """Get or create conversation state for a project."""
        if project_id not in self._states:
            import time
            timestamp = int(time.time() * 1000)
            self._states[project_id] = ConversationState(
                projectId=project_id,
                createdAt=timestamp,
                updatedAt=timestamp
            )
        return self._states[project_id]

    def update(self, project_id: str, state: ConversationState):
        """Update conversation state for a project."""
        import time
        state.updated_at = int(time.time() * 1000)
        self._states[project_id] = state

    def reset(self, project_id: str) -> ConversationState:
        """Reset conversation state for a project."""
        import time
        timestamp = int(time.time() * 1000)
        state = ConversationState(
            projectId=project_id,
            createdAt=timestamp,
            updatedAt=timestamp
        )
        self._states[project_id] = state
        return state

    def cleanup_messages(self, project_id: str, max_messages: int = 20, keep_last: int = 15):
        """Clean up old messages to prevent unbounded growth."""
        state = self.get_or_create(project_id)
        if len(state.context.messages) > max_messages:
            state.context.messages = state.context.messages[-keep_last:]
            self.update(project_id, state)

    def cleanup_edits(self, project_id: str, max_edits: int = 10, keep_last: int = 8):
        """Clean up old edits to prevent unbounded growth."""
        state = self.get_or_create(project_id)
        if len(state.context.edits) > max_edits:
            state.context.edits = state.context.edits[-keep_last:]
            self.update(project_id, state)


# Global conversation state manager
conversation_manager = ConversationStateManager()
