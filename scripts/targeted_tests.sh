#!/bin/bash
# Targeted test runner for PostToolUse hook.
#
# Strategy:
#   - Editing a test file directly → run only that file (~0.5s)
#   - Editing a src/ file → find the matching unit test file and run it (~1-3s)
#   - No match found → run all unit tests as fallback (still <10s, no E2E)
#   - Full suite (E2E included) runs only in CI and during /run-cycle Step 6
#
# This replaces the old "pytest tests/" on every edit, which wasted time
# running 400+ tests when only one module changed.

FILE=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json, os, glob

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)

file_path = d.get('file_path', '')
project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')

if not file_path or not project_dir:
    sys.exit(0)

# Editing a test file directly — run just that file
if '/tests/' in file_path and os.path.basename(file_path).startswith('test_'):
    print(file_path)
    sys.exit(0)

# src/ Python file — find the matching unit test
if '/src/blind_assistant/' in file_path and file_path.endswith('.py'):
    basename = os.path.splitext(os.path.basename(file_path))[0]
    # Exact match: tests/unit/**/test_{basename}.py
    for match in glob.glob(f'{project_dir}/tests/unit/**/test_{basename}.py', recursive=True):
        print(match)
        sys.exit(0)
    # Prefix match: tests/unit/**/test_{basename}_*.py
    for match in glob.glob(f'{project_dir}/tests/unit/**/test_{basename}_*.py', recursive=True):
        print(match)
        sys.exit(0)
    # No exact match — fall back to all unit tests (but not E2E)
    print(f'{project_dir}/tests/unit/')
    sys.exit(0)

# Not a src/ or test file — skip
sys.exit(0)
" 2>/dev/null || echo "")

# Nothing to run
if [ -z "$FILE" ]; then
    exit 0
fi

# Run with short tracebacks so failures are readable in the hook output
cd "$CLAUDE_PROJECT_DIR" && python3 -m pytest "$FILE" --tb=short -q --no-header 2>&1 | tail -8 || true
