#!/bin/sh
# Install/refresh the app environment with uv. The interpreter is kept in ./.python
# (not ~/.local/share/uv) because the service runs with ProtectHome=tmpfs.
# Usage: ./sync.sh            (add packages with: ./sync.sh add <pkg>, upgrade: ./sync.sh lock --upgrade)
set -e
cd "$(dirname "$0")"
export UV_PYTHON_INSTALL_DIR="$PWD/.python"
export UV_PYTHON_PREFERENCE=only-managed   # never the distro Python (an upgrade can break it)
UV="${UV:-$(command -v uv || echo "$HOME/.local/bin/uv")}"
if [ $# -eq 0 ]; then
    "$UV" sync --locked || "$UV" sync
else
    "$UV" "$@" && "$UV" sync
fi
