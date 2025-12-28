"""Generate project info (title and description) endpoint."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import json

from app.core.ai_provider import ai_provider
from app.config.settings import settings


router = APIRouter()


class GenerateProjectInfoRequest(BaseModel):
    """Request model for project info generation."""
    prompt: str = Field(..., min_length=1, description="User's project requirements")
    model: Optional[str] = Field(default=None, description="AI model to use")


class ProjectInfo(BaseModel):
    """Project information schema."""
    name: str = Field(..., min_length=1, max_length=100, description="Project title")
    description: str = Field(..., min_length=1, max_length=500, description="Project description")


class GenerateProjectInfoResponse(BaseModel):
    """Response model for project info generation."""
    success: bool
    data: ProjectInfo


@router.post("/generate-project-info")
async def generate_project_info(request: GenerateProjectInfoRequest):
    """
    Generate project title and description based on user requirements.

    Args:
        request: Contains prompt and optional model

    Returns:
        Project information with title and description
    """
    try:
        # Get model (use default if not specified)
        model = request.model or settings.DEFAULT_AI_MODEL

        # Build system prompt
        system_prompt = """You are an expert project title and description generator. Based on the user's project requirements, generate a concise project title and a brief but informative description.

The project title should be:
- Creative and relevant to the requirements
- Clear and descriptive
- Between 1-100 characters

The description should:
- Explain what the project is about
- Highlight core functionality
- Be concise but informative
- Between 1-500 characters

You MUST respond with ONLY a valid JSON object in this exact format:
{
  "name": "Project Title Here",
  "description": "Brief description of the project and its core functionality here."
}

Do not include any other text, markdown formatting, or explanations. Only return the JSON object."""

        # Build user prompt
        user_prompt = f"""Generate a project title and description for the following requirements:

{request.prompt}

Remember: Respond with ONLY the JSON object, nothing else."""

        # Generate response from AI
        full_response = ""
        async for chunk in ai_provider.stream_with_retry(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=500  # Short response, we just need title and description
        ):
            full_response += chunk

        # Parse JSON response
        try:
            # Try to extract JSON from response (in case AI added extra text)
            json_start = full_response.find('{')
            json_end = full_response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = full_response[json_start:json_end]
                project_data = json.loads(json_str)
            else:
                # Try parsing the whole response
                project_data = json.loads(full_response)

            # Validate and create ProjectInfo object
            project_info = ProjectInfo(**project_data)

            return GenerateProjectInfoResponse(
                success=True,
                data=project_info
            )

        except json.JSONDecodeError as e:
            # If JSON parsing fails, create a fallback response
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse AI response as JSON: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to validate project info: {str(e)}"
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate project information: {str(e)}"
        )
