import tkinter as tk

from analysis.dependency_graph import DependencyGraph, GraphNode


class TreeViewer:
    NODE_WIDTH = 230
    NAME_HEIGHT = 18
    LINE_HEIGHT = 15
    CARD_PADDING = 8
    H_GAP = 28
    V_GAP = 64
    MARGIN = 40

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.canvas.bind("<MouseWheel>", self._on_vertical_scroll)
        self.canvas.bind("<Shift-MouseWheel>", self._on_horizontal_scroll)

    def show(self, graph: DependencyGraph) -> None:
        self.clear()
        positions: dict[int, tuple[float, float]] = {}
        left = float(self.MARGIN)

        for root in graph.roots:
            self._layout(root, left, float(self.MARGIN), positions)
            left += self._subtree_width(root) + self.H_GAP

        for root in graph.roots:
            self._draw(root, positions)

        self._update_scrollregion()
        self.reset_view()

    def clear(self) -> None:
        self.canvas.delete("all")

    def reset_view(self) -> None:
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def _update_scrollregion(self) -> None:
        bounds = self.canvas.bbox("all")
        if bounds is None:
            self.canvas.configure(scrollregion=(0, 0, 0, 0))
            return

        _, _, x2, y2 = bounds
        margin = self.MARGIN
        self.canvas.configure(scrollregion=(0, 0, x2 + margin, y2 + margin))

    def _scroll_units(self, event: tk.Event) -> int:
        if event.delta > 0:
            return -1
        if event.delta < 0:
            return 1
        return 0

    def _on_vertical_scroll(self, event: tk.Event) -> str:
        self.canvas.yview_scroll(self._scroll_units(event), "units")
        return "break"

    def _on_horizontal_scroll(self, event: tk.Event) -> str:
        self.canvas.xview_scroll(self._scroll_units(event), "units")
        return "break"

    def _subtree_width(self, node: GraphNode) -> float:
        if not node.children:
            return float(self.NODE_WIDTH)

        total = sum(self._subtree_width(child) for child in node.children)
        total += self.H_GAP * (len(node.children) - 1)
        return max(float(self.NODE_WIDTH), total)

    def _card_height(self, node: GraphNode) -> float:
        lines = max(1, len(node.preview))
        return self.CARD_PADDING * 2 + lines * self.LINE_HEIGHT

    def _node_height(self, node: GraphNode) -> float:
        return self.NAME_HEIGHT + self._card_height(node)

    def _layout(
        self,
        node: GraphNode,
        left: float,
        top: float,
        positions: dict[int, tuple[float, float]],
    ) -> None:
        width = self._subtree_width(node)
        positions[id(node)] = (left + (width - self.NODE_WIDTH) / 2, top)

        child_left = left
        child_top = top + self._node_height(node) + self.V_GAP
        for child in node.children:
            self._layout(child, child_left, child_top, positions)
            child_left += self._subtree_width(child) + self.H_GAP

    def _draw(
        self,
        node: GraphNode,
        positions: dict[int, tuple[float, float]],
    ) -> None:
        x, y = positions[id(node)]
        self._draw_node(node, x, y)

        start_y = y + self._node_height(node)
        for child in node.children:
            child_x, child_y = positions[id(child)]
            end_y = child_y + self.NAME_HEIGHT
            self.canvas.create_line(
                x + self.NODE_WIDTH / 2,
                start_y,
                child_x + self.NODE_WIDTH / 2,
                end_y,
                fill="#546e7a",
                arrow=tk.LAST,
            )
            self.canvas.create_text(
                (x + child_x) / 2 + self.NODE_WIDTH / 2,
                (start_y + end_y) / 2,
                text="#include",
                fill="#1565c0",
                font=("Arial", 9),
            )
            self._draw(child, positions)

    def _draw_node(self, node: GraphNode, x: float, y: float) -> None:
        if node.is_system:
            fill, outline = "#c8e6c9", "#2e7d32"
        elif node.missing:
            fill, outline = "#ffcdd2", "#c62828"
        elif node.name.endswith(".h"):
            fill, outline = "#b3e5fc", "#0277bd"
        else:
            fill, outline = "#ffffff", "#212121"

        card_y = y + self.NAME_HEIGHT
        card_height = self._card_height(node)
        self.canvas.create_text(
            x + self.NODE_WIDTH / 2,
            y + self.NAME_HEIGHT / 2,
            text=node.name,
            fill="#1a1a1a",
            font=("Arial", 11, "bold"),
        )
        self.canvas.create_rectangle(
            x,
            card_y,
            x + self.NODE_WIDTH,
            card_y + card_height,
            fill=fill,
            outline=outline,
            width=2,
        )

        text_y = card_y + self.CARD_PADDING

        for line in node.preview:
            if line.startswith("#include") and "<" in line:
                color = "#b71c1c"
            elif line.startswith("#include"):
                color = "#1565c0"
            else:
                color = "#1a1a1a"
            self.canvas.create_text(
                x + 8,
                text_y,
                text=line,
                anchor="nw",
                fill=color,
                font=("Courier New", 9),
            )
            text_y += self.LINE_HEIGHT
