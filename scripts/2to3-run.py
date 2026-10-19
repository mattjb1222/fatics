#!/usr/bin/env python3
"""Run 2to3 over FatICS source trees using lib2to3 directly.

Run from the FatICS source root. Skips itself (lib2to3 cannot parse
recent Python 3 syntax).
"""
import os
import sys
import logging
from lib2to3.refactor import RefactoringTool, get_all_fix_names

logging.basicConfig(level=logging.WARNING)

fixers = ["lib2to3.fixes.fix_%s" % n for n in get_all_fix_names("lib2to3.fixes")]
tool = RefactoringTool(
    fixers,
    options={"write_unchanged_files": False},
    explicit=["lib2to3.fixes.fix_imports"],
)

items = []
for d in ["src", "fbot", "scripts", "test"]:
    if not os.path.isdir(d):
        continue
    for dp, dn, fns in os.walk(d):
        dn[:] = [x for x in dn if not x.startswith(".")]
        for fn in sorted(fns):
            if fn.endswith(".py") and not fn.startswith("."):
                if os.path.basename(__file__) != fn:
                    items.append(os.path.join(dp, fn))

tool.refactor(items, write=True)
print("modified %d files" % len(tool.files))
for err in tool.errors:
    print("ERROR:", err, file=sys.stderr)
sys.exit(1 if tool.errors else 0)
