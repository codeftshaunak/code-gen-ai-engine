"""
Code Parser Utilities
Parses AI responses to extract files, packages, and commands
"""
import re
from typing import List, Dict, Tuple


def parse_ai_response(response: str) -> Dict[str, any]:
    """
    Parse AI response to extract files, packages, and commands

    Supports XML-style tags:
    <file path="src/App.jsx">...</file>
    <package>react-router-dom</package>
    <command>npm run build</command>

    Also supports markdown code blocks with file paths
    """
    files = {}
    packages = []
    commands = []

    # Parse <file> tags
    file_pattern = r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>'
    for match in re.finditer(file_pattern, response, re.DOTALL):
        path = match.group(1)
        content = match.group(2).strip()
        files[path] = content

    # Parse markdown code blocks with file paths
    # ```jsx:src/App.jsx
    markdown_file_pattern = r'```(?:\w+)?:([^\n]+)\n(.*?)```'
    for match in re.finditer(markdown_file_pattern, response, re.DOTALL):
        path = match.group(1).strip()
        content = match.group(2).strip()
        files[path] = content

    # Parse <package> tags
    package_pattern = r'<package>(.*?)</package>'
    packages = re.findall(package_pattern, response)

    # Parse <command> tags
    command_pattern = r'<command>(.*?)</command>'
    commands = re.findall(command_pattern, response)

    # Detect packages from import statements in files
    detected_packages = detect_packages_from_code(files)
    packages.extend(detected_packages)

    # Deduplicate packages
    packages = list(set(packages))

    return {
        "files": files,
        "packages": packages,
        "commands": commands
    }


def detect_packages_from_code(files: Dict[str, str]) -> List[str]:
    """
    Detect npm packages from import statements in code

    Detects:
    - import X from 'package'
    - import { X } from 'package'
    - const X = require('package')
    """
    packages = set()

    # Patterns to match imports
    import_patterns = [
        r'import\s+.*?\s+from\s+["\']([^"\'./][^"\']*)["\']',  # ES6 imports
        r'import\s+["\']([^"\'./][^"\']*)["\']',  # Side-effect imports
        r'require\(["\']([^"\'./][^"\']*)["\']\)',  # CommonJS requires
    ]

    for file_content in files.values():
        for pattern in import_patterns:
            matches = re.findall(pattern, file_content)
            for match in matches:
                # Extract base package name (handle scoped packages)
                package = extract_package_name(match)
                if package and not is_builtin_module(package):
                    packages.add(package)

    return list(packages)


def extract_package_name(import_path: str) -> str:
    """
    Extract package name from import path

    Examples:
    - 'react-router-dom' -> 'react-router-dom'
    - 'react-router-dom/something' -> 'react-router-dom'
    - '@mui/material' -> '@mui/material'
    - '@mui/material/Button' -> '@mui/material'
    """
    if import_path.startswith("@"):
        # Scoped package: @scope/package
        parts = import_path.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return import_path
    else:
        # Regular package
        return import_path.split("/")[0]


def is_builtin_module(package_name: str) -> bool:
    """Check if package is a Node.js built-in module"""
    builtins = {
        'fs', 'path', 'http', 'https', 'url', 'os', 'util', 'events',
        'stream', 'crypto', 'zlib', 'buffer', 'process', 'child_process',
        'cluster', 'dgram', 'dns', 'net', 'readline', 'repl', 'tls',
        'tty', 'vm', 'assert', 'constants', 'module', 'querystring',
        'string_decoder', 'timers', 'v8', 'worker_threads'
    }
    return package_name in builtins


def normalize_file_path(path: str) -> str:
    """
    Normalize file path to add src/ prefix if needed

    Examples:
    - 'App.jsx' -> 'src/App.jsx'
    - 'components/Button.jsx' -> 'src/components/Button.jsx'
    - 'src/App.jsx' -> 'src/App.jsx' (no change)
    """
    # Remove leading slash if present
    path = path.lstrip("/")

    # Add src/ prefix if not already present and not a config file
    config_files = {
        'package.json', 'vite.config.js', 'tailwind.config.js',
        'postcss.config.js', '.eslintrc', 'tsconfig.json', 'index.html'
    }

    if not path.startswith("src/") and path not in config_files:
        path = f"src/{path}"

    return path
