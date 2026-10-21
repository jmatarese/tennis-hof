#!/usr/bin/env bash
# First-time setup on macOS, Linux or a Codespace:  bash scripts/setup.sh
# Safe to run again at any time; it only installs what is missing.
set -euo pipefail

if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Everything else lives in Python, so it is the same on every OS.
uv run hof setup
