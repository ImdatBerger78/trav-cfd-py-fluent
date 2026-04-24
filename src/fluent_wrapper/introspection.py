from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApiNode:
    """Simple API tree node generated from runtime object traversal."""
    name: str
    children: dict[str, "ApiNode"] = field(default_factory=dict)
    methods: set[str] = field(default_factory=set)


def safe_getattr(obj: Any, attr: str) -> Any:
    try:
        return getattr(obj, attr)
    except Exception:
        return None


# ==========================================
# ENGINE 1: THE SOLVER CRAWLER
# ==========================================
def build_solver_tree(
        root_obj: Any,
        root_name: str = "SolverSession",
        max_depth: int = 5,
        max_children_per_node: int = 200,
) -> ApiNode:
    """Highly fault-tolerant crawler for the Solver state machine."""
    visited: set[int] = set()
    IGNORE_TYPES = (str, int, float, bool, bytes, complex, type(None), list, dict, tuple, set)

    NOISE_METHODS = {
        "append", "clear", "copy", "count", "extend", "index", "insert",
        "pop", "remove", "reverse", "sort", "fromkeys", "get", "items",
        "keys", "popitem", "setdefault", "update", "values",
        "get_active_child_names", "get_active_command_names", "get_active_query_names",
        "get_attr", "get_attrs", "get_state", "set_state", "print_state", "is_active",
        "is_read_only", "child_names", "command_names", "query_names", "flproxy",
        "fluent_name", "obj_name", "python_name", "python_path", "to_python_keys", "to_scheme_keys"
    }

    def walk(obj: Any, name: str, depth: int) -> ApiNode:
        if isinstance(obj, IGNORE_TYPES):
            return ApiNode(name=name)

        node = ApiNode(name=name)
        obj_id = id(obj)
        if depth > max_depth or obj_id in visited:
            return node
        visited.add(obj_id)

        try:
            names = sorted(n for n in dir(obj) if n and not n.startswith("_"))[:max_children_per_node]
        except Exception:
            names = []

        for attr_name in names:
            if not attr_name.isidentifier() or attr_name in NOISE_METHODS:
                continue

            attr = safe_getattr(obj, attr_name)
            if attr is None:
                continue

            try:
                is_container = hasattr(attr, "get_state") or hasattr(attr, "child_names")
            except Exception:
                is_container = False

            if callable(attr) and not is_container:
                node.methods.add(attr_name)
                continue

            try:
                node.children[attr_name] = walk(attr, attr_name, depth + 1)
            except Exception:
                node.children[attr_name] = ApiNode(name=attr_name)

        return node

    return walk(root_obj, root_name, depth=0)


# ==========================================
# ENGINE 2: THE MESHING CRAWLER
# ==========================================
def build_meshing_tree(
        root_obj: Any,
        root_name: str = "MeshingWorkflow",
        max_depth: int = 6,
        max_children_per_node: int = 200,
) -> ApiNode:
    """Strict, targeted crawler for the Meshing Datamodel and TaskObjects."""
    visited: set[int] = set()
    IGNORE_TYPES = (str, int, float, bool, bytes, complex, type(None), list, dict, tuple, set)

    def walk(obj: Any, name: str, depth: int) -> ApiNode:
        if isinstance(obj, IGNORE_TYPES):
            return ApiNode(name=name)

        node = ApiNode(name=name)
        obj_id = id(obj)
        if depth > max_depth or obj_id in visited:
            return node
        visited.add(obj_id)

        # Meshing specifically uses get_object_names() for TaskObjects
        try:
            if hasattr(obj, "get_object_names") and callable(getattr(obj, "get_object_names")):
                for key in list(obj.get_object_names())[:max_children_per_node]:
                    key_name = f"['{key}']"
                    try:
                        child_obj = obj[key]
                        node.children[key_name] = walk(child_obj, key_name, depth + 1)
                    except Exception:
                        node.children[key_name] = ApiNode(name=key_name)
        except Exception:
            pass

        try:
            names = sorted(n for n in dir(obj) if n and not n.startswith("_"))[:max_children_per_node]
        except Exception:
            names = []

        for attr_name in names:
            if not attr_name.isidentifier():
                continue

            attr = safe_getattr(obj, attr_name)
            if attr is None:
                continue

            # Identify containers strictly by Ansys Meshing signatures
            is_container = hasattr(attr, "get_object_names") or attr_name == "TaskObject"

            if callable(attr) and not is_container:
                # Do not document noisy dictionary/list methods in the workflow
                if attr_name not in {"append", "clear", "pop", "insert", "remove", "update", "values", "items"}:
                    node.methods.add(attr_name)
                continue

            try:
                node.children[attr_name] = walk(attr, attr_name, depth + 1)
            except Exception:
                node.children[attr_name] = ApiNode(name=attr_name)

        return node

    return walk(root_obj, root_name, depth=0)


# ==========================================
# RENDERERS (Unchanged)
# ==========================================
def _pascal_from_path(path: str) -> str:
    parts = [p for p in path.replace(".", "_").split("_") if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)


def render_pyi_from_tree(tree: ApiNode) -> str:
    lines: list[str] = ["from __future__ import annotations", "", "from typing import Any", ""]
    class_defs: dict[str, list[str]] = {}

    def emit(node: ApiNode, path: str) -> str:
        class_name = _pascal_from_path(path)
        body: list[str] = []
        for method_name in sorted(node.methods):
            body.append(f"    def {method_name}(self, *args: Any, **kwargs: Any) -> Any: ...")
        for child_name in sorted(node.children):
            child_node = node.children[child_name]
            child_class = emit(child_node, f"{path}_{child_name}")
            body.append(f"    {child_name}: {child_class}")
        if not body:
            body = ["    ..."]
        class_defs[class_name] = [f"class {class_name}:", *body, ""]
        return class_name

    root_class = emit(tree, tree.name)
    for class_name in sorted(class_defs):
        lines.extend(class_defs[class_name])
    lines.extend([f"class {tree.name}({root_class}):", "    ...", ""])
    return "\n".join(lines)


def render_markdown_context(tree: ApiNode, title: str) -> str:
    lines = [f"# {title}", "", "## API Tree", ""]

    def write_node(node: ApiNode, depth: int) -> None:
        indent = "  " * depth
        lines.append(f"{indent}- `{node.name}`")
        for method_name in sorted(node.methods):
            lines.append(f"{indent}  - `() {method_name}`")
        for child_name in sorted(node.children):
            write_node(node.children[child_name], depth + 1)

    write_node(tree, 0)
    lines.append("")
    return "\n".join(lines)