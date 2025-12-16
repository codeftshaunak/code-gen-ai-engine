"""
Project Utilities
Validation and helper functions for projects
"""
import re
from fastapi import Header, HTTPException


def validate_project_id(project_id: str) -> bool:
    """Validate project ID format"""
    pattern = r'^[a-zA-Z0-9_-]{1,64}$'
    return bool(re.match(pattern, project_id))


def sanitize_project_id(project_id: str) -> str:
    """Sanitize project ID to alphanumeric with hyphens/underscores"""
    return re.sub(r'[^a-zA-Z0-9_-]', '', project_id)[:64]


async def get_project_id(x_project_id: str = Header(None)) -> str:
    """
    Extract and validate project ID from header

    Args:
        x_project_id: X-Project-Id header value

    Returns:
        Validated project ID

    Raises:
        HTTPException: If project ID is missing or invalid
    """
    if not x_project_id:
        raise HTTPException(
            status_code=400,
            detail="Missing X-Project-Id header"
        )

    project_id = sanitize_project_id(x_project_id)

    if not validate_project_id(project_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid project ID format"
        )

    return project_id
