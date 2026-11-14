
from pathlib import Path


class Project:
    SUPPORTED_EXTENSIONS = {".cpp", ".h", ".rc"}

    def __init__(self, root_path: str, main_file: str | None = None):
        self.root_path = Path(root_path)
        self.main_file = Path(main_file) if main_file else None

    @property
    def name(self) -> str:
        return self.root_path.name

    def get_source_files(self) -> list[Path]:
        return sorted(
            file for file in self.root_path.iterdir()
            if file.is_file()
            and file.suffix.lower() in self.SUPPORTED_EXTENSIONS
        )

    def __repr__(self) -> str:
        return f"Project(name='{self.name}', path='{self.root_path}')"
