from __future__ import annotations

import unittest

from fluent_wrapper.introspection import build_api_tree, render_markdown_context, render_pyi_from_tree


class _Leaf:
    def ping(self) -> str:
        return "pong"


class _Root:
    def __init__(self) -> None:
        self.child = _Leaf()

    def run(self) -> None:
        return None


class IntrospectionTests(unittest.TestCase):
    def test_build_tree_and_render_pyi(self) -> None:
        tree = build_api_tree(_Root(), root_name="SolverSession", max_depth=3)
        pyi = render_pyi_from_tree(tree)

        self.assertIn("class SolverSession", pyi)
        self.assertIn("def run", pyi)
        self.assertIn("child:", pyi)

    def test_render_markdown(self) -> None:
        tree = build_api_tree(_Root(), root_name="MeshingWorkflow", max_depth=3)
        md = render_markdown_context(tree, title="Meshing API Context")

        self.assertIn("# Meshing API Context", md)
        self.assertIn("`MeshingWorkflow`", md)


if __name__ == "__main__":
    unittest.main()

