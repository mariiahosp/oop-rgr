import re
import tkinter as tk
import tkinter.font as tkfont

from analysis.dependency_graph import DependencyGraph, GraphNode, NodeKind
from viewer.graph_layout import GraphLayout, NodeBox, PlacedNode, Route


class _Row:
    def __init__(self, text: str, style: str, height: float):
        self.text = text
        self.style = style
        self.height = height


class GraphViewer:
    TITLE_HEIGHT = 22
    CARD_PADDING = 8
    MIN_CARD_WIDTH = 150
    MAX_CARD_WIDTH = 320
    TEXT_WIDTH = 190
    MAX_MEMBER_ROWS = 3
    STACK_OFFSET = 7
    STACK_COUNT = 2
    MARGIN = 40
    LEVEL_LABEL_GAP = 30
    SCROLL_STEP = 20

    _COLORS = {
        NodeKind.SOURCE: ("#ffffff", "#262626"),
        NodeKind.HEADER: ("#ccf6fb", "#262626"),
        NodeKind.SYSTEM: ("#9ef0c4", "#262626"),
        NodeKind.GROUP: ("#9ef0c4", "#262626"),
        NodeKind.MISSING: ("#ffd9d9", "#c62828"),
    }
    _KEYWORD_COLOR = "#1f3fbf"
    _NAME_COLOR = "#a31515"
    _COMMENT_COLOR = "#808080"
    _CODE_COLOR = "#4d4d4d"
    _EDGE_COLOR = "#262626"
    _CYCLE_COLOR = "#c62828"

    _INCLUDE_LINE = re.compile(r"^(#\s*include)(\s*)(.*)$")

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self._code_font = tkfont.Font(family="Courier New", size=9)
        self._text_font = tkfont.Font(family="Times New Roman", size=10)
        self._title_font = tkfont.Font(family="Arial", size=11, weight="bold")
        self._label_font = tkfont.Font(family="Arial", size=9)
        self._level_font = tkfont.Font(family="Arial", size=11)
        self._rows: dict[str, tuple[list[_Row], float]] = {}
        self._content_bounds: tuple[float, float, float, float] | None = None

        self.canvas.configure(
            xscrollincrement=self.SCROLL_STEP, yscrollincrement=self.SCROLL_STEP
        )
        self._bind_scrolling()

    def show(self, graph: DependencyGraph) -> None:
        self.clear()
        layout = GraphLayout(graph, self._measure)
        if not layout.nodes:
            return

        offset_x = self.MARGIN
        if graph.level_count > 1:
            offset_x += self._level_label_width() + self.LEVEL_LABEL_GAP
        offset_y = self.MARGIN

        self._draw_level_labels(layout, offset_y)
        for route in layout.routes:
            self._draw_edge(route, offset_x, offset_y)
        for placed in layout.nodes.values():
            self._draw_node(placed, offset_x, offset_y)
        self._draw_edge_labels(layout.routes, offset_x, offset_y)

        self._content_bounds = (
            0,
            0,
            offset_x + layout.width + self.MARGIN,
            offset_y + layout.height + self.MARGIN,
        )
        self._update_scrollregion()
        self.reset_view()

    def clear(self) -> None:
        self.canvas.delete("all")
        self._rows.clear()
        self._content_bounds = None
        self._update_scrollregion()

    def reset_view(self) -> None:
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    # ---- scrolling and resizing ----

    def _bind_scrolling(self) -> None:
        self.canvas.bind("<MouseWheel>", self._on_vertical_scroll)
        self.canvas.bind("<Shift-MouseWheel>", self._on_horizontal_scroll)
        self.canvas.bind("<Button-4>", lambda _: self._scroll_y(-1))
        self.canvas.bind("<Button-5>", lambda _: self._scroll_y(1))
        self.canvas.bind("<Shift-Button-4>", lambda _: self._scroll_x(-1))
        self.canvas.bind("<Shift-Button-5>", lambda _: self._scroll_x(1))
        self.canvas.bind("<Up>", lambda _: self._scroll_y(-1))
        self.canvas.bind("<Down>", lambda _: self._scroll_y(1))
        self.canvas.bind("<Left>", lambda _: self._scroll_x(-1))
        self.canvas.bind("<Right>", lambda _: self._scroll_x(1))
        self.canvas.bind("<Button-1>", lambda _: self.canvas.focus_set())
        self.canvas.bind("<Configure>", lambda _: self._update_scrollregion())

    def _scroll_y(self, units: int) -> str:
        self.canvas.yview_scroll(units, "units")
        return "break"

    def _scroll_x(self, units: int) -> str:
        self.canvas.xview_scroll(units, "units")
        return "break"

    def _wheel_units(self, event: tk.Event) -> int:
        if event.delta > 0:
            return -1
        if event.delta < 0:
            return 1
        return 0

    def _on_vertical_scroll(self, event: tk.Event) -> str:
        return self._scroll_y(self._wheel_units(event))

    def _on_horizontal_scroll(self, event: tk.Event) -> str:
        return self._scroll_x(self._wheel_units(event))

    def _update_scrollregion(self) -> None:
        if self._content_bounds is None:
            self.canvas.configure(scrollregion=(0, 0, 0, 0))
            return

        x1, y1, x2, y2 = self._content_bounds
        visible_width = self.canvas.winfo_width()
        content_width = x2 - x1
        if visible_width > content_width:
            extra = (visible_width - content_width) / 2
            x1, x2 = x1 - extra, x2 + extra
        self.canvas.configure(scrollregion=(x1, y1, x2, y2))

    # ---- node measuring ----

    def _measure(self, node: GraphNode) -> NodeBox:
        rows, card_width = self._prepare_rows(node)
        card_height = self.CARD_PADDING * 2 + sum(row.height for row in rows)
        stack = self.STACK_OFFSET * self.STACK_COUNT if node.kind is NodeKind.GROUP else 0
        return NodeBox(
            width=card_width + stack,
            height=self.TITLE_HEIGHT + card_height + stack,
            top_anchor=self.TITLE_HEIGHT,
            bottom_anchor=self.TITLE_HEIGHT + card_height,
            card_width=card_width,
            title_width=self._title_font.measure(node.title),
        )

    def _prepare_rows(self, node: GraphNode) -> tuple[list[_Row], float]:
        if node.key in self._rows:
            return self._rows[node.key]

        code_height = self._code_font.metrics("linespace") + 2
        text_height = self._text_font.metrics("linespace") + 1
        inner_limit = self.MAX_CARD_WIDTH - self.CARD_PADDING * 2

        rows: list[_Row] = []
        for line in node.lines:
            rows.append(_Row(self._fit_line(line, self._code_font, inner_limit), "code", code_height))

        if node.description:
            for line in self._wrap(node.description, self._text_font, self.TEXT_WIDTH):
                rows.append(_Row(line, "text", text_height))

        if node.members:
            member_rows = self._wrap(", ".join(node.members), self._code_font, self.TEXT_WIDTH)
            if len(member_rows) > self.MAX_MEMBER_ROWS:
                member_rows = member_rows[:self.MAX_MEMBER_ROWS - 1] + ["..."]
            for line in member_rows:
                rows.append(_Row(line, "member", code_height))

        if not rows:
            rows.append(_Row("(порожній файл)", "text", text_height))

        widest = 0.0
        for row in rows:
            font = self._text_font if row.style == "text" else self._code_font
            widest = max(widest, font.measure(row.text))

        card_width = widest + self.CARD_PADDING * 2
        card_width = max(card_width, self._title_font.measure(node.title) + self.CARD_PADDING)
        card_width = min(max(card_width, self.MIN_CARD_WIDTH), self.MAX_CARD_WIDTH)

        self._rows[node.key] = (rows, card_width)
        return rows, card_width

    def _fit_line(self, line: str, font: tkfont.Font, max_width: float) -> str:
        if font.measure(line) <= max_width:
            return line

        ellipsis = "..."
        trimmed = line
        while trimmed and font.measure(trimmed + ellipsis) > max_width:
            trimmed = trimmed[:-1]
        return trimmed + ellipsis

    def _wrap(self, text: str, font: tkfont.Font, max_width: float) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}" if current else word
            if font.measure(candidate) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = self._fit_line(word, font, max_width)
        if current:
            lines.append(current)
        return lines

    # ---- drawing ----

    def _level_label_width(self) -> float:
        return max(
            self._level_font.measure("верхній рівень"),
            self._level_font.measure("нижній рівень"),
        )

    def _draw_level_labels(self, layout: GraphLayout, offset_y: float) -> None:
        if len(layout.layer_tops) < 2:
            return

        for index, text in ((0, "верхній рівень"), (-1, "нижній рівень")):
            top = layout.layer_tops[index] + offset_y
            self.canvas.create_text(
                self.MARGIN,
                top + self.TITLE_HEIGHT / 2,
                text=text,
                anchor="w",
                fill="#262626",
                font=self._level_font,
            )

    def _draw_edge(self, route: Route, offset_x: float, offset_y: float) -> None:
        coordinates: list[float] = []
        for x, y in route.points:
            coordinates.extend((x + offset_x, y + offset_y))

        is_cycle = route.edge.is_back
        self.canvas.create_line(
            *coordinates,
            fill=self._CYCLE_COLOR if is_cycle else self._EDGE_COLOR,
            width=1.2,
            dash=(5, 3) if is_cycle else (),
            arrow=tk.LAST if route.arrow_at_end else tk.FIRST,
            arrowshape=(10, 12, 4),
        )

    def _draw_edge_labels(self, routes: list[Route], offset_x: float, offset_y: float) -> None:
        stagger = (0.5, 0.3, 0.7)
        counters: dict[str, int] = {}

        for route in routes:
            if route.arrow_at_end:
                (x1, y1), (x2, y2) = route.points[-2], route.points[-1]
            else:
                (x2, y2), (x1, y1) = route.points[0], route.points[1]

            includer = route.edge.includer.key
            order = counters.get(includer, 0)
            counters[includer] = order + 1
            t = stagger[order % len(stagger)]

            text_id = self.canvas.create_text(
                x1 + (x2 - x1) * t + offset_x,
                y1 + (y2 - y1) * t + offset_y,
                text="#include (цикл)" if route.edge.is_back else "#include",
                fill=self._CYCLE_COLOR if route.edge.is_back else self._KEYWORD_COLOR,
                font=self._label_font,
            )
            bounds = self.canvas.bbox(text_id)
            if bounds is not None:
                background = self.canvas.create_rectangle(
                    bounds[0] - 2, bounds[1], bounds[2] + 2, bounds[3],
                    fill="white", outline="",
                )
                self.canvas.tag_raise(text_id, background)

    def _draw_node(self, placed: PlacedNode, offset_x: float, offset_y: float) -> None:
        node, box = placed.node, placed.box
        x, y = placed.x + offset_x, placed.y + offset_y
        card_top = y + box.top_anchor
        card_bottom = y + box.bottom_anchor
        card_width = box.card_width
        fill, outline = self._COLORS[node.kind]
        dash = (4, 2) if node.kind is NodeKind.MISSING else ()

        if node.kind is NodeKind.GROUP:
            for step in range(self.STACK_COUNT, 0, -1):
                shift = step * self.STACK_OFFSET
                self.canvas.create_rectangle(
                    x + shift, card_top + shift, x + card_width + shift, card_bottom + shift,
                    fill=fill, outline=outline, width=1.5,
                )

        self.canvas.create_rectangle(
            x, card_top, x + card_width, card_bottom,
            fill=fill, outline=outline, width=1.5, dash=dash,
        )
        self.canvas.create_text(
            x,
            y + self.TITLE_HEIGHT / 2,
            text=node.title,
            anchor="w",
            fill="#1a1a1a",
            font=self._title_font,
        )

        rows, _ = self._prepare_rows(node)
        text_y = card_top + self.CARD_PADDING
        for row in rows:
            if row.style == "code":
                self._draw_code_line(row.text, x + self.CARD_PADDING, text_y)
            else:
                self.canvas.create_text(
                    x + card_width / 2,
                    text_y,
                    text=row.text,
                    anchor="n",
                    justify="center",
                    fill="#1a1a1a" if row.style == "text" else self._NAME_COLOR,
                    font=self._text_font if row.style == "text" else self._code_font,
                )
            text_y += row.height

    def _draw_code_line(self, line: str, x: float, y: float) -> None:
        match = self._INCLUDE_LINE.match(line)
        if match is not None:
            keyword = match.group(1) + match.group(2)
            self.canvas.create_text(
                x, y, text=keyword, anchor="nw",
                fill=self._KEYWORD_COLOR, font=self._code_font,
            )
            self.canvas.create_text(
                x + self._code_font.measure(keyword), y, text=match.group(3),
                anchor="nw", fill=self._NAME_COLOR, font=self._code_font,
            )
            return

        is_comment = line == "..." or line.startswith(("//", "/*"))
        self.canvas.create_text(
            x, y, text=line, anchor="nw",
            fill=self._COMMENT_COLOR if is_comment else self._CODE_COLOR,
            font=self._code_font,
        )
