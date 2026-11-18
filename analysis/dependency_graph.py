from pathlib import Path

from models.source_file import IncludeRef, SourceFile


class GraphNode:
    def __init__(
        self,
        name: str,
        is_system: bool,
        path: Path | None = None,
        preview: list[str] | None = None,
    ):
        self.name = name
        self.is_system = is_system
        self.path = path
        self.preview = preview or []
        self.children: list[GraphNode] = []

    @property
    def missing(self) -> bool:
        return self.path is None and not self.is_system

    def __repr__(self) -> str:
        return f"GraphNode(name='{self.name}', children={len(self.children)})"


class DependencyGraph:
    def __init__(self, sources: list[SourceFile], main_file: Path | None = None):
        self._sources = sources
        self._by_path = {source.path.resolve(): source for source in sources}
        self.roots: list[GraphNode] = []
        self._build(main_file)

    def _build(self, main_file: Path | None) -> None:
        if main_file is not None:
            source = self._by_path.get(Path(main_file).resolve())
            if source is not None:
                self.roots.append(self._expand(source, set()))
            return

        for source in self._sources:
            if source.path.suffix.lower() in {".cpp", ".rc"}:
                self.roots.append(self._expand(source, set()))

    def _expand(self, source: SourceFile, trail: set[Path]) -> GraphNode:
        path = source.path.resolve()
        node = GraphNode(
            source.name,
            is_system=False,
            path=source.path,
            preview=source.preview_lines,
        )
        if path in trail:
            return node

        trail = set(trail)
        trail.add(path)
        for include in source.includes:
            node.children.append(self._include_node(include, trail))
        return node

    def _include_node(self, include: IncludeRef, trail: set[Path]) -> GraphNode:
        if include.resolved is not None:
            source = self._by_path.get(include.resolved.resolve())
            if source is not None:
                return self._expand(source, trail)

        if include.is_system:
            preview = ["системний заголовок"]
        else:
            preview = ["файл не знайдено"]
        return GraphNode(include.name, is_system=include.is_system, preview=preview)
