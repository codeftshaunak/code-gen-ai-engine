"""System prompt builder for AI code generation."""

from typing import Dict, Optional, List
from app.models.api_models import RequestContext
from app.models.conversation import ConversationState, UserPreferences


class PromptBuilder:
    """Builds system prompts for AI code generation."""

    @staticmethod
    def build_system_prompt(
        user_prompt: str,
        is_edit: bool = False,
        context: Optional[RequestContext] = None,
        conversation_state: Optional[ConversationState] = None,
        user_preferences: Optional[UserPreferences] = None
    ) -> str:
        """
        Build comprehensive system prompt for code generation.

        Args:
            user_prompt: The user's request
            is_edit: Whether this is an edit to existing code
            context: Application context (files, conversation history, etc.)
            conversation_state: Full conversation state with message history
            user_preferences: Analyzed user preferences

        Returns:
            Complete system prompt string
        """
        sections = []

        # Core identity and role
        sections.append(PromptBuilder._get_core_identity())

        # Conversation history context
        if conversation_state:
            sections.append(PromptBuilder._format_conversation_history(conversation_state, user_preferences))

        # Conversation context if available (scraped websites, etc.)
        if context and context.conversation_context:
            sections.append(PromptBuilder._format_conversation_context(context))

        # Edit mode instructions
        if is_edit:
            sections.append(PromptBuilder._get_edit_mode_instructions())

        # File context if available
        if context and context.current_files:
            sections.append(PromptBuilder._format_file_context(context.current_files))

        # Critical rules and guidelines
        sections.append(PromptBuilder._get_critical_rules())

        # Code structure format
        sections.append(PromptBuilder._get_code_format_instructions())

        # Styling rules
        sections.append(PromptBuilder._get_styling_rules())

        # Code validation rules
        sections.append(PromptBuilder._get_validation_rules())

        return "\n\n".join(sections)

    @staticmethod
    def _get_core_identity() -> str:
        """Get core identity and role description."""
        return """You are an expert React developer with perfect memory of the conversation.
You maintain context across messages and remember generated components and applied code.
Generate clean, modern React code for Vite applications using React 18+ and Tailwind CSS.

Your role is to help users build beautiful, functional web applications by:
- Understanding their requirements precisely
- Generating complete, working code
- Following React and web development best practices
- Creating responsive, accessible interfaces
- Writing clean, maintainable code"""

    @staticmethod
    def _get_edit_mode_instructions() -> str:
        """Get instructions for edit mode."""
        return """## CRITICAL: EDIT MODE ACTIVE

THIS IS AN EDIT TO AN EXISTING APPLICATION - FOLLOW THESE RULES:

1. DO NOT regenerate the entire application
2. DO NOT create files that already exist unless they need modification
3. ONLY edit the EXACT files needed for the requested change
4. When adding new components:
   - Create the new component file
   - Update ONLY the parent component that will use it
   - Do not modify unrelated files
5. For style changes:
   - Only modify the specific component being styled
   - Do not regenerate other components
6. Maintain existing functionality:
   - Preserve all existing code that isn't being changed
   - Don't remove features that aren't mentioned
   - Keep the same file structure unless explicitly asked to change it"""

    @staticmethod
    def _get_critical_rules() -> str:
        """Get critical rules for code generation."""
        return """## CRITICAL RULES - MUST FOLLOW:

1. **Do Exactly What Is Asked - Nothing More, Nothing Less**
   - If user asks for "a blue button", create ONLY a blue button
   - Don't add extra features, components, or functionality
   - Don't make assumptions about what else they might want

2. **Check Before Creating**
   - Always check App.jsx first before creating new components
   - If functionality exists, modify it - don't duplicate

3. **File Count Limits**
   - Simple change (color, text, size) = 1 file maximum
   - New component = 2 files maximum (component + parent that uses it)
   - Complex feature = 3-4 files maximum
   - If you need more files, you're probably doing too much

4. **Component Creation Rules**
   - Create new components ONLY when:
     * User explicitly asks for a new component
     * The component is genuinely reusable
     * It makes the code significantly cleaner
   - DO NOT create unnecessary abstraction

5. **Never Create SVGs from Scratch**
   - Use icon libraries (lucide-react, react-icons)
   - Only create SVG if explicitly asked
   - For logos, use text or image placeholders

6. **Complete Code Only**
   - NEVER truncate code with "..." or comments like "// rest of code"
   - ALWAYS return complete, working files
   - If running out of space, prioritize completing the current file"""

    @staticmethod
    def _get_code_format_instructions() -> str:
        """Get code format instructions."""
        return """## CODE OUTPUT FORMAT

You must wrap all code files in the following XML-style format:

```
<file path="src/components/Hero.jsx">
// Complete file content here
import React from 'react';

export default function Hero() {
  return (
    <div className="min-h-screen bg-blue-500">
      <h1 className="text-4xl font-bold">Hello World</h1>
    </div>
  );
}
</file>
```

**Format Rules:**
1. Each file MUST have opening `<file path="...">` and closing `</file>` tags
2. Path must be relative to project root (e.g., "src/App.jsx", "src/components/Button.jsx")
3. Include complete file content between tags - no truncation
4. Multiple files should each have their own file tags
5. Do not include explanatory text inside file tags - only code

**Before each file, you can optionally include:**
- A brief explanation of what the file does
- Why you're creating or modifying it
- Important implementation notes

**Example:**

I'll create a hero section component with a dark background and centered text.

<file path="src/components/Hero.jsx">
[Complete component code]
</file>

Now I'll update App.jsx to use this component.

<file path="src/App.jsx">
[Complete App code with Hero imported and used]
</file>"""

    @staticmethod
    def _get_styling_rules() -> str:
        """Get styling rules."""
        return """## CRITICAL STYLING RULES - MUST FOLLOW:

1. **Use ONLY Tailwind CSS for ALL styling**
   - NEVER use inline styles with `style={{ }}`
   - NEVER use `<style jsx>` tags
   - NEVER create CSS files (except src/index.css)
   - NEVER import CSS modules

2. **Standard Tailwind Classes Only**
   - Use standard classes: `bg-white`, `text-black`, `bg-blue-500`
   - DO NOT use custom theme variables: `bg-background`, `text-foreground`
   - DO NOT use CSS variables: `var(--background)`
   - Stick to Tailwind's default palette and utilities

3. **Index.css Configuration**
   - ONLY create src/index.css if it doesn't exist
   - It should ONLY contain:
     ```css
     @tailwind base;
     @tailwind components;
     @tailwind utilities;
     ```
   - No custom CSS, no @layer directives, no custom classes

4. **Responsive Design**
   - Use Tailwind's responsive prefixes: `md:`, `lg:`, `xl:`
   - Mobile-first approach: base styles for mobile, prefixes for larger screens

5. **Dark Mode** (if requested)
   - Use Tailwind's dark mode classes: `dark:bg-gray-900`
   - Configure in tailwind.config.js with `darkMode: 'class'`"""

    @staticmethod
    def _get_validation_rules() -> str:
        """Get code validation rules."""
        return """## CRITICAL CODE GENERATION RULES:

1. **No Truncation - Ever**
   - NEVER truncate ANY code
   - NEVER use "..." anywhere in your code
   - NEVER use comments like "// ... rest of the code" or "// ... other imports"
   - NEVER cut off strings, arrays, or objects mid-sentence
   - ALWAYS write COMPLETE files from start to finish

2. **Proper Code Closure**
   - ALWAYS close ALL tags: `<div>` must have `</div>`
   - ALWAYS close ALL quotes: every `"` or `'` must be paired
   - ALWAYS close ALL brackets: `{`, `[`, `(` must have matching closures
   - ALWAYS close ALL JSX components properly

3. **File Completeness**
   - Every file must be complete and ready to use
   - Include ALL imports needed
   - Include ALL props, functions, and returns
   - Include ALL closing braces and tags

4. **Quality Standards**
   - Code must be syntactically correct
   - Code must follow React best practices
   - Code must be properly formatted and indented
   - Components must be properly exported

5. **If Space Is Limited**
   - Prioritize completing the current file over starting new ones
   - Better to have 2 complete files than 4 incomplete ones
   - Finish what you start - never leave files half-done"""

    @staticmethod
    def _format_file_context(current_files: Dict[str, str]) -> str:
        """Format current file context for AI."""
        if not current_files:
            return ""

        file_list = []
        for file_path, content in current_files.items():
            # Truncate very long files for context
            if len(content) > 2000:
                truncated_content = content[:2000] + "\n// ... (truncated for context)"
            else:
                truncated_content = content

            file_list.append(f"### {file_path}\n```\n{truncated_content}\n```")

        files_section = "\n\n".join(file_list)

        return f"""## CURRENT APPLICATION FILES

Here are the existing files in the application. Reference these to understand the current structure and avoid duplicating code:

{files_section}

**Important:**
- Check these files before creating new components
- Modify existing files instead of creating duplicates
- Maintain consistency with existing code style
- Preserve imports and dependencies that are already set up"""

    @staticmethod
    def _format_conversation_history(
        conversation_state: ConversationState,
        user_preferences: Optional[UserPreferences] = None
    ) -> str:
        """Format conversation history for AI context."""
        sections = []

        messages = conversation_state.context.messages
        edits = conversation_state.context.edits
        evolution = conversation_state.context.project_evolution

        # Recent conversation history (last 5 messages)
        if messages and len(messages) > 0:
            sections.append("## CONVERSATION HISTORY")
            sections.append("\nRecent conversation (use this to maintain context):\n")

            recent_messages = messages[-5:]  # Last 5 messages
            for msg in recent_messages:
                role_prefix = "User" if msg.role == "user" else "Assistant"
                # Truncate very long messages for context
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                sections.append(f"- **{role_prefix}**: {content}")

        # Edit history (last 3 edits)
        if edits and len(edits) > 0:
            sections.append("\n## RECENT EDITS")
            sections.append("\nYou recently made these changes:\n")

            recent_edits = edits[-3:]  # Last 3 edits
            for edit in recent_edits:
                outcome_emoji = "✅" if edit.outcome == "success" else "⚠️" if edit.outcome == "partial" else "❌"
                sections.append(f"- {outcome_emoji} **{edit.edit_type}**: {edit.user_request}")
                if edit.target_files:
                    sections.append(f"  Files: {', '.join(edit.target_files[:3])}")

        # User preferences
        if user_preferences:
            sections.append("\n## USER PREFERENCES")
            sections.append(f"\n- **Edit Style**: {user_preferences.edit_style}")

            if user_preferences.edit_style == "targeted":
                sections.append("  → User prefers precise, minimal edits (only change what's needed)")
            else:
                sections.append("  → User prefers comprehensive rebuilds when making changes")

            if user_preferences.common_patterns:
                sections.append(f"- **Common Patterns**: {', '.join(user_preferences.common_patterns)}")

        # Project evolution (major milestones)
        if evolution and len(evolution) > 0:
            sections.append("\n## PROJECT EVOLUTION")
            sections.append("\nMajor project changes:\n")

            for milestone in evolution[-2:]:  # Last 2 major changes
                sections.append(f"- {milestone.description}")

        if sections:
            sections.append("\n**Use this context to:**")
            sections.append("- Maintain consistency with previous decisions")
            sections.append("- Avoid repeating work already done")
            sections.append("- Understand the user's workflow and preferences")
            sections.append("- Reference previous components and patterns")

        return "\n".join(sections) if sections else ""

    @staticmethod
    def _format_conversation_context(context: RequestContext) -> str:
        """Format conversation context for AI."""
        sections = []

        conv_ctx = context.conversation_context
        if not conv_ctx:
            return ""

        # Scraped websites
        if conv_ctx.scraped_websites:
            sections.append("### Referenced Websites:")
            for site in conv_ctx.scraped_websites[-3:]:  # Last 3 websites
                sections.append(f"- {site.url}")

        # Current project
        if conv_ctx.current_project:
            sections.append(f"\n### Current Project: {conv_ctx.current_project}")

        if sections:
            return f"""## CONVERSATION CONTEXT

{chr(10).join(sections)}

This context helps you understand what the user has been working on. Use it to maintain consistency and avoid repeating information."""

        return ""


# Global prompt builder instance
prompt_builder = PromptBuilder()
