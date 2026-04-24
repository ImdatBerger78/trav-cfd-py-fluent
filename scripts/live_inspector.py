from fluent_wrapper.session import FluentSessionWrapper, FluentLaunchConfig, LaunchMode
from fluent_wrapper.introspection import build_solver_tree, render_pyi_from_tree
from pathlib import Path

wrapper = FluentSessionWrapper()
session = None

def start_fluent(case_path: str):
    global session
    config = FluentLaunchConfig(mode=LaunchMode.SOLVER, show_gui=True, processor_count=24)
    session = wrapper.launch(config)
    wrapper.load_case(Path(case_path))
    print("\n[READY] Fluent is open. Use the GUI, then run 'refresh(\"1\")'")

def refresh(selection: str = "1"):
    menu = {
        "1": "setup.models",
        "2": "setup.boundary_conditions",
        "3": "setup.cell_zone_conditions",
        "4": "setup.materials",
        "5": "solution.methods",
        "6": "solution.run_calculation"
    }
    targets = [menu[s.strip()] for s in selection.split(",") if s.strip() in menu]
    update_context(targets)

def update_context(targets: list[str]):
    if not session:
        print("[ERROR] Run start_fluent('path/to/case') first.")
        return
    output_dir = Path("generated/stubs")
    output_dir.mkdir(parents=True, exist_ok=True)
    for target_path in targets:
        obj = session
        for part in target_path.split('.'):
            obj = getattr(obj, part)
        tree = build_solver_tree(obj, root_name=target_path.replace(".", "_"), max_depth=5)
        file_name = f"{target_path.replace('.', '_')}.pyi"
        (output_dir / file_name).write_text(render_pyi_from_tree(tree))
        print(f"[OK] Updated: {file_name}")