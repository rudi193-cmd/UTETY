#!/usr/bin/env python3
"""The load-bearing test: the local-first core has NO network path.

Ground rule 3 (build-plan §0) is enforced structurally, not by policy. Student
data cannot leave the device because the store imports no networking library.
This test proves the invariant by parsing the AST of every module under
utety/core/ and asserting none of them import a network-capable stdlib or
third-party module — transitively across the package's own imports.

If a future change adds `import urllib` (or socket, http, requests, ...) to the
data core, this test fails loudly. The consented-sync spine, when built, must
live OUTSIDE utety/core/ so this guarantee holds for the store.
"""
import ast
import unittest
from pathlib import Path

# Modules that can move bytes off the machine — directly (network) or via an
# escape hatch (spawning a process, calling foreign code). If the on-device
# core imports any of these (directly or via another core module), the
# local-first guarantee is broken.
_FORBIDDEN = {
    "socket", "ssl", "urllib", "http", "ftplib", "smtplib", "poplib",
    "imaplib", "telnetlib", "asyncio", "requests", "httpx", "aiohttp",
    "urllib3", "websocket", "websockets", "grpc", "paramiko", "boto3",
    "xmlrpc", "webbrowser", "subprocess", "ctypes",
}

_CORE_DIR = Path(__file__).resolve().parent.parent / "utety" / "core"


def _imported_modules(source: str) -> set[str]:
    """Top-level module names imported by a source file."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:  # skip relative (in-package) imports
                names.add(node.module.split(".")[0])
    return names


class TestNoEgress(unittest.TestCase):
    def test_core_modules_import_no_network_library(self):
        core_files = sorted(_CORE_DIR.glob("*.py"))
        self.assertTrue(core_files, "no core modules found to audit")
        offenders = {}
        for f in core_files:
            imported = _imported_modules(f.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN
            if bad:
                offenders[f.name] = sorted(bad)
        self.assertEqual(
            offenders, {},
            f"local-first core imports network libraries: {offenders}. "
            "Student data must not have an egress path — move any sync code "
            "outside utety/core/.",
        )

    def test_importing_store_does_not_load_network_modules(self):
        # Beyond static analysis: importing the store in a subprocess must not
        # pull a network-CAPABLE module into sys.modules through any transitive
        # path. Checked at full module-name granularity: on Python 3.11/3.12 the
        # stdlib's own pathlib imports urllib.parse (pure string manipulation,
        # cannot move bytes), so forbidding the top-level 'urllib' name would
        # fail on stdlib behavior, not on anything the core does. The modules
        # that can actually open a connection are listed exactly.
        import subprocess
        import sys

        code = (
            "import sys; import utety.core.store; "
            "net={'socket','ssl','urllib.request','urllib.error','http.client',"
            "'ftplib','smtplib','poplib','imaplib','requests','httpx','aiohttp'};"
            "loaded=net & set(sys.modules);"
            "print(','.join(sorted(loaded)))"
        )
        repo_root = str(Path(__file__).resolve().parent.parent)
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, cwd=repo_root,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        loaded = out.stdout.strip()
        self.assertEqual(
            loaded, "",
            f"importing utety.core.store loaded network modules: {loaded}",
        )


if __name__ == "__main__":
    unittest.main()
