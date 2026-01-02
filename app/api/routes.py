"""API routes configuration."""

from fastapi import APIRouter
from app.api.endpoints import (
    create_sandbox_v1,
    generate_ai_code,
    apply_ai_code,
    conversation_state,
    create_ai_sandbox_v2,
    install_packages,
    detect_and_install_packages,
    get_sandbox_files_v1,
    kill_sandbox,
    sandbox_status,
    update_sandbox_session_time,
    analyze_edit_intent,
    generate_project_info,
    test_stream
)

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    generate_ai_code.router,
    tags=["Code Generation"]
)

api_router.include_router(
    apply_ai_code.router,
    tags=["Code Application"]
)

api_router.include_router(
    conversation_state.router,
    tags=["Conversation State"]
)

api_router.include_router(
    create_ai_sandbox_v2.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    create_sandbox_v1.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    sandbox_status.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    get_sandbox_files_v1.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    kill_sandbox.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    install_packages.router,
    tags=["Package Management"]
)

api_router.include_router(
    detect_and_install_packages.router,
    tags=["Package Management"]
)

api_router.include_router(
    update_sandbox_session_time.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    analyze_edit_intent.router,
    tags=["AI Analysis"]
)

api_router.include_router(
    generate_project_info.router,
    tags=["AI Analysis"]
)

api_router.include_router(
    test_stream.router,
    tags=["Testing"]
)
