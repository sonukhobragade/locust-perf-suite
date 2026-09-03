#!/usr/bin/env python3
"""Check requirements.txt against what the source actually imports.

    python tools/check_deps.py

Two failures are reported:

  undeclared  a module is imported but nothing in requirements.txt provides it.
              This is the dangerous one. `flask` sat in this state: it worked
              only because Locust happened to install Flask for its own web UI,
              so the suite depended on a package it never asked for.

  unused      a package is pinned but nothing imports it. This is how the file
              reached 24 entries of which 14 were dead, and 342MB of install
              for a 77MB tool.

A package may be declared without being imported when it is deliberately
pinned, so ALLOWED_UNIMPORTED lists those with a reason. Adding to that list is
a decision someone makes on purpose, which is the point.
"""

from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# requirements name -> module name it provides, where they differ.
DIST_TO_MODULE = {
    "python-dotenv": "dotenv",
    "prometheus-client": "prometheus_client",
    "grpcio": "grpc",
    "grpcio-tools": "grpc_tools",
    "pyyaml": "yaml",
    "psycopg2-binary": "psycopg2",
    "confluent-kafka": "confluent_kafka",
    "paho-mqtt": "paho",
    "websocket-client": "websocket",
    "influxdb-client": "influxdb_client",
    "locust-plugins": "locust_plugins",
    "pytest-html": "pytest_html",
    "jsonpath-ng": "jsonpath_ng",
}

# Declared on purpose without a direct import, with the reason.
ALLOWED_UNIMPORTED = {
    "protobuf": "imported by generated gRPC stubs, not by our source",
}

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "proto_generated", "reports"}


def parse(path: pathlib.Path) -> dict[str, str]:
    """requirements name -> module it provides."""
    out = {}
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        name = line.split("==")[0].split(">=")[0].split("<")[0].strip()
        out[name.lower()] = DIST_TO_MODULE.get(name.lower(), name.lower().replace("-", "_"))
    return out


def declared() -> dict[str, str]:
    """Runtime requirements only. This is the file kept honest."""
    return parse(ROOT / "requirements.txt")


def declared_dev() -> dict[str, str]:
    """Tooling. Tests import pytest; that is not a runtime dependency."""
    return parse(ROOT / "requirements-dev.txt")


def imported() -> set[str]:
    """Top-level modules imported anywhere in the source."""
    mods: set[str] = set()
    for path in ROOT.rglob("*.py"):
        if SKIP_DIRS & set(path.parts):
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            print(f"!! could not parse {path.relative_to(ROOT)}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
    return mods


def main() -> int:
    decl = declared()
    imp = imported()

    local = {p.name for p in ROOT.iterdir() if p.is_dir()} | {
        p.stem for p in ROOT.glob("*.py")
    }
    stdlib = set(sys.stdlib_module_names)

    third_party = {m for m in imp if m not in stdlib and m not in local}
    provided = set(decl.values()) | set(declared_dev().values())

    undeclared = sorted(third_party - provided)
    unused = sorted(
        name for name, mod in decl.items()
        if mod not in imp and name not in ALLOWED_UNIMPORTED
    )

    for name, why in ALLOWED_UNIMPORTED.items():
        if name in decl:
            print(f"   {name}: kept on purpose, {why}")

    if undeclared:
        print("\n!! imported but not in requirements.txt:")
        for m in undeclared:
            print(f"     {m}")
    if unused:
        print("\n!! in requirements.txt but never imported:")
        for m in unused:
            print(f"     {m}")

    if undeclared or unused:
        print("\n   Add the dependency, remove it, or record it in")
        print("   ALLOWED_UNIMPORTED with a reason.")
        return 1

    print(f"\nOK: {len(decl)} declared, all imported or explained")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
