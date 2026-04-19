#!/usr/bin/env python3
import py_compile
import sys

files = [
    'test_lipsync_engine.py',
    'backend/activities/video_renderer.py',
    'backend/breaking.py',
]

errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"✓ {f}")
    except py_compile.PyCompileError as e:
        print(f"✗ {f}")
        errors.append(str(e))

if errors:
    print("\nErrors found:")
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print("\nAll files verified successfully!")
    sys.exit(0)
