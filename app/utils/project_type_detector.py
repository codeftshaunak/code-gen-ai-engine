"""Project type detection utilities."""

import logging
import json
from typing import Dict, List
from app.core.ai_provider import ai_provider
from app.config.settings import settings


logger = logging.getLogger(__name__)


async def detect_project_type(prompt: str) -> Dict[str, any]:
    """
    Analyze user prompt to determine if it's a frontend-only or full-stack project.

    Uses AI to intelligently detect if the user needs:
    - Frontend only (React UI components, pages, styling)
    - Full-stack (Frontend + Supabase backend with database, auth, storage)

    Args:
        prompt: User's project description

    Returns:
        Dictionary with:
            - type: "frontend" or "fullstack"
            - features: List of backend features needed (e.g., ["auth", "database", "storage"])
            - database_entities: List of database tables/entities detected
            - confidence: Confidence score (0.0-1.0)
            - reasoning: Brief explanation of the decision

    Examples:
        >>> await detect_project_type("Create a landing page with hero section")
        {"type": "frontend", "features": [], "database_entities": [], "confidence": 0.95}

        >>> await detect_project_type("Build a todo app with user authentication")
        {"type": "fullstack", "features": ["auth", "database"], "database_entities": ["users", "todos"], "confidence": 0.9}
    """
    system_prompt = """You are a project architecture analyzer. Analyze the user's request and determine if they need:

1. **Frontend only**: Just UI components, pages, styling, no data persistence or user accounts
2. **Full-stack**: Requires backend features like database, authentication, or storage

BACKEND INDICATORS (choose "fullstack"):
- User accounts, login, signup, authentication
- Data persistence (save, store, database, CRUD operations)
- User-specific data ("my todos", "my profile", "user dashboard")
- Multi-user features (social, sharing, comments)
- File uploads, storage
- Real-time features (chat, notifications)
- API integration that requires server-side secrets

FRONTEND-ONLY INDICATORS (choose "frontend"):
- Static pages (landing, about, contact)
- UI components without persistence
- Forms that don't save data
- Galleries, portfolios, marketing sites
- Calculators, converters (client-side only)
- No mention of users or accounts

RESPOND ONLY WITH VALID JSON (no markdown, no extra text):
{
  "type": "frontend" or "fullstack",
  "features": ["auth", "database", "storage"],  // Empty for frontend
  "database_entities": ["users", "posts"],      // Empty for frontend
  "confidence": 0.9,
  "reasoning": "Brief explanation"
}

Be conservative: if unsure, default to "frontend"."""

    user_message = f"""Analyze this project request:

"{prompt}"

What type of project is this?"""

    try:
        # Use AI to analyze the prompt
        response = ""
        async for chunk in ai_provider.stream_with_retry(
            model=settings.DEFAULT_AI_MODEL,
            system_prompt=system_prompt,
            user_prompt=user_message,
            temperature=0.3  # Lower temperature for more consistent analysis
        ):
            response += chunk

        # Parse the JSON response
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            # Remove markdown code block
            lines = response.split("\n")
            response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
        
        response = response.replace("```json", "").replace("```", "").strip()

        result = json.loads(response)
        
        logger.info(f"Project type detected: {result.get('type')} (confidence: {result.get('confidence')})")
        logger.info(f"Reasoning: {result.get('reasoning')}")
        
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        logger.error(f"Response was: {response}")
        
        # Fallback to simple keyword detection
        return _fallback_detection(prompt)
    
    except Exception as e:
        logger.error(f"Error in project type detection: {str(e)}")
        
        # Fallback to simple keyword detection
        return _fallback_detection(prompt)


def _fallback_detection(prompt: str) -> Dict[str, any]:
    """
    Simple fallback detection using keyword matching.

    Args:
        prompt: User's project description

    Returns:
        Detection result dictionary
    """
    prompt_lower = prompt.lower()
    
    # Backend keywords
    backend_keywords = [
        "auth", "login", "signup", "user", "account", "database", "save", "store",
        "crud", "api", "backend", "server", "persist", "signup", "sign up",
        "authentication", "profile", "dashboard", "todo", "chat", "real-time",
        "upload", "storage", "comments", "posts", "social"
    ]
    
    # Count backend indicators
    backend_score = sum(1 for keyword in backend_keywords if keyword in prompt_lower)
    
    if backend_score >= 2:
        # Likely needs backend
        features = []
        entities = []
        
        if any(word in prompt_lower for word in ["auth", "login", "signup", "user", "account"]):
            features.append("auth")
            entities.append("users")
        
        if any(word in prompt_lower for word in ["database", "save", "store", "crud", "persist"]):
            features.append("database")
        
        if any(word in prompt_lower for word in ["upload", "storage", "file"]):
            features.append("storage")
        
        # Try to extract entity names
        if "todo" in prompt_lower:
            entities.append("todos")
        if "post" in prompt_lower:
            entities.append("posts")
        if "comment" in prompt_lower:
            entities.append("comments")
        if "product" in prompt_lower:
            entities.append("products")
        
        return {
            "type": "fullstack",
            "features": list(set(features)) if features else ["database"],
            "database_entities": list(set(entities)),
            "confidence": 0.7,
            "reasoning": f"Detected {backend_score} backend indicators using keyword fallback"
        }
    
    else:
        # Frontend only
        return {
            "type": "frontend",
            "features": [],
            "database_entities": [],
            "confidence": 0.8,
            "reasoning": "No strong backend indicators found - defaulting to frontend"
        }
