from pathlib import Path


class IncludeRef:
    def __init__(self, name: str, is_system: bool, resolved: Path | None = None):
        self.name = name
        self.is_system = is_system
        self.resolved = resolved

    @property
    def display_name(self) -> str:
        return f"<{self.name}>" if self.is_system else f'"{self.name}"'

    def __repr__(self) -> str:
        return (
            f"IncludeRef(name='{self.name}', is_system={self.is_system}, "
            f"resolved={self.resolved!r})"
        )


class SourceFile:
    def __init__(self, path: Path):
        self.path = path
        self.includes: list[IncludeRef] = []
        self.preview_lines: list[str] = []
        self.description = ""

    @property
    def name(self) -> str:
        return self.path.name

    def add_include(self, include: IncludeRef) -> None:
        self.includes.append(include)

    def __repr__(self) -> str:
        return f"SourceFile(name='{self.name}', includes={len(self.includes)})"
