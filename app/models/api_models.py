"""API request and response models."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Literal


class ScrapedWebsite(BaseModel):
    """Scraped website data."""

    url: str
    timestamp: int
    content: Any


class ConversationContext(BaseModel):
    """Conversation context information."""

    scraped_websites: Optional[List[ScrapedWebsite]] = Field(None, alias="scrapedWebsites")
    current_project: Optional[str] = Field(None, alias="currentProject")


class RequestContext(BaseModel):
    """Request context containing application state."""

    sandbox_id: Optional[str] = Field(None, alias="sandboxId")
    structure: Optional[str] = None
    current_files: Optional[Dict[str, str]] = Field(None, alias="currentFiles")
    conversation_context: Optional[ConversationContext] = Field(None, alias="conversationContext")


class GenerateCodeRequest(BaseModel):
    """Request model for generate-ai-code-stream endpoint."""

    prompt: str = Field(..., description="User prompt describing what code to generate")
    model: Optional[str] = Field(None, description="AI model to use (e.g., 'anthropic/claude-4.5-sonnet')")
    context: Optional[RequestContext] = Field(None, description="Current application context")
    is_edit: bool = Field(False, alias="isEdit", description="Whether this is an edit or new generation")


class StreamEvent(BaseModel):
    """Server-Sent Event model."""

    type: Literal["status", "stream", "conversation", "component", "package", "warning", "complete", "error"]
    message: Optional[str] = None
    text: Optional[str] = None
    raw: Optional[bool] = None
    name: Optional[str] = None
    path: Optional[str] = None
    index: Optional[int] = None
    generated_code: Optional[str] = Field(None, alias="generatedCode")
    explanation: Optional[str] = None
    files: Optional[int] = None
    components: Optional[int] = None
    model: Optional[str] = None
    packages_to_install: Optional[List[str]] = Field(None, alias="packagesToInstall")
    warnings: Optional[List[str]] = None
    error: Optional[str] = None


class ApplyCodeRequest(BaseModel):
    """Request model for apply-ai-code-stream endpoint."""

    response: str = Field(..., description="AI-generated response containing file blocks")
    is_edit: bool = Field(False, alias="isEdit", description="Enable Morph Fast Apply mode")
    packages: Optional[List[str]] = Field(None, description="Additional packages to install")
    sandbox_id: Optional[str] = Field(None, alias="sandboxId", description="Specific sandbox ID to use")


class ApplyCodeResults(BaseModel):
    """Results from applying code."""

    files_created: List[str] = Field(default_factory=list, alias="filesCreated")
    files_updated: List[str] = Field(default_factory=list, alias="filesUpdated")
    packages_installed: List[str] = Field(default_factory=list, alias="packagesInstalled")
    packages_already_installed: List[str] = Field(default_factory=list, alias="packagesAlreadyInstalled")
    packages_failed: List[str] = Field(default_factory=list, alias="packagesFailed")
    commands_executed: List[str] = Field(default_factory=list, alias="commandsExecuted")
    errors: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = False
    error: str
