"""Public synthetic example. Never presented as a historical model output."""

from importlib.resources import files
from pathlib import Path

from .core import CapsuleError


def create_demo(destination: Path) -> Path:
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise CapsuleError(f"Demo destination must be empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    resources = files("secondlook").joinpath("demo")
    for name in ("index.html", "capsule.json"):
        (destination / name).write_text(resources.joinpath(name).read_text(encoding="utf-8"), encoding="utf-8")
    return destination / "capsule.json"
