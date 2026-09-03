#!/usr/bin/env python3
"""Import everything the suite needs, using only requirements.txt.

    python tools/check_runtime_imports.py

Run this against an environment built from requirements.txt alone. It fails if
any module the suite imports is missing, which is how `flask` would have been
caught: it was imported by util/locust_metrics.py and declared nowhere, and it
resolved only because Locust installs Flask for its own web UI.

Two details about the exit, both deliberate.

Importing locust pulls in gevent, which monkey-patches threading. When a short
script like this one then exits, gevent's greenlet teardown races CPython's
interpreter finalisation and prints

    RuntimeError: greenlet is being finalized

to stderr, after the script body has finished. The process still exits 0, so a
CI step passes, but anything this script printed can be lost in that teardown.
A check whose output disappears is not a check. So results are flushed
explicitly and the process leaves through os._exit, which skips finalisation
entirely.
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys

# Run from anywhere: the suite's own packages live at the repository root.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Third-party modules the suite imports directly, and the file that imports
# each one, so a failure names the reason the dependency exists.
RUNTIME = [
    ("locust", "tests/*/*_load.py, util/grpc_helper.py"),
    ("flask", "util/locust_metrics.py"),
    ("grpc", "util/grpc_helper.py"),
    ("prometheus_client", "util/locust_metrics.py, util/prometheus_metrics.py"),
    ("dotenv", "LocustHelpers/command_line_parser.py"),
]

# Our own modules, imported last so that a missing third-party dependency is
# reported as itself rather than as an import error inside one of these.
LOCAL = [
    "util.data_loader",
    "util.grpc_helper",
    "util.locust_metrics",
    "util.prometheus_metrics",
    "LocustHelpers.command_line_parser",
]


def main() -> int:
    failures = []

    for name, used_by in RUNTIME:
        try:
            importlib.import_module(name)
        except ImportError as exc:
            failures.append(f"{name:20} needed by {used_by}\n{'':22} {exc}")
        else:
            print(f"  ok  {name:20} {used_by}")

    local_failures = []
    for name in LOCAL:
        try:
            importlib.import_module(name)
        except ImportError as exc:
            local_failures.append(f"{name:36} {exc}")
        else:
            print(f"  ok  {name}")

    if failures or local_failures:
        if failures:
            print("\n!! third-party imports failed against requirements.txt alone:")
            for f in failures:
                print(f"     {f}")
            print("\n   Add the dependency to requirements.txt. Do not rely on it")
            print("   arriving as somebody else's transitive install.")
        if local_failures:
            print("\n!! modules in this repository failed to import:")
            for f in local_failures:
                print(f"     {f}")
        rc = 1
    else:
        print(f"\nOK: {len(RUNTIME)} runtime and {len(LOCAL)} local modules imported")
        rc = 0

    # Flush before leaving, because os._exit does not.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)


if __name__ == "__main__":
    main()
