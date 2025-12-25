"""Analyze edit intent endpoint."""

import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from enum import Enum

from app.core.ai_provider import ai_provider
from app.config.settings import settings


router = APIRouter()


class EditType(str, Enum):
    """Types of edits that can be performed."""

    UPDATE_COMPONENT = "UPDATE_COMPONENT"
    ADD_FEATURE = "ADD_FEATURE"
    FIX_ISSUE = "FIX_ISSUE"
    UPDATE_STYLE = "UPDATE_STYLE"
    REFACTOR = "REFACTOR"
    ADD_DEPENDENCY = "ADD_DEPENDENCY"
    REMOVE_ELEMENT = "REMOVE_ELEMENT"


class FallbackSearch(BaseModel):
    """Fallback search configuration."""

    terms: List[str]
    patterns: Optional[List[str]] = None


class SearchPlan(BaseModel):
    """AI-generated search plan for finding code to edit."""

    edit_type: EditType = Field(..., alias="editType")
    reasoning: str
    search_terms: List[str] = Field(..., alias="searchTerms")
    regex_patterns: Optional[List[str]] = Field(None, alias="regexPatterns")
    file_types_to_search: List[str] = Field(
        default=[".jsx", ".tsx", ".js", ".ts"],
        alias="fileTypesToSearch"
    )
    expected_matches: int = Field(default=1, ge=1, le=10, alias="expectedMatches")
    fallback_search: Optional[FallbackSearch] = Field(None, alias="fallbackSearch")


class AnalyzeEditIntentRequest(BaseModel):
    """Request model for edit intent analysis."""

    prompt: str
    manifest: Dict[str, Any]
    model: Optional[str] = "anthropic/claude-3-5-sonnet-20241022"


