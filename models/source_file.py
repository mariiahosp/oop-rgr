from pathlib import Path


class IncludeRef:
    def __init__(self, name: str, is_system: bool, resolved: Path | None = None):
        self.name = name
        self.is_system = is_system
        self.resolved = resolved

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

    @property
    def name(self) -> str:
        return self.path.name

    def add_include(self, include: IncludeRef) -> None:
        self.includes.append(include)

    def __repr__(self) -> str:
        return f"SourceFile(name='{self.name}', includes={len(self.includes)})"
