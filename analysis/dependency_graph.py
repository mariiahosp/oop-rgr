from enum import Enum
from pathlib import Path

from analysis.header_catalog import HeaderCatalog, HeaderCategory
from models.source_file import IncludeRef, SourceFile


class NodeKind(Enum):
    SOURCE = "source"
    HEADER = "header"
    SYSTEM = "system"
    GROUP = "group"
    MISSING = "missing"


class GraphNode:
    def __init__(
        self,
        key: str,
        title: str,
        kind: NodeKind,
        lines: list[str] | None = None,
        description: str = "",
        path: Path | None = None,
    ):
        self.key = key
        self.title = title
        self.kind = kind
        self.lines = lines or []
        self.description = description
        self.path = path
        self.members: list[str] = []
        self.level = 0

    def add_member(self, name: str) -> None:
        if name not in self.members:
            self.members.append(name)

    def __repr__(self) -> str:
        return f"GraphNode(title='{self.title}', kind={self.kind.value}, level={self.level})"


class GraphEdge:
    def __init__(self, included: GraphNode, includer: GraphNode):
        self.included = included
        self.includer = includer
        self.is_back = False

    @property
    def upper(self) -> GraphNode:
        return self.includer if self.includer.level < self.included.level else self.included

    @property
    def lower(self) -> GraphNode:
        return self.included if self.upper is self.includer else self.includer

    def __repr__(self) -> str:
        return f"GraphEdge({self.included.title} -> {self.includer.title})"


