"""Conversation State Models"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime


class Message(BaseModel):
    """Conversation message"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
    edited_files: Optional[List[str]] = None
    packages_installed: Optional[List[str]] = None
    edit_type: Optional[str] = None


class EditHistory(BaseModel):
    """Edit operation history"""
    timestamp: datetime = Field(default_factory=datetime.now)
    files_modified: List[str] = []
    edit_type: str
    prompt: str
    outcome: str = "pending"
    error: Optional[str] = None


class ProjectEvolution(BaseModel):
    """Project evolution tracking"""
    timestamp: datetime = Field(default_factory=datetime.now)
    change_type: str
    description: str
    files_affected: List[str] = []


class UserPreferences(BaseModel):
    """User preferences"""
    edit_style: Literal["targeted", "comprehensive"] = "targeted"
    common_patterns: List[str] = []


class ConversationState(BaseModel):
    """Complete conversation state"""
    project_id: str
    current_topic: str = "general development"
    messages: List[Message] = []
    edit_history: List[EditHistory] = []
    project_evolution: List[ProjectEvolution] = []
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ConversationStateAction(BaseModel):
    """Conversation state action request"""
    action: Literal["reset", "clear-old", "update"]
    data: Optional[Dict[str, Any]] = None
