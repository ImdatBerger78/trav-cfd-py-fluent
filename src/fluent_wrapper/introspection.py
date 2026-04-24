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
    """Get attribute without crashing traversal when PyFluent proxy access fails."""

    try:
        return getattr(obj, attr)
    except Exception:
        return None


def build_api_tree(
        root_obj: Any,
        root_name: str = "SolverSession",
        max_depth: int = 6,
        max_children_per_node: int = 200,
) -> ApiNode:
    """Recursively scan a session object and build a conservative API tree."""

    visited: set[int] = set()
    IGNORE_TYPES = (str, int, float, bool, bytes, complex, type(None))

    # Filter out standard list/dict methods to reduce context window noise
    NOISE_METHODS = {
        "append", "clear", "copy", "count", "extend", "index", "insert",
        "pop", "remove", "reverse", "sort", "fromkeys", "get", "items",
        "keys", "popitem", "setdefault", "update", "values"
    }

    def walk(obj: Any, name: str, depth: int) -> ApiNode:
        if isinstance(obj, IGNORE_TYPES):
            return ApiNode(name=name)

        node = ApiNode(name=name)
        obj_id = id(obj)
        if depth > max_depth or obj_id in visited:
            return node
        visited.add(obj_id)

        # 1. Capture dictionary keys FIRST (Crucial for PyFluent TaskObjects/Zones)
        if hasattr(obj, "keys") and callable(getattr(obj, "keys")):
            try:
                for key in list(obj.keys())[:max_children_per_node]:
                    if isinstance(key, str):
                        key_name = f"['{key}']"
                        # Attempt to walk into the specific task to capture its arguments
                        try:
                            child_obj = obj[key]
                            node.children[key_name] = walk(child_obj, key_name, depth + 1)
                        except Exception:
                            node.children[key_name] = ApiNode(name=key_name)
            except Exception:
                pass

        # 2. Capture standard attributes
        names = sorted(n for n in dir(obj) if n and not n.startswith("_"))[:max_children_per_node]
        for attr_name in names:
            if not attr_name.isidentifier() or attr_name in NOISE_METHODS:
                continue

            attr = safe_getattr(obj, attr_name)
            if attr is None:
                continue

            # THE FIX: PyFluent proxies (like TaskObject) are callable, but they are also containers.
            # We must treat them as objects to crawl, not just as endpoints/methods.
            is_container = hasattr(attr, "keys") or hasattr(attr, "get_object_names")

            if callable(attr) and not is_container:
                node.methods.add(attr_name)
                continue

            child = walk(attr, attr_name, depth + 1)
            node.children[attr_name] = child

        return node

    return walk(root_obj, root_name, depth=0)


def _pascal_from_path(path: str) -> str:
    parts = [p for p in path.replace(".", "_").split("_") if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)


def render_pyi_from_tree(tree: ApiNode) -> str:
    """Render a pyi module from an API tree with nested class typing links."""

    lines: list[str] = [
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
    ]

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

    lines.extend(
        [
            f"class {tree.name}({root_class}):",
            "    ...",
            "",
        ]
    )
    return "\n".join(lines)


def render_markdown_context(tree: ApiNode, title: str) -> str:
    """Render a compact markdown reference suitable for local AI context files."""

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

