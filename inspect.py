from pathlib import Path

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    ".mypy_cache",
}


def print_tree(root: Path, prefix: str = "") -> None:
    """
    Recursively print a directory tree.

    Definition/Rule:
    pathlib.Path is preferred over os.path for filesystem work
    because it is more readable, safer, and cross-platform.

    Example:
    Path("/tmp").iterdir()
    """
    entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))

    for index, path in enumerate(entries):
        if path.name in EXCLUDE_DIRS:
            continue

        is_last = index == len(entries) - 1
        connector = "└── " if is_last else "├── "

        print(f"{prefix}{connector}{path.name}")

        if path.is_dir():
            extension = "    " if is_last else "│   "
            print_tree(path, prefix + extension)


def main() -> None:
    project_root = Path(
        "/Users/fabianstulzebach/dev/projects/ebook_secondbrain_pipeline"
    )

    if not project_root.exists():
        raise FileNotFoundError(f"Path does not exist: {project_root}")

    print(project_root.name)
    print_tree(project_root)


if __name__ == "__main__":
    main()
