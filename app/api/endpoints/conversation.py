"""
Conversation State Endpoint
Manages conversation history and context
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.models.conversation import ConversationState, ConversationStateAction
from app.models.api_models import ErrorResponse
from app.core.app_state_manager import app_state_manager
from app.utils.project_utils import get_project_id
from datetime import datetime

router = APIRouter()


@router.get(
    "/conversation-state",
    response_model=ConversationState,
    summary="Get Conversation State",
    description="""
    Retrieve the current conversation state for a project.

    **Returns:**
    - Complete conversation history
    - Messages with metadata
    - Edit history
    - Project evolution
    - User preferences

    **Request Headers:**
    - `X-Project-Id`: Required project identifier
    """
)
async def get_conversation_state(
    project_id: str = Depends(get_project_id)
) -> ConversationState:
    """Get current conversation state"""
    context = app_state_manager.for_project(project_id)
    return context.get_conversation_state()


@router.post(
    "/conversation-state",
    response_model=ConversationState,
    summary="Update Conversation State",
    description="""
    Update conversation state with various actions.

    **Actions:**
    - `reset`: Create new conversation state
    - `clear-old`: Trim old messages (keeps last 5), edits (last 3), changes (last 2)
    - `update`: Update topic or user preferences

    **Request Headers:**
    - `X-Project-Id`: Required project identifier
    """
)
async def update_conversation_state(
    action_request: ConversationStateAction,
    project_id: str = Depends(get_project_id)
) -> ConversationState:
    """Update conversation state based on action"""
    context = app_state_manager.for_project(project_id)
    conversation_state = context.get_conversation_state()

    if action_request.action == "reset":
        # Create new conversation state
        context.conversation_state = ConversationState(project_id=project_id)
        return context.conversation_state

    elif action_request.action == "clear-old":
        # Trim old messages, edits, and changes
        if len(conversation_state.messages) > 5:
            conversation_state.messages = conversation_state.messages[-5:]

        if len(conversation_state.edit_history) > 3:
            conversation_state.edit_history = conversation_state.edit_history[-3:]

        if len(conversation_state.project_evolution) > 2:
            conversation_state.project_evolution = conversation_state.project_evolution[-2:]

        conversation_state.updated_at = datetime.now()
        return conversation_state

    elif action_request.action == "update":
        # Update topic or user preferences
        if action_request.data:
            if "currentTopic" in action_request.data:
                conversation_state.current_topic = action_request.data["currentTopic"]

            if "userPreferences" in action_request.data:
                prefs = action_request.data["userPreferences"]
                if "editStyle" in prefs:
                    conversation_state.user_preferences.edit_style = prefs["editStyle"]
                if "commonPatterns" in prefs:
                    conversation_state.user_preferences.common_patterns = prefs["commonPatterns"]

        conversation_state.updated_at = datetime.now()
        return conversation_state

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action: {action_request.action}"
        )


@router.delete(
    "/conversation-state",
    summary="Clear Conversation State",
    description="""
    Clear all conversation data for a project.

    **Request Headers:**
    - `X-Project-Id`: Required project identifier
    """
)
async def clear_conversation_state(
    project_id: str = Depends(get_project_id)
):
    """Clear conversation state"""
    context = app_state_manager.for_project(project_id)
    context.conversation_state = None

    return {
        "success": True,
        "message": "Conversation state cleared"
    }
