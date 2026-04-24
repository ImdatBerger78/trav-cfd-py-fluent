from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fluent_wrapper.introspection import build_api_tree, render_pyi_from_tree
from fluent_wrapper.session import FluentLaunchConfig, FluentSessionWrapper, LaunchMode

DEFAULT_BASE_DIR = Path(r"S:\SIMULATIONSDATEN\SIMULATIONS\AKW\imma\trav-cfd-py-fluent")


def _find_case_file(base_dir: Path, explicit_case: Optional[Path]) -> Path:
    if explicit_case is not None:
        return explicit_case.expanduser().resolve()

    prepost = base_dir / "03_PrePost"
    matches = sorted(prepost.glob("*.cas*"))
    if not matches:
        raise FileNotFoundError(f"No .cas files found in: {prepost}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate static .pyi stubs from an active solver session."
    )
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    parser.add_argument(
        "--case-file",
        type=Path,
        default=None,
        help="Optional explicit .cas file path. If omitted, first *.cas in 03_PrePost is used.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "generated" / "stubs" / "solver_session.pyi",
    )
    parser.add_argument("--max-depth", type=int, default=6)
    args = parser.parse_args()

    base_dir = args.base_dir.expanduser().resolve()
    case_file = _find_case_file(base_dir, args.case_file)
    output_file = args.output.expanduser().resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    wrapper = FluentSessionWrapper()
    try:
        session = wrapper.launch(FluentLaunchConfig(mode=LaunchMode.SOLVER))
        wrapper.load_case(case_file)
        print(f"[OK] Loaded case: {case_file}")

        # --- NEW: Interactive Selection Menu ---
        print("\n" + "=" * 50)
        print("  PyFluent Context Extraction Menu")
        print("=" * 50)

        options = {
            "1": ("Setup: Models (Viscous, Energy, Multiphase...)", "setup.models"),
            "2": ("Setup: Boundary Conditions", "setup.boundary_conditions"),
            "3": ("Setup: Cell Zone Conditions", "setup.cell_zone_conditions"),
            "4": ("Setup: Materials", "setup.materials"),
            "5": ("Solution: Methods", "solution.methods"),
            "6": ("Solution: Run Calculation", "solution.run_calculation"),
            "7": ("Solution: Report Definitions", "solution.report_definitions"),
        }

        for key, (desc, path) in options.items():
            print(f"  [{key}] {desc}")

        print("\nType the numbers you want to extract, separated by commas (e.g., 1,2,6)")
        choice = input("\nYour selection: ").strip()

        targets = []
        for num in choice.split(','):
            num = num.strip()
            if num in options:
                targets.append(options[num][1])

        if not targets:
            print("[WARNING] No valid selection made. Exiting without generating stubs.")
            return 0

        print(f"\n[INFO] Extracting the following branches: {targets}")

        # Helper to fetch nested objects from the active session
        def get_nested_attr(base_obj, path):
            current = base_obj
            for part in path.split('.'):
                current = getattr(current, part)
            return current

        # Extract only the chosen targets
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("from __future__ import annotations\nfrom typing import Any\n\n")

            for target_path in targets:
                print(f"--> Crawling branch: {target_path} ...")
                target_obj = get_nested_attr(session, target_path)

                # Render the stubs for this specific branch
                tree = build_api_tree(target_obj, root_name=target_path.replace(".", "_"), max_depth=5)
                stub_text = render_pyi_from_tree(tree)
                f.write(stub_text + "\n\n")

        print(f"[OK] Wrote targeted stubs: {output_file}")
        tree = build_api_tree(session, root_name="SolverSession", max_depth=args.max_depth)
        stub_text = render_pyi_from_tree(tree)
        output_file.write_text(stub_text, encoding="utf-8")

        print(f"[OK] Loaded case: {case_file}")
        print(f"[OK] Wrote stubs: {output_file}")
        return 0
    except Exception as exc:
        print(f"[ERROR] Stub generation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        wrapper.close()


if __name__ == "__main__":
    raise SystemExit(main())

