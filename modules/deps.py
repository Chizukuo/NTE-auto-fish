"""Dependency validation helpers for NTE Auto-Fish."""
import importlib
import sys

# CLI-only dependencies (no dearpygui, no keyboard)
CLI_PACKAGES: dict[str, str] = {
    "cv2": "opencv-python-headless",
    "numpy": "numpy",
    "mss": "mss",
    "pydirectinput": "pydirectinput",
    "screeninfo": "screeninfo",
}

# GUI adds these on top of CLI
GUI_PACKAGES: dict[str, str] = {
    **CLI_PACKAGES,
    "dearpygui": "dearpygui",
    "keyboard": "keyboard",
}


def _is_importable(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def get_missing_dependencies(packages: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """Return [(module_name, package_name), ...] for dependencies that cannot be imported."""
    if packages is None:
        packages = CLI_PACKAGES

    missing = []
    for module_name, package_name in packages.items():
        if not _is_importable(module_name):
            missing.append((module_name, package_name))
    return missing


def _format_missing_message(missing: list[tuple[str, str]]) -> str:
    lines = ["ERROR: Missing required dependencies:"]
    for module_name, package_name in missing:
        lines.append(f"  - {package_name} (import: {module_name})")
    lines.append("")
    lines.append("Install dependencies with:")
    lines.append(f"  {sys.executable} -m pip install -r requirements.txt")
    return "\n".join(lines)


def ensure_dependencies(packages: dict[str, str] | None = None) -> None:
    """Raise RuntimeError when one or more required dependencies are missing."""
    missing = get_missing_dependencies(packages)
    if missing:
        raise RuntimeError(_format_missing_message(missing))


def exit_if_missing_dependencies(packages: dict[str, str] | None = None) -> None:
    """Print a friendly error and exit when dependencies are missing."""
    missing = get_missing_dependencies(packages)
    if missing:
        print(_format_missing_message(missing))
        sys.exit(1)
