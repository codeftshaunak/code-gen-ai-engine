"""Code parsing utilities for extracting files and packages from AI responses."""

import re
from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class ParsedFile:
    """Represents a parsed file from AI response."""

    path: str
    content: str
    is_complete: bool = True


@dataclass
class ParsedResponse:
    """Represents parsed AI response."""

    files: List[ParsedFile]
    packages: List[str]
    commands: List[str]


def parse_ai_response(response: str) -> ParsedResponse:
    """
    Parse AI response to extract files, packages, and commands.

    Args:
        response: The AI-generated response string

    Returns:
        ParsedResponse containing files, packages, and commands
    """
    files = _extract_files(response)
    packages = _extract_packages_from_response(response)
    commands = _extract_commands(response)

    return ParsedResponse(files=files, packages=packages, commands=commands)


def _extract_files(response: str) -> List[ParsedFile]:
    """Extract file blocks from AI response using multiple patterns."""
    files_dict: Dict[str, ParsedFile] = {}

    # Pattern 1: XML-style file tags
    xml_pattern = r'<file path="([^"]+)">([\s\S]*?)(?:</file>|$)'
    for match in re.finditer(xml_pattern, response):
        path = match.group(1).strip()
        content = match.group(2).strip()
        is_complete = '</file>' in match.group(0)

        # Check for truncation indicators
        if '...' in content or '// ...' in content:
            is_complete = False

        _add_or_update_file(files_dict, path, content, is_complete)

    # Pattern 2: Markdown code blocks with path
    md_pattern = r'```(?:file )?path="([^"]+)"\n([\s\S]*?)```'
    for match in re.finditer(md_pattern, response):
        path = match.group(1).strip()
        content = match.group(2).strip()
        _add_or_update_file(files_dict, path, content, True)

    return list(files_dict.values())


def _add_or_update_file(
    files_dict: Dict[str, ParsedFile],
    path: str,
    content: str,
    is_complete: bool
):
    """Add or update file in dictionary, preferring complete versions."""
    if path in files_dict:
        existing = files_dict[path]
        # Prefer complete files
        if is_complete and not existing.is_complete:
            files_dict[path] = ParsedFile(path, content, is_complete)
        # If both complete, prefer longer version
        elif is_complete and existing.is_complete and len(content) > len(existing.content):
            files_dict[path] = ParsedFile(path, content, is_complete)
    else:
        files_dict[path] = ParsedFile(path, content, is_complete)


def _extract_packages_from_response(response: str) -> List[str]:
    """Extract package names from XML tags in AI response."""
    packages: Set[str] = set()

    # Pattern 1: Individual package tags
    single_pattern = r'<package>(.*?)</package>'
    for match in re.finditer(single_pattern, response):
        package = match.group(1).strip()
        if package:
            packages.add(package)

    # Pattern 2: Multiple packages in packages tag
    multi_pattern = r'<packages>([\s\S]*?)</packages>'
    for match in re.finditer(multi_pattern, response):
        content = match.group(1)
        # Split by newlines and commas
        for line in content.split('\n'):
            for pkg in line.split(','):
                pkg = pkg.strip().strip('-').strip()
                if pkg:
                    packages.add(pkg)

    return list(packages)


def _extract_commands(response: str) -> List[str]:
    """Extract command tags from AI response."""
    commands: List[str] = []

    pattern = r'<command>(.*?)</command>'
    for match in re.finditer(pattern, response, re.DOTALL):
        command = match.group(1).strip()
        if command:
            commands.append(command)

    return commands


def extract_packages_from_code(content: str) -> List[str]:
    """
    Extract npm packages from ES6 import statements in code.

    Args:
        content: JavaScript/TypeScript code content

    Returns:
        List of npm package names
    """
    packages: Set[str] = set()

    # Regex for ES6 imports
    import_pattern = r'import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)(?:\s*,\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+))*\s+from\s+)?[\'"]([^\'"]+)[\'"]'

    for match in re.finditer(import_pattern, content):
        import_path = match.group(1)

        # Skip relative imports
        if import_path.startswith(('.', '/', '@/')):
            continue

        # Skip built-in modules
        if import_path in ('react', 'react-dom'):
            continue

        # Extract package name (handle scoped packages)
        if import_path.startswith('@'):
            # Scoped package: @scope/package or @scope/package/subpath
            parts = import_path.split('/')
            if len(parts) >= 2:
                package_name = f"{parts[0]}/{parts[1]}"
                packages.add(package_name)
        else:
            # Regular package: package or package/subpath
            package_name = import_path.split('/')[0]
            if package_name:
                packages.add(package_name)

    return sorted(list(packages))


def normalize_file_path(file_path: str) -> str:
    """
    Normalize file path to sandbox structure.

    Args:
        file_path: Original file path from AI

    Returns:
        Normalized path for sandbox
    """
    path = file_path.strip().lstrip('/')

    # Config files that stay in root
    config_files = {
        'tailwind.config.js',
        'tailwind.config.ts',
        'vite.config.js',
        'vite.config.ts',
        'package.json',
        'package-lock.json',
        'tsconfig.json',
        'postcss.config.js',
        'postcss.config.cjs',
        '.eslintrc.js',
        '.eslintrc.cjs',
        '.prettierrc'
    }

    filename = path.split('/')[-1]

    # Auto-prefix with src/ if needed
    if (not path.startswith(('src/', 'public/')) and
        path != 'index.html' and
        filename not in config_files):
        path = 'src/' + path

    return path


def strip_css_imports(content: str, file_path: str) -> str:
    """
    Strip CSS import statements from JS/JSX/TS/TSX files.

    Args:
        content: File content
        file_path: File path to check extension

    Returns:
        Content with CSS imports removed
    """
    # Only strip from JS/JSX/TS/TSX files
    if not file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
        return content

    # Remove CSS imports
    css_import_pattern = r'import\s+[\'"].*?\.css[\'"];?\s*\n?'
    content = re.sub(css_import_pattern, '', content)

    return content


def fix_tailwind_classes(content: str) -> str:
    """
    Fix common Tailwind CSS class errors.

    Args:
        content: File content

    Returns:
        Content with fixed Tailwind classes
    """
    # Fix shadow-3xl to shadow-2xl (shadow-3xl doesn't exist)
    content = content.replace('shadow-3xl', 'shadow-2xl')

    return content
