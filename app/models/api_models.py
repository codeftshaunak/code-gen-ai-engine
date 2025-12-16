"""API Request/Response Models"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class GenerateCodeRequest(BaseModel):
    """Generate AI code request"""
    prompt: str
    model: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    is_edit: bool = False


class ApplyCodeRequest(BaseModel):
    """Apply AI code request"""
    response: str
    is_edit: bool = False
    packages: List[str] = []
    sandbox_id: Optional[str] = None


class InstallPackagesRequest(BaseModel):
    """Install packages request"""
    packages: List[str]
    sandbox_id: Optional[str] = None


class DetectPackagesRequest(BaseModel):
    """Detect packages from files request"""
    files: Dict[str, str]


class DetectPackagesResponse(BaseModel):
    """Detect packages response"""
    success: bool
    packages_installed: List[str] = []
    packages_already_installed: List[str] = []
    message: str


class StreamEvent(BaseModel):
    """Server-Sent Event for streaming"""
    event: str
    data: Any


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    message: Optional[str] = None
