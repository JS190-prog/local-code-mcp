from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

CANONICAL_PACKAGE_ALIAS = "_local_code_mcp_canonical"
CANONICAL_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_PACKAGE_DIR = CANONICAL_ROOT / "local_code_mcp"


def _ensure_canonical_package() -> ModuleType:
    """Load the root-level local_code_mcp package under an internal alias.

    This nested package is retained only as a compatibility shim for older launch
    configurations that start from C:/local-code-mcp/local_code_mcp. The canonical
    source package is C:/local-code-mcp/local_code_mcp.
    """
    if CANONICAL_PACKAGE_ALIAS in sys.modules:
        return sys.modules[CANONICAL_PACKAGE_ALIAS]

    init_file = CANONICAL_PACKAGE_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        CANONICAL_PACKAGE_ALIAS,
        init_file,
        submodule_search_locations=[str(CANONICAL_PACKAGE_DIR)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load canonical package from {init_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[CANONICAL_PACKAGE_ALIAS] = module
    spec.loader.exec_module(module)
    return module


def load_canonical_module(module_name: str) -> ModuleType:
    _ensure_canonical_package()
    return importlib.import_module(f"{CANONICAL_PACKAGE_ALIAS}.{module_name}")
