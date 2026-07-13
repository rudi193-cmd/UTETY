#!/usr/bin/env python3
"""Package-wide structural boundaries — the policy tests that scale with the tree.

test_no_egress.py guards utety/core specifically. These tests guard the WHOLE
package, so they apply automatically to every module any future phase adds
(student front, teacher console, sync spine, ...):

1. THE SEAM IS THE ONLY DOOR. No module under utety/ may import a
   network-capable library except the modules explicitly allowlisted in
   _EGRESS_ALLOWED (today: only utety/knowledge.py, the quarantined seam).
   Adding a second door must be a deliberate, reviewed act — editing the
   allowlist here — never an accident.

2. STDLIB-ONLY. Every module under utety/ imports only the standard library
   or the package itself (ground rules: Termux/Windows parity, small enough
   to audit, nothing to pip-install on a child's device). A new third-party
   dependency must be argued for in review, starting with the failure of
   this test.

Both checks are AST-based (no imports executed) and walk utety/ recursively,
so they need no updating as the tree grows.
"""
import ast
import sys
import unittest
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent.parent / "utety"
_PKG_NAME = "utety"

# Modules that can move bytes off the machine (superset of test_no_egress's
# list; urllib/http forbidden at top level here because package code has no
# reason to import ANY of them outside the seam).
_NETWORK = {
    "socket", "ssl", "urllib", "http", "ftplib", "smtplib", "poplib",
    "imaplib", "telnetlib", "asyncio", "requests", "httpx", "aiohttp",
    "urllib3", "websocket", "websockets", "grpc", "paramiko", "boto3",
    "xmlrpc", "webbrowser", "subprocess", "ctypes",
}

# The ONLY modules allowed to import network-capable libraries. Paths relative
# to utety/. Growing this list is a privacy decision — treat an edit here like
# an edit to the consent gate, and record the reviewed reason inline.
_EGRESS_ALLOWED = {
    # The seam: the one true egress path (de-identified concept queries out,
    # sourced cards back). Audited 2026-07-13.
    "knowledge.py",
    # The reading-room server: http.server LISTENER + urllib.parse only — it
    # accepts loopback connections, it does not originate any. Its default
    # bind is pinned to 127.0.0.1 by TestLocalFirstBinding below; audited
    # 2026-07-13 (docs/audit-bite-4-web-2026-07-13.md).
    "web/server.py",
}


def _py_files() -> list[Path]:
    return sorted(_PKG_DIR.rglob("*.py"))


def _imports_of(path: Path) -> set[str]:
    """Top-level names of absolute imports in a file (relative imports skipped)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


class TestSeamIsTheOnlyDoor(unittest.TestCase):
    def test_no_module_outside_the_seam_imports_network(self):
        offenders = {}
        for f in _py_files():
            rel = f.relative_to(_PKG_DIR).as_posix()
            if rel in _EGRESS_ALLOWED:
                continue
            bad = _imports_of(f) & _NETWORK
            if bad:
                offenders[rel] = sorted(bad)
        self.assertEqual(
            offenders, {},
            f"modules outside the knowledge seam import network/exec libraries: "
            f"{offenders}. The seam (utety/knowledge.py) is the only door — if a "
            "new module genuinely needs egress, add it to _EGRESS_ALLOWED in a "
            "reviewed change; do not import around the boundary.",
        )

    def test_allowlist_entries_exist(self):
        # A stale allowlist (file renamed/moved) would silently widen the door.
        for rel in _EGRESS_ALLOWED:
            self.assertTrue(
                (_PKG_DIR / rel).is_file(),
                f"_EGRESS_ALLOWED entry {rel!r} does not exist — update the list",
            )


class TestLocalFirstBinding(unittest.TestCase):
    def test_reading_room_binds_loopback_by_default(self):
        # The student front must not be reachable from the LAN. serve()'s
        # default host is part of the privacy posture: changing it to
        # "0.0.0.0" (or "") exposes a child's tutor to the network and must
        # be a reviewed decision, not a default drift.
        import inspect

        from utety.web.server import serve

        default_host = inspect.signature(serve).parameters["host"].default
        self.assertEqual(
            default_host, "127.0.0.1",
            "the reading room's default bind must stay loopback-only",
        )


class TestStdlibOnly(unittest.TestCase):
    def test_package_imports_only_stdlib_and_itself(self):
        stdlib = set(sys.stdlib_module_names)
        offenders = {}
        for f in _py_files():
            third_party = {
                name for name in _imports_of(f)
                if name != _PKG_NAME and name not in stdlib
            }
            if third_party:
                offenders[f.relative_to(_PKG_DIR).as_posix()] = sorted(third_party)
        self.assertEqual(
            offenders, {},
            f"third-party imports found: {offenders}. utety is stdlib-only "
            "(Termux/Windows parity; nothing to install on a child's device). "
            "A new dependency is a project decision, not an import statement.",
        )


if __name__ == "__main__":
    unittest.main()
