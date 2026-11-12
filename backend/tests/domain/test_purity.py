"""The domain layer is pure Python: standard library and other domain modules only."""

import ast
import sys
from pathlib import Path

import pytest

DOMAIN = Path(__file__).parents[2] / "app" / "domain"
MODULES = sorted(DOMAIN.glob("*.py"))


def _imported_modules(path: Path) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _is_allowed(module: str) -> bool:
    top_level = module.split(".")[0]
    return (
        module == "app.domain"
        or module.startswith("app.domain.")
        or (top_level in sys.stdlib_module_names)
    )


def test_domain_modules_were_found() -> None:
    assert len(MODULES) > 1


@pytest.mark.parametrize("path", MODULES, ids=lambda path: path.name)
def test_domain_module_imports_only_the_standard_library_and_the_domain(path: Path) -> None:
    disallowed = sorted(m for m in _imported_modules(path) if not _is_allowed(m))

    assert disallowed == []