class DependencyGraph:
    _ROOT_ORDER = {".cpp": 0, ".rc": 1}

    _GROUPS = {
        HeaderCategory.WINDOWS_API: (
            "group:winapi", "Інші заголовочні файли Windows API"
        ),
        HeaderCategory.STANDARD: (
            "group:std", "Заголовочні файли стандартних бібліотек C++"
        ),
        HeaderCategory.EXTERNAL: (
            "group:external", "Інші зовнішні заголовочні файли"
        ),
    }

    _WINDOWS_KEY = "system:windows.h"

    def __init__(
        self,
        sources: list[SourceFile],
        main_file: Path | None = None,
        catalog: HeaderCatalog | None = None,
    ):
        self._catalog = catalog or HeaderCatalog()
        self._sources = sorted(sources, key=self._root_sort_key)
        self._by_path = {source.path.resolve(): source for source in sources}
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self.roots: list[GraphNode] = []
        self._edge_keys: set[tuple[str, str]] = set()

        self._build(main_file)
        self._mark_back_edges()
        self._assign_levels()

    @property
    def level_count(self) -> int:
        if not self.nodes:
            return 0
        return max(node.level for node in self.nodes.values()) + 1

    @property
    def levels(self) -> list[list[GraphNode]]:
        layers: list[list[GraphNode]] = [[] for _ in range(self.level_count)]
        for node in self.nodes.values():
            layers[node.level].append(node)
        return layers

    @property
    def cycle_count(self) -> int:
        return sum(1 for edge in self.edges if edge.is_back)

    def _root_sort_key(self, source: SourceFile) -> tuple[int, str]:
        return self._ROOT_ORDER.get(source.path.suffix.lower(), 2), source.name.lower()

    def _build(self, main_file: Path | None) -> None:
        included: set[Path] = set()
        for source in self._sources:
            own_path = source.path.resolve()
            for include in source.includes:
                if include.resolved is not None and include.resolved.resolve() != own_path:
                    included.add(include.resolved.resolve())

        main = None
        if main_file is not None:
            main = self._by_path.get(Path(main_file).resolve())

        if main is not None:
            candidates = [main] + [
                source
                for source in self._sources
                if source is not main
                and source.path.suffix.lower() == ".rc"
                and source.path.resolve() not in included
            ]
        else:
            candidates = [
                source for source in self._sources
                if source.path.resolve() not in included
            ]

        for source in candidates:
            self.roots.append(self._visit(source))

        if main is None:
            for source in self._sources:
                if self._source_key(source) not in self.nodes:
                    self.roots.append(self._visit(source))

        windows = self.nodes.get(self._WINDOWS_KEY)
        if windows is not None:
            self._add_edge(self._group_node(HeaderCategory.WINDOWS_API), windows)

    def _source_key(self, source: SourceFile) -> str:
        return f"file:{source.path.resolve()}"

    def _visit(self, source: SourceFile) -> GraphNode:
        key = self._source_key(source)
        if key in self.nodes:
            return self.nodes[key]

        is_header = source.path.suffix.lower() == ".h"
        node = GraphNode(
            key,
            source.name,
            NodeKind.HEADER if is_header else NodeKind.SOURCE,
            path=source.path,
        )
        if not source.includes and source.description:
            node.description = source.description
        else:
            node.lines = list(source.preview_lines)
        self.nodes[key] = node

        for include in source.includes:
            target = self._include_target(include)
            if target is not node:
                self._add_edge(target, node)
        return node

    def _include_target(self, include: IncludeRef) -> GraphNode:
        if include.resolved is not None:
            source = self._by_path.get(include.resolved.resolve())
            if source is not None:
                return self._visit(source)

        category = self._catalog.classify(include.name, include.is_system)
        if category is HeaderCategory.WINDOWS_MAIN:
            return self._get_or_create(
                GraphNode(
                    self._WINDOWS_KEY,
                    "windows.h",
                    NodeKind.SYSTEM,
                    description="Головний заголовочний файл Windows API",
                )
            )

        if category is HeaderCategory.UNKNOWN:
            return self._get_or_create(
                GraphNode(
                    f"missing:{include.name.lower()}",
                    include.name,
                    NodeKind.MISSING,
                    description="Файл не знайдено в папці проекту",
                )
            )

        group = self._group_node(category)
        group.add_member(include.display_name)
        return group

    def _group_node(self, category: HeaderCategory) -> GraphNode:
        key, description = self._GROUPS[category]
        return self._get_or_create(
            GraphNode(key, "*.h", NodeKind.GROUP, description=description)
        )

    def _get_or_create(self, node: GraphNode) -> GraphNode:
        return self.nodes.setdefault(node.key, node)

    def _add_edge(self, included: GraphNode, includer: GraphNode) -> None:
        key = (included.key, includer.key)
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append(GraphEdge(included, includer))

    def _mark_back_edges(self) -> None:
        """Marks edges that close an include cycle, so the rest forms a DAG."""
        outgoing: dict[str, list[GraphEdge]] = {key: [] for key in self.nodes}
        for edge in self.edges:
            outgoing[edge.includer.key].append(edge)

        state: dict[str, str] = {}
        starts = self.roots + list(self.nodes.values())

        for start in starts:
            if start.key in state:
                continue
            state[start.key] = "active"
            stack = [(start, iter(outgoing[start.key]))]

            while stack:
                node, edges = stack[-1]
                edge = next(edges, None)
                if edge is None:
                    state[node.key] = "done"
                    stack.pop()
                    continue

                child = edge.included
                child_state = state.get(child.key)
                if child_state == "active":
                    edge.is_back = True
                elif child_state is None:
                    state[child.key] = "active"
                    stack.append((child, iter(outgoing[child.key])))

    def _assign_levels(self) -> None:
        """Longest path from the top; files that include nothing go to the bottom level."""
        forward = [edge for edge in self.edges if not edge.is_back]
        incoming = {key: 0 for key in self.nodes}
        children: dict[str, list[GraphNode]] = {key: [] for key in self.nodes}
        for edge in forward:
            incoming[edge.included.key] += 1
            children[edge.includer.key].append(edge.included)

        queue = [node for node in self.nodes.values() if incoming[node.key] == 0]
        for node in queue:
            node.level = 0

        while queue:
            node = queue.pop(0)
            for child in children[node.key]:
                child.level = max(child.level, node.level + 1)
                incoming[child.key] -= 1
                if incoming[child.key] == 0:
                    queue.append(child)

        bottom = max((node.level for node in self.nodes.values()), default=0)
        has_parent = {edge.included.key for edge in forward}
        for node in self.nodes.values():
            if not children[node.key] and node.key in has_parent:
                node.level = bottom
