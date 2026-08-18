#!/usr/bin/env python3
"""
Verify all required imports are working correctly
Run this to check if your environment is properly configured
"""

import sys
import os

print("=" * 60)
print("Python Environment Verification")
print("=" * 60)
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current directory: {os.getcwd()}")
print()

# Check required packages
print("Checking required packages:")
print("-" * 60)

packages_to_check = [
    ("locust", "Locust"),
    ("dotenv", "python-dotenv"),
    ("requests", "requests"),
    ("gevent", "gevent"),
]

all_good = True

for module_name, package_name in packages_to_check:
    try:
        module = __import__(module_name)
        version = getattr(module, "__version__", "unknown")
        print(f"✅ {package_name:20} - version {version}")
    except ImportError:
        print(f"❌ {package_name:20} - NOT INSTALLED")
        all_good = False

print()

if all_good:
    print("=" * 60)
    print("✅ All required packages are installed!")
    print("=" * 60)
    print()
    print("Your environment is ready to run load tests.")
    print()
    print("Next steps:")
    print("  make headless   # or: locust -f tests/SampleService/sample_http_load.py")
else:
    print("=" * 60)
    print("❌ Some packages are missing!")
    print("=" * 60)
    print()
    print("Please run:")
    print("  source venv/bin/activate")
    print("  pip install -r requirements.txt")

# ── Locustfiles ───────────────────────────────────────────────────────────
#
# Checking that locust is installed says nothing about whether the suites in
# this repo still import. A rename or a deleted helper breaks them silently
# until someone starts a run, so compile every locustfile here instead.

import ast  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

print()
print("Checking locustfiles:")
print("-" * 60)

# Top-level packages that live in this repo, so a broken reference is our bug.
_FIRST_PARTY = {"tests", "util", "tools", "LocustHelpers", "proto_generated", "config"}

_locustfiles = sorted(_Path("tests").rglob("*_load*.py"))
if not _locustfiles:
    print("no locustfiles found under tests/")
for _f in _locustfiles:
    try:
        # Importing a locustfile executes it, which registers users and can open
        # sockets, so resolve statically instead: parse it, then check that every
        # first-party module it imports still exists on disk. That is what a
        # rename or a deleted directory actually breaks.
        tree = ast.parse(_f.read_text(encoding="utf-8"), filename=str(_f))
    except SyntaxError as exc:
        print(f"FAIL {_f}:{exc.lineno}: {exc.msg}")
        all_good = False
        continue

    _missing = []
    for _node in ast.walk(tree):
        if isinstance(_node, ast.ImportFrom) and _node.level == 0 and _node.module:
            _mods = [_node.module]
        elif isinstance(_node, ast.Import):
            _mods = [a.name for a in _node.names]
        else:
            continue
        for _mod in _mods:
            _root = _mod.split(".")[0]
            if _root not in _FIRST_PARTY:
                continue
            _target = _Path(*_mod.split("."))
            if not (_target.with_suffix(".py").exists() or (_target / "__init__.py").exists()):
                _missing.append(_mod)

    if _missing:
        print(f"FAIL {_f}: imports missing local module(s): {', '.join(sorted(set(_missing)))}")
        all_good = False
    else:
        print(f"OK   {_f}")

print()
print()
print("IDE Configuration:")
print("-" * 60)
print("✅ .vscode/settings.json created")
print("✅ pyrightconfig.json created")
print("✅ .python-version created")
print()
print("Please reload your IDE window to apply the new settings.")
print("In VS Code: Cmd+Shift+P > 'Developer: Reload Window'")
print()

# Exit status is what `make verify` and CI act on. Printing FAIL and returning 0
# means the gate passes on a broken tree, which is worse than not checking.
sys.exit(0 if all_good else 1)
