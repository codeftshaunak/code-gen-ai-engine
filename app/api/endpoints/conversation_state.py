"""Conversation state management endpoint."""

import time
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from app.models.conversation import conversation_manager, ConversationState


router = APIRouter()


class ConversationStateUpdateData(BaseModel):
    """Data for updating conversation state."""

    current_topic: Optional[str] = Field(None, alias="currentTopic")
    user_preferences: Optional[dict] = Field(None, alias="userPreferences")


class ConversationStateActionRequest(BaseModel):
    """Request model for conversation state actions."""

    action: Literal["reset", "clear-old", "update"]
    data: Optional[ConversationStateUpdateData] = None


class ConversationStateResponse(BaseModel):
    """Response model for conversation state operations."""

    success: bool
    project_id: str = Field(..., alias="projectId")
    message: Optional[str] = None
    state: Optional[ConversationState] = None
    error: Optional[str] = None


@router.get("/conversation-state")
async def get_conversation_state(
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Retrieve current conversation state for a project.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Returns:
        JSON response with conversation state or null if no active conversation

    Example:
        ```bash
        curl -X GET http://localhost:3100/api/conversation-state \
          -H "X-Project-Id: my-project-123"
        ```
    """
    try:
        project_id = x_project_id or "default"

        # Check if state exists in manager
        if project_id not in conversation_manager._states:
            return {
                "success": True,
                "projectId": project_id,
                "state": None,
                "message": "No active conversation"
            }

        state = conversation_manager._states[project_id]

        return {
            "success": True,
            "projectId": project_id,
            "state": state
        }

    except Exception as e:
        return {
            "success": False,
            "projectId": x_project_id or "default",
            "error": str(e)
        }, 500


@router.post("/conversation-state")
async def manage_conversation_state(
    request: ConversationStateActionRequest,
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Reset, update, or clear old conversation state data.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Request Body:
        - action (str): Action to perform - "reset", "clear-old", or "update"
        - data (dict, optional): Additional data for update action

    Actions:
        - reset: Completely reset conversation state to initial empty state
        - clear-old: Keep only recent data (last 5 messages, 3 edits, 2 evolution events)
        - update: Update specific fields like currentTopic or userPreferences

    Examples:
        Reset conversation:
        ```bash
        curl -X POST http://localhost:3100/api/conversation-state \
          -H "Content-Type: application/json" \
          -H "X-Project-Id: my-project-123" \
          -d '{"action": "reset"}'
        ```

        Clear old data:
        ```bash
        curl -X POST http://localhost:3100/api/conversation-state \
          -H "Content-Type: application/json" \
          -H "X-Project-Id: my-project-123" \
          -d '{"action": "clear-old"}'
        ```

        Update state:
        ```bash
        curl -X POST http://localhost:3100/api/conversation-state \
          -H "Content-Type: application/json" \
          -H "X-Project-Id: my-project-123" \
          -d '{
            "action": "update",
            "data": {
              "currentTopic": "Building authentication system"
            }
          }'
        ```
    """
    try:
        project_id = x_project_id or "default"

        if request.action == "reset":
            # Reset conversation state
            new_state = conversation_manager.reset(project_id)

            print(f"[conversation-state] Reset conversation state for project {project_id}")

            return {
                "success": True,
                "projectId": project_id,
                "message": "Conversation state reset",
                "state": new_state
            }

        elif request.action == "clear-old":
            # Clear old conversation data but keep recent context
            current_state = conversation_manager.get_or_create(project_id)

            if not current_state.context.messages:
                # Initialize conversation state if it doesn't exist
                print(f"[conversation-state] Initialized new conversation state for project {project_id} clear-old")

                return {
                    "success": True,
                    "projectId": project_id,
                    "message": "New conversation state initialized",
                    "state": current_state
                }

            # Keep only recent data
            current_state.context.messages = current_state.context.messages[-5:]
            current_state.context.edits = current_state.context.edits[-3:]
            current_state.context.project_evolution = current_state.context.project_evolution[-2:]
            current_state.updated_at = int(time.time() * 1000)

            conversation_manager.update(project_id, current_state)

            print(f"[conversation-state] Cleared old conversation data for project {project_id}")

            return {
                "success": True,
                "projectId": project_id,
                "message": "Old conversation data cleared",
                "state": current_state
            }

        elif request.action == "update":
            # Update specific fields
            existing_state = conversation_manager.get_or_create(project_id)

            # Update specific fields if provided
            if request.data:
                if request.data.current_topic is not None:
                    existing_state.context.current_topic = request.data.current_topic

                if request.data.user_preferences:
                    # Merge user preferences
                    current_prefs = existing_state.context.user_preferences
                    if "editStyle" in request.data.user_preferences:
                        current_prefs.edit_style = request.data.user_preferences["editStyle"]
                    if "commonPatterns" in request.data.user_preferences:
                        current_prefs.common_patterns = request.data.user_preferences["commonPatterns"]

                existing_state.updated_at = int(time.time() * 1000)
                conversation_manager.update(project_id, existing_state)

            return {
                "success": True,
                "projectId": project_id,
                "message": "Conversation state updated",
                "state": existing_state
            }

        else:
            raise HTTPException(
                status_code=400,
                detail='Invalid action. Use "reset", "clear-old", or "update"'
            )

    except HTTPException:
        raise

    except Exception as e:
        print(f"[conversation-state] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.delete("/conversation-state")
async def delete_conversation_state(
    x_project_id: str = Header(default="default", alias="X-Project-Id")
):
    """
    Clear/delete conversation state for a project.

    Headers:
        X-Project-Id (str): Project identifier (defaults to "default")

    Returns:
        JSON response confirming deletion

    Example:
        ```bash
        curl -X DELETE http://localhost:3100/api/conversation-state \
          -H "X-Project-Id: my-project-123"
        ```
    """
    try:
        project_id = x_project_id or "default"

        # Clear the conversation state by removing it from the manager
        if project_id in conversation_manager._states:
            del conversation_manager._states[project_id]

        print(f"[conversation-state] Cleared conversation state for project {project_id}")

        return {
            "success": True,
            "projectId": project_id,
            "message": "Conversation state cleared"
        }

    except Exception as e:
        print(f"[conversation-state] Error clearing state: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
