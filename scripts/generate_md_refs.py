from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fluent_wrapper.introspection import build_api_tree, render_markdown_context
from fluent_wrapper.session import FluentLaunchConfig, FluentSessionWrapper, LaunchMode

DEFAULT_BASE_DIR = Path(r"S:\SIMULATIONSDATEN\SIMULATIONS\AKW\imma\trav-cfd-py-fluent")


def _find_workflow_file(base_dir: Path, explicit_workflow: Optional[Path]) -> Path:
    if explicit_workflow is not None:
        return explicit_workflow.expanduser().resolve()

    mesh_dir = base_dir / "02_Mesh"
    matches = sorted(mesh_dir.glob("*.wft"))
    if not matches:
        raise FileNotFoundError(f"No .wft files found in: {mesh_dir}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate markdown context for active meshing workflow APIs."
    )
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    parser.add_argument(
        "--workflow-file",
        type=Path,
        default=None,
        help="Optional explicit .wft file path. If omitted, first *.wft in 02_Mesh is used.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "generated" / "docs" / "meshing_api_context.md",
    )
    parser.add_argument("--max-depth", type=int, default=5)
    args = parser.parse_args()

    base_dir = args.base_dir.expanduser().resolve()
    workflow_file = _find_workflow_file(base_dir, args.workflow_file)
    output_file = args.output.expanduser().resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    wrapper = FluentSessionWrapper()
    try:
        session = wrapper.launch(FluentLaunchConfig(mode=LaunchMode.MESHING))
        wrapper.load_workflow(workflow_file)

        # Meshing-specific context should focus on workflow branch when available.
        root_obj = getattr(session, "workflow", session)
        tree = build_api_tree(root_obj, root_name="MeshingWorkflow", max_depth=args.max_depth)
        markdown = render_markdown_context(tree, title="Meshing API Context")
        output_file.write_text(markdown, encoding="utf-8")

        print(f"[OK] Loaded workflow: {workflow_file}")
        print(f"[OK] Wrote markdown context: {output_file}")
        return 0
    except Exception as exc:
        print(f"[ERROR] Markdown context generation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        wrapper.close()


if __name__ == "__main__":
    raise SystemExit(main())

