from collections.abc import Callable

from analysis.dependency_graph import DependencyGraph, GraphEdge, GraphNode


class NodeBox:
    """Size of a drawn node and the y offsets where arrows attach to it."""

    def __init__(
        self,
        width: float,
        height: float,
        top_anchor: float,
        bottom_anchor: float,
        card_width: float | None = None,
        title_width: float = 0.0,
    ):
        self.width = width
        self.height = height
        self.top_anchor = top_anchor
        self.bottom_anchor = bottom_anchor
        self.card_width = width if card_width is None else card_width
        self.title_width = title_width


class PlacedNode:
    def __init__(self, node: GraphNode, box: NodeBox, x: float, y: float):
        self.node = node
        self.box = box
        self.x = x
        self.y = y


class Route:
    def __init__(self, edge: GraphEdge, points: list[tuple[float, float]]):
        self.edge = edge
        self.points = points

    @property
    def arrow_at_end(self) -> bool:
        return self.edge.includer is self.edge.upper


class _Slot:
    """A node or a bend point of a long edge inside one layer."""

    def __init__(self, layer: int, width: float, node: GraphNode | None = None):
        self.layer = layer
        self.width = width
        self.node = node
        self.center = 0.0
        self.up: list[_Slot] = []
        self.down: list[_Slot] = []


