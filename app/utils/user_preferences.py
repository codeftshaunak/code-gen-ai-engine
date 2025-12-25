"""User preference analysis from conversation history."""

import re
from typing import List, Tuple, Literal
from app.models.conversation import ConversationMessage, UserPreferences


def analyze_user_preferences(messages: List[ConversationMessage]) -> UserPreferences:
    """
    Analyze user preferences from conversation history.

    Args:
        messages: List of conversation messages

    Returns:
        UserPreferences with detected patterns and edit style
    """
    user_messages = [msg for msg in messages if msg.role == "user"]
    patterns: List[str] = []

    # Count edit-related keywords
    targeted_edit_count = 0
    comprehensive_edit_count = 0

    for msg in user_messages:
        content = msg.content.lower()

        # Check for targeted edit patterns
        if re.search(
            r'\b(update|change|fix|modify|edit|remove|delete)\s+(\w+\s+)?(\w+)\b',
            content
        ):
            targeted_edit_count += 1

        # Check for comprehensive edit patterns
        if re.search(r'\b(rebuild|recreate|redesign|overhaul|refactor)\b', content):
            comprehensive_edit_count += 1

        # Extract common request patterns
        if 'hero' in content:
            patterns.append("hero section edits")
        if 'header' in content:
            patterns.append("header modifications")
        if 'color' in content or 'style' in content:
            patterns.append("styling changes")
        if 'button' in content:
            patterns.append("button updates")
        if 'animation' in content:
            patterns.append("animation requests")
        if 'footer' in content:
            patterns.append("footer modifications")
        if 'nav' in content or 'navigation' in content:
            patterns.append("navigation updates")

    # Remove duplicates and keep top 3
    unique_patterns = list(dict.fromkeys(patterns))[:3]

    # Determine preferred edit style
    edit_style: Literal["targeted", "comprehensive"] = (
        "targeted" if targeted_edit_count > comprehensive_edit_count
        else "comprehensive"
    )

    return UserPreferences(
        editStyle=edit_style,
        commonPatterns=unique_patterns
    )
