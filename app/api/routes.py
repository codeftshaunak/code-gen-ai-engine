"""API routes configuration."""

from fastapi import APIRouter
from app.api.endpoints import (
    create_modal_sandbox,
    generate_ai_code,
    apply_ai_code,
    apply_ai_code_modal,
    conversation_state,
    create_ai_sandbox_v2,
    get_modal_sandbox_files,
    get_sandbox_files,
    install_packages,
    install_packages_modal,
    detect_and_install_packages,
    kill_sandbox,
    kill_sandbox_modal,
    sandbox_status,
    update_sandbox_session_time,
    analyze_edit_intent,
    generate_project_info,
    test_stream,
    run_command_modal,
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
    apply_ai_code_modal.router,
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
    create_modal_sandbox.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    sandbox_status.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    get_modal_sandbox_files.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    get_sandbox_files.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    kill_sandbox.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    kill_sandbox_modal.router,
    tags=["Sandbox Management"]
)

api_router.include_router(
    install_packages.router,
    tags=["Package Management"]
)

api_router.include_router(
    install_packages_modal.router,
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

api_router.include_router(
    run_command_modal.router,
    tags=["Sandbox Management"]
)