@router.post("/analyze-edit-intent")
async def analyze_edit_intent(request: AnalyzeEditIntentRequest):
    """
    Analyze user's edit intent and create a search plan to find the code to modify.

    This endpoint uses AI to understand the user's edit request and generate a specific
    search strategy to locate the exact code that needs to be modified. Instead of
    guessing which files to edit, it provides search terms and patterns.

    Request Body:
        - prompt (str): User's edit request (e.g., "change button text to 'Go Now'")
        - manifest (dict): File manifest with project structure and component info
        - model (str, optional): AI model to use for analysis

    Returns:
        JSON response with search plan including:
        - editType: Type of edit (UPDATE_COMPONENT, ADD_FEATURE, etc.)
        - reasoning: Explanation of search strategy
        - searchTerms: Specific text to search for
        - regexPatterns: Optional regex patterns for structural searches
        - fileTypesToSearch: File extensions to search
        - expectedMatches: Expected number of matches
        - fallbackSearch: Backup search if primary fails

    Example:
        ```bash
        curl -X POST http://localhost:3100/api/analyze-edit-intent \
          -H "Content-Type: application/json" \
          -d '{
            "prompt": "change the header text from Start Deploying to Go Now",
            "manifest": {
              "files": {
                "/src/App.jsx": {"componentInfo": {"name": "App"}}
              }
            },
            "model": "anthropic/claude-3-5-sonnet-20241022"
          }'
        ```

    Response:
        ```json
        {
          "success": true,
          "searchPlan": {
            "editType": "UPDATE_COMPONENT",
            "reasoning": "Search for exact text 'Start Deploying' in header components",
            "searchTerms": ["Start Deploying", "header", "Header"],
            "regexPatterns": ["className=.*header.*"],
            "fileTypesToSearch": [".jsx", ".tsx"],
            "expectedMatches": 1
          }
        }
        ```
    """
    try:
        print("[analyze-edit-intent] Request received")
        print(f"[analyze-edit-intent] Prompt: {request.prompt}")
        print(f"[analyze-edit-intent] Model: {request.model}")

        if not request.prompt or not request.manifest:
            raise HTTPException(
                status_code=400,
                detail="prompt and manifest are required"
            )

        # Validate and filter manifest files
        manifest_files = request.manifest.get("files", {})
        print(f"[analyze-edit-intent] Manifest files count: {len(manifest_files)}")

        valid_files = {
            path: info
            for path, info in manifest_files.items()
            if isinstance(path, str) and '.' in path and not path.endswith(('/0', '/1', '/2', '/3', '/4', '/5', '/6', '/7', '/8', '/9'))
        }

        if not valid_files:
            print("[analyze-edit-intent] No valid files found in manifest")
            raise HTTPException(
                status_code=400,
                detail="No valid files found in manifest"
            )

        print(f"[analyze-edit-intent] Valid files found: {len(valid_files)}")

        # Create file summary for AI context
        file_summary_parts = []
        for path, info in list(valid_files.items())[:50]:  # Limit to 50 files
            component_name = info.get("componentInfo", {}).get("name", path.split("/")[-1])
            child_components = ", ".join(info.get("componentInfo", {}).get("childComponents", [])) or "none"
            file_summary_parts.append(f"- {path} ({component_name}, renders: {child_components})")

        file_summary = "\n".join(file_summary_parts)

        print(f"[analyze-edit-intent] File summary preview: {file_summary_parts[:5]}")

        # Build system prompt
        system_prompt = f"""You are an expert at planning code searches. Your job is to create a search strategy to find the exact code that needs to be edited.

DO NOT GUESS which files to edit. Instead, provide specific search terms that will locate the code.

SEARCH STRATEGY RULES:
1. For text changes (e.g., "change 'Start Deploying' to 'Go Now'"):
   - Search for the EXACT text: "Start Deploying"

2. For style changes (e.g., "make header black"):
   - Search for component names: "Header", "<header"
   - Search for class names: "header", "navbar"
   - Search for className attributes containing relevant words

3. For removing elements (e.g., "remove the deploy button"):
   - Search for the button text or aria-label
   - Search for relevant IDs or data-testids

4. For navigation/header issues:
   - Search for: "navigation", "nav", "Header", "navbar"
   - Look for Link components or href attributes

5. Be SPECIFIC:
   - Use exact capitalization for user-visible text
   - Include multiple search terms for redundancy
   - Add regex patterns for structural searches

Current project structure for context:
{file_summary}

You must respond with a valid JSON object matching this structure:
{{
  "editType": "UPDATE_COMPONENT" | "ADD_FEATURE" | "FIX_ISSUE" | "UPDATE_STYLE" | "REFACTOR" | "ADD_DEPENDENCY" | "REMOVE_ELEMENT",
  "reasoning": "explanation of search strategy",
  "searchTerms": ["specific", "search", "terms"],
  "regexPatterns": ["optional regex patterns"],
  "fileTypesToSearch": [".jsx", ".tsx", ".js", ".ts"],
  "expectedMatches": 1
}}"""

        user_prompt = f"""User request: "{request.prompt}"

Create a search plan to find the exact code that needs to be modified. Include specific search terms and patterns.

Respond with ONLY a valid JSON object, no other text."""

        print("[analyze-edit-intent] Calling AI to generate search plan...")

        # Use AI to generate search plan
        model = request.model or settings.DEFAULT_AI_MODEL

        # Stream AI response and collect full response
        full_response = ""
        async for chunk in ai_provider.stream_with_retry(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,  # Lower temperature for more consistent JSON
            max_tokens=2048
        ):
            full_response += chunk

        print(f"[analyze-edit-intent] AI response received (length: {len(full_response)})")

        # Extract JSON from response (in case AI added extra text)
        json_start = full_response.find("{")
        json_end = full_response.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            raise ValueError("No valid JSON found in AI response")

        json_str = full_response[json_start:json_end]

        # Parse the JSON response
        try:
            search_plan_dict = json.loads(json_str)

            # Validate and create SearchPlan model
            search_plan = SearchPlan(**search_plan_dict)

            print(f"[analyze-edit-intent] Search plan created:")
            print(f"  - Edit type: {search_plan.edit_type}")
            print(f"  - Search terms: {search_plan.search_terms}")
            print(f"  - Patterns: {len(search_plan.regex_patterns or [])}")
            print(f"  - Reasoning: {search_plan.reasoning[:100]}...")

            return {
                "success": True,
                "searchPlan": search_plan.dict(by_alias=True)
            }

        except json.JSONDecodeError as e:
            print(f"[analyze-edit-intent] JSON parse error: {e}")
            print(f"[analyze-edit-intent] Response was: {json_str[:500]}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse AI response as JSON: {str(e)}"
            )

    except HTTPException:
        raise

    except Exception as e:
        print(f"[analyze-edit-intent] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
