import os
import pathlib

def initialize_registry(path: str):
    """Set up a new project registry at given path"""
    base = pathlib.Path(path)
    base.mkdir(parents=True, exist_ok=True)

    (base / ".gitignore").write_text("index.db\n")
    (base / "config.yml").write_text("# Registry Configuration\n")
    for folder in ["programs", "projects", "missions", "actions"]:
        (base / folder).mkdir(exist_ok=True)

    print(f"✅ Registry initialized at: {base.resolve()}")
