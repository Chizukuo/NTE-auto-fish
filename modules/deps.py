"""Dependency auto-detection and installation for NTE Auto-Fish."""
import importlib
import subprocess
import sys

# CLI-only dependencies (no dearpygui, no keyboard)
CLI_PACKAGES: dict[str, str] = {
    "cv2": "opencv-python-headless",
    "numpy": "numpy",
    "mss": "mss",
    "pydirectinput": "pydirectinput",
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


def _pip_available() -> bool:
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _install(package_name: str) -> bool:
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package_name],
        )
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_dependencies(packages: dict[str, str] | None = None) -> None:
    """Check that all required packages are importable; install if missing."""
    if packages is None:
        packages = CLI_PACKAGES

    missing = [mod for mod in packages if not _is_importable(mod)]
    if not missing:
        return

    if not _pip_available():
        print("ERROR: The following required packages are missing:")
        for mod in missing:
            print(f"  - {packages[mod]} (import: {mod})")
        print()
        print("pip is not available. Please install Python and pip, then run:")
        print(f"  {sys.executable} -m pip install -r requirements.txt")
        sys.exit(1)

    still_missing = []
    for mod in missing:
        pkg = packages[mod]
        print(f"Installing {pkg}...")
        if _install(pkg):
            print(f"  {pkg} installed successfully.")
        else:
            still_missing.append(pkg)

    if still_missing:
        print("ERROR: Failed to install the following packages:")
        for pkg in still_missing:
            print(f"  - {pkg}")
        print(f"Try manually: {sys.executable} -m pip install {' '.join(still_missing)}")
        sys.exit(1)

    importlib.invalidate_caches()
