"""GUI entry point for NTE Auto-Fish."""
from modules.deps import GUI_PACKAGES, exit_if_missing_dependencies

exit_if_missing_dependencies(GUI_PACKAGES)

from gui.app import FishingGUI  # noqa: E402

if __name__ == "__main__":
    app = FishingGUI()
    app.run()