class GraphLayout:
    H_GAP = 36
    V_GAP = 70
    DUMMY_WIDTH = 14
    ORDER_PASSES = 12
    POSITION_PASSES = 16
    PORT_SPREAD = 0.6

    def __init__(self, graph: DependencyGraph, measure: Callable[[GraphNode], NodeBox]):
        self.graph = graph
        self._measure = measure
        self.nodes: dict[str, PlacedNode] = {}
        self.routes: list[Route] = []
        self.layer_tops: list[float] = []
        self.layer_heights: list[float] = []
        self.width = 0.0
        self.height = 0.0

        self._boxes = {key: measure(node) for key, node in graph.nodes.items()}
        self._layers: list[list[_Slot]] = []
        self._chains: list[tuple[GraphEdge, list[_Slot]]] = []

        if graph.nodes:
            self._create_slots()
            self._order_layers()
            self._place_horizontally()
            self._place_vertically()
            self._build_routes()

    def _create_slots(self) -> None:
        by_key: dict[str, _Slot] = {}
        self._layers = [[] for _ in range(self.graph.level_count)]

        for layer, nodes in enumerate(self.graph.levels):
            for node in nodes:
                slot = _Slot(layer, self._boxes[node.key].width, node)
                by_key[node.key] = slot
                self._layers[layer].append(slot)

        for edge in self.graph.edges:
            lower, upper = by_key[edge.lower.key], by_key[edge.upper.key]
            chain = [lower]
            for layer in range(lower.layer - 1, upper.layer, -1):
                dummy = _Slot(layer, self.DUMMY_WIDTH)
                self._layers[layer].append(dummy)
                chain.append(dummy)
            chain.append(upper)

            for below, above in zip(chain, chain[1:]):
                below.up.append(above)
                above.down.append(below)
            self._chains.append((edge, chain))

    def _order_layers(self) -> None:
        best = [list(layer) for layer in self._layers]
        best_crossings = self._count_crossings()

        for iteration in range(self.ORDER_PASSES):
            downward = iteration % 2 == 0
            indexes = range(1, len(self._layers)) if downward else range(
                len(self._layers) - 2, -1, -1
            )
            for index in indexes:
                self._sort_by_barycenter(index, downward)

            crossings = self._count_crossings()
            if crossings < best_crossings:
                best_crossings = crossings
                best = [list(layer) for layer in self._layers]
            if best_crossings == 0:
                break

        self._layers = best

    def _sort_by_barycenter(self, index: int, use_upper: bool) -> None:
        reference = self._layers[index - 1] if use_upper else self._layers[index + 1]
        position = {id(slot): order for order, slot in enumerate(reference)}

        weights: dict[int, float] = {}
        for order, slot in enumerate(self._layers[index]):
            neighbours = slot.up if use_upper else slot.down
            if neighbours:
                weights[id(slot)] = sum(position[id(n)] for n in neighbours) / len(neighbours)
            else:
                weights[id(slot)] = float(order)

        self._layers[index].sort(key=lambda slot: weights[id(slot)])

    def _count_crossings(self) -> int:
        total = 0
        for index in range(1, len(self._layers)):
            upper_position = {id(slot): order for order, slot in enumerate(self._layers[index - 1])}
            segments = []
            for order, slot in enumerate(self._layers[index]):
                for above in slot.up:
                    segments.append((upper_position[id(above)], order))

            for i, (top_a, bottom_a) in enumerate(segments):
                for top_b, bottom_b in segments[i + 1:]:
                    if (top_a - top_b) * (bottom_a - bottom_b) < 0:
                        total += 1
        return total

    def _separation(self, left: _Slot, right: _Slot) -> float:
        gap = self.H_GAP if left.node and right.node else self.H_GAP / 2
        return (left.width + right.width) / 2 + gap

    def _place_horizontally(self) -> None:
        for layer in self._layers:
            x = 0.0
            for order, slot in enumerate(layer):
                if order > 0:
                    x += self._separation(layer[order - 1], slot)
                slot.center = x
            shift = x / 2
            for slot in layer:
                slot.center -= shift

        for iteration in range(self.POSITION_PASSES):
            downward = iteration % 2 == 0
            indexes = range(1, len(self._layers)) if downward else range(
                len(self._layers) - 2, -1, -1
            )
            for index in indexes:
                self._align_layer(self._layers[index], downward)

        left = min(slot.center - slot.width / 2 for layer in self._layers for slot in layer)
        for layer in self._layers:
            for slot in layer:
                slot.center -= left

        self.width = max(slot.center + slot.width / 2 for layer in self._layers for slot in layer)

    def _align_layer(self, layer: list[_Slot], use_upper: bool) -> None:
        """Moves slots towards their neighbours while keeping order and gaps."""
        desired = []
        for slot in layer:
            neighbours = slot.up if use_upper else slot.down
            if neighbours:
                desired.append(sum(n.center for n in neighbours) / len(neighbours))
            else:
                desired.append(slot.center)

        count = len(layer)
        forward = desired[:]
        for i in range(1, count):
            forward[i] = max(desired[i], forward[i - 1] + self._separation(layer[i - 1], layer[i]))

        backward = desired[:]
        for i in range(count - 2, -1, -1):
            backward[i] = min(desired[i], backward[i + 1] - self._separation(layer[i], layer[i + 1]))

        for i, slot in enumerate(layer):
            slot.center = (forward[i] + backward[i]) / 2

    def _place_vertically(self) -> None:
        y = 0.0
        for layer in self._layers:
            height = max(
                (self._boxes[slot.node.key].height for slot in layer if slot.node),
                default=0.0,
            )
            self.layer_tops.append(y)
            self.layer_heights.append(height)

            for slot in layer:
                if slot.node is not None:
                    box = self._boxes[slot.node.key]
                    self.nodes[slot.node.key] = PlacedNode(
                        slot.node, box, slot.center - box.width / 2, y
                    )
            y += height + self.V_GAP

        self.height = y - self.V_GAP

    def _build_routes(self) -> None:
        top_ports = self._ports(
            [(chain[0], chain[1]) for _, chain in self._chains], avoid_title=True
        )
        bottom_ports = self._ports([(chain[-1], chain[-2]) for _, chain in self._chains])

        for index, (edge, chain) in enumerate(self._chains):
            lower = self.nodes[chain[0].node.key]
            upper = self.nodes[chain[-1].node.key]

            points = [(top_ports[index], lower.y + lower.box.top_anchor)]
            for dummy in chain[1:-1]:
                top = self.layer_tops[dummy.layer]
                points.append((dummy.center, top + self.layer_heights[dummy.layer]))
                points.append((dummy.center, top))
            points.append((bottom_ports[index], upper.y + upper.box.bottom_anchor))

            self.routes.append(Route(edge, points))

    def _ports(
        self,
        attachments: list[tuple[_Slot, _Slot]],
        avoid_title: bool = False,
    ) -> list[float]:
        """Spreads edges along a node side, ordered by where they go."""
        grouped: dict[int, list[int]] = {}
        for index, (slot, _) in enumerate(attachments):
            grouped.setdefault(id(slot), []).append(index)

        ports = [0.0] * len(attachments)
        for indexes in grouped.values():
            placed = self.nodes[attachments[indexes[0]][0].node.key]
            indexes.sort(key=lambda i: attachments[i][1].center)

            card_width = placed.box.card_width
            margin = card_width * (1 - self.PORT_SPREAD) / 2
            start = placed.x + margin
            end = placed.x + card_width - margin
            if avoid_title:
                after_title = placed.x + placed.box.title_width + 10
                if end - after_title >= card_width * 0.3:
                    start = max(start, after_title)

            for order, index in enumerate(indexes):
                fraction = (order + 1) / (len(indexes) + 1)
                ports[index] = start + (end - start) * fraction
        return ports
