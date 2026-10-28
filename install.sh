#!/usr/bin/env bash
# Install astro-showcase wrapper to ~/.local/bin using uv

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.local/bin"
TARGET_PATH="$TARGET_DIR/astro-showcase"

# Ensure dependencies are synced
uv sync --directory "$SCRIPT_DIR"

# Write wrapper script with absolute path to source directory
mkdir -p "$TARGET_DIR"
cat > "$TARGET_PATH" << EOF
#!/usr/bin/env bash
exec uv run --directory "$SCRIPT_DIR" python "$SCRIPT_DIR/check_astro_showcase.py" "\$@"
EOF
chmod +x "$TARGET_PATH"

echo "Installed astro-showcase to $TARGET_PATH"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "Note: ~/.local/bin is not in your PATH."
    echo "Add this to your shell config (~/.bashrc, ~/.zshrc, etc.):"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi
