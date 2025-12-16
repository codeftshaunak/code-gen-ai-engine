"""
API Routes
Main router that includes all API endpoints
"""
from fastapi import APIRouter

from app.api.endpoints import (
    generate_ai_code,
    apply_ai_code,
    install_packages,
    detect_packages,
    conversation,
    sandbox,
    create_zip
)

router = APIRouter()

# Include all endpoint routers
router.include_router(generate_ai_code.router, tags=["AI Generation"])
router.include_router(apply_ai_code.router, tags=["Code Application"])
router.include_router(install_packages.router, tags=["Package Management"])
router.include_router(detect_packages.router, tags=["Package Detection"])
router.include_router(conversation.router, tags=["Conversation State"])
router.include_router(sandbox.router, tags=["Sandbox Management"])
router.include_router(create_zip.router, tags=["File Operations"])
