"""统一源代码、发布包和外部资源目录的查找顺序。"""
import os
from pathlib import Path


def resource_roots(project):
    roots = []
    external = os.environ.get("MAAFGO_RESOURCE_DIR")
    candidates = [Path(external)] if external else []
    for root in (Path(project), Path(project).parent):
        candidates.extend((root / "assets/resource", root / "resource"))
    for path in candidates:
        path = path.resolve()
        if path.is_dir() and path not in roots:
            roots.append(path)
    return tuple(roots)
