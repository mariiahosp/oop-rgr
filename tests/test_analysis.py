import tempfile
import unittest
from pathlib import Path

from analysis.dependency_graph import DependencyGraph, NodeKind
from analysis.include_analyzer import IncludeAnalyzer
from models.project import Project
from viewer.graph_layout import GraphLayout, NodeBox

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def build_graph(folder: Path, main_file: Path | None = None) -> DependencyGraph:
    project = Project(str(folder), str(main_file) if main_file else None)
    return DependencyGraph(IncludeAnalyzer().analyze(project), project.main_file)


def titles(graph: DependencyGraph) -> list[str]:
    return sorted(node.title for node in graph.nodes.values())


class IncludeAnalyzerTest(unittest.TestCase):
    def test_ignores_comments_and_disabled_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "main.cpp").write_text(
                '#include "a.h"\n'
                '// #include "line_comment.h"\n'
                '/* #include "block_comment.h" */\n'
                "#if 0\n"
                '#include "disabled.h"\n'
                "#else\n"
                '#include "enabled.h"\n'
                "#endif\n"
                "#  include <vector>\n",
                encoding="utf-8",
            )
            sources = IncludeAnalyzer().analyze(Project(folder))

        names = [include.name for include in sources[0].includes]
        self.assertEqual(names, ["a.h", "enabled.h", "vector"])

    def test_preview_shows_includes_separated_by_dots(self):
        sources = IncludeAnalyzer().analyze(Project(str(SAMPLES / "MyProg")))
        main = next(source for source in sources if source.name == "MyProg.cpp")

        self.assertEqual(main.preview_lines[0], "//-- головний файл проекту --")
        self.assertIn('#include "framework.h"', main.preview_lines)
        self.assertIn("...", main.preview_lines)


class DependencyGraphTest(unittest.TestCase):
    def test_every_file_is_drawn_once(self):
        graph = build_graph(SAMPLES / "MyProg")

        self.assertEqual(
            titles(graph),
            ["*.h", "*.h", "MyProg.cpp", "MyProg.h", "MyProg.rc", "framework.h",
             "resource.h", "targetver.h", "windows.h"],
        )
        targetver = next(n for n in graph.nodes.values() if n.title == "targetver.h")
        includers = sorted(e.includer.title for e in graph.edges if e.included is targetver)
        self.assertEqual(includers, ["MyProg.rc", "framework.h"])

    def test_quoted_windows_header_is_system(self):
        graph = build_graph(SAMPLES / "MyProg")
        kinds = {node.title: node.kind for node in graph.nodes.values()}

        self.assertEqual(kinds["windows.h"], NodeKind.SYSTEM)
        self.assertNotIn(NodeKind.MISSING, kinds.values())

    def test_levels_go_from_sources_to_leaves(self):
        graph = build_graph(SAMPLES / "MyProg")
        level = {node.title: node.level for node in graph.nodes.values() if node.title != "*.h"}

        self.assertEqual(level["MyProg.cpp"], 0)
        self.assertEqual(level["MyProg.rc"], 0)
        self.assertEqual(level["targetver.h"], graph.level_count - 1)
        self.assertEqual(level["resource.h"], graph.level_count - 1)
        for edge in graph.edges:
            self.assertLess(edge.includer.level, edge.included.level)

    def test_main_file_limits_the_graph(self):
        folder = SAMPLES / "cycle_and_missing"
        graph = build_graph(folder, folder / "main.cpp")

        self.assertEqual([root.title for root in graph.roots], ["main.cpp"])

    def test_cycle_and_missing_file(self):
        graph = build_graph(SAMPLES / "cycle_and_missing")
        kinds = {node.title: node.kind for node in graph.nodes.values()}

        self.assertEqual(graph.cycle_count, 1)
        self.assertEqual(kinds["config.h"], NodeKind.MISSING)
        self.assertNotIn("disabled.h", kinds)
        self.assertNotIn("commented_out.h", kinds)


class GraphLayoutTest(unittest.TestCase):
    def test_nodes_in_a_layer_do_not_overlap(self):
        graph = build_graph(SAMPLES / "MyProg")
        layout = GraphLayout(graph, lambda node: NodeBox(200, 80, 20, 80))

        for nodes in graph.levels:
            placed = sorted((layout.nodes[n.key] for n in nodes), key=lambda p: p.x)
            for left, right in zip(placed, placed[1:]):
                self.assertLessEqual(left.x + left.box.width, right.x)

        self.assertEqual(len(layout.routes), len(graph.edges))


if __name__ == "__main__":
    unittest.main()
