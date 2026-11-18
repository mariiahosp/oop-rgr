import tkinter as tk

from analysis.dependency_graph import DependencyGraph, GraphNode


class TreeViewer:
    NODE_WIDTH = 150
    NODE_HEIGHT = 36
    H_GAP = 24
    V_GAP = 56
    MARGIN = 24

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas

    def show(self, graph: DependencyGraph) -> None:
        self.clear()
        positions: dict[int, tuple[float, float]] = {}
        left = float(self.MARGIN)

        for root in graph.roots:
            self._layout(root, left, float(self.MARGIN), positions)
            left += self._subtree_width(root) + self.H_GAP

        for root in graph.roots:
            self._draw(root, positions)

        bounds = self.canvas.bbox("all")
        self.canvas.configure(scrollregion=bounds or (0, 0, 0, 0))
        self.reset_view()

    def clear(self) -> None:
        self.canvas.delete("all")

    def reset_view(self) -> None:
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def _subtree_width(self, node: GraphNode) -> float:
        if not node.children:
            return float(self.NODE_WIDTH)

        total = sum(self._subtree_width(child) for child in node.children)
        total += self.H_GAP * (len(node.children) - 1)
        return max(float(self.NODE_WIDTH), total)

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
        child_top = top + self.NODE_HEIGHT + self.V_GAP
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

        for child in node.children:
            child_x, child_y = positions[id(child)]
            self.canvas.create_line(
                x + self.NODE_WIDTH / 2,
                y + self.NODE_HEIGHT,
                child_x + self.NODE_WIDTH / 2,
                child_y,
                fill="#546e7a",
                arrow=tk.LAST,
            )
            self._draw(child, positions)

    def _draw_node(self, node: GraphNode, x: float, y: float) -> None:
        if node.is_system:
            fill, outline = "#e8f5e9", "#2e7d32"
        elif node.missing:
            fill, outline = "#ffebee", "#c62828"
        else:
            fill, outline = "#e3f2fd", "#1565c0"

        self.canvas.create_rectangle(
            x,
            y,
            x + self.NODE_WIDTH,
            y + self.NODE_HEIGHT,
            fill=fill,
            outline=outline,
            width=2,
        )
        self.canvas.create_text(
            x + self.NODE_WIDTH / 2,
            y + self.NODE_HEIGHT / 2,
            text=node.name,
            fill="#1a1a1a",
            font=("Arial", 10),
        )
