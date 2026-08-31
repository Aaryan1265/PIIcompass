"""Firewall around the sealed ground truth.

Two independent controls guarantee the scanning pipeline never reads its own
answer key:

  check_static() : scans the pipeline's own source files for any textual
                   reference to the ground-truth location. A reference is a build
                   failure. (config.py is excluded because it only *declares* the
                   path constant; evaluate.py is excluded because it is the one
                   component allowed to read the key, after the fact.)

  sealed()       : a context manager that installs a CPython audit hook. While
                   active, any attempt to open a file inside the ground-truth
                   directory raises PermissionError, aborting the read. A
                   booby-trap unit test proves the hook fires.
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

from .config import GROUND_TRUTH_DIR, PACKAGE_DIR

# Modules that make up the scanning pipeline. None of these may reference the
# ground truth. config.py (declares the constant) and evaluate.py (allowed
# reader) are intentionally excluded.
_PIPELINE_MODULES = [
    "classifier.py", "schema_scanner.py", "code_scanner.py", "vendors.py",
    "flow_graph.py", "article30.py", "ai_draft.py", "render_svg.py", "pipeline.py",
]

_FORBIDDEN_TOKENS = ("ground_truth", "expected_pii", "GROUND_TRUTH")

_SEALED_PREFIX = os.path.abspath(str(GROUND_TRUTH_DIR)) + os.sep
_ACTIVE = False
_HOOK_INSTALLED = False


def check_static() -> list[str]:
    """Return a list of static-scan violations (empty means clean)."""
    violations: list[str] = []
    for name in _PIPELINE_MODULES:
        path = PACKAGE_DIR / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in _FORBIDDEN_TOKENS:
            if token in text:
                violations.append(f"{name}: references forbidden token '{token}'")
    return violations


def assert_static_clean() -> None:
    violations = check_static()
    if violations:
        raise RuntimeError(
            "Firewall static scan failed; the pipeline references the sealed "
            "ground truth:\n  " + "\n  ".join(violations)
        )


def _audit(event: str, args) -> None:
    if not _ACTIVE:
        return
    if event != "open":
        return
    target = args[0]
    if target is None:
        return
    try:
        resolved = os.path.abspath(os.fspath(target))
    except TypeError:
        return
    if resolved == os.path.abspath(str(GROUND_TRUTH_DIR)) or resolved.startswith(_SEALED_PREFIX):
        raise PermissionError(
            f"Firewall: the scanning pipeline attempted to open the sealed "
            f"ground truth ({resolved}). This is forbidden."
        )


def _ensure_hook() -> None:
    global _HOOK_INSTALLED
    if not _HOOK_INSTALLED:
        sys.addaudithook(_audit)
        _HOOK_INSTALLED = True


@contextmanager
def sealed():
    """Within this context, opening any file under the ground-truth dir raises."""
    global _ACTIVE
    _ensure_hook()
    previous = _ACTIVE
    _ACTIVE = True
    try:
        yield
    finally:
        _ACTIVE = previous
