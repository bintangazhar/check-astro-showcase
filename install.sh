#!/usr/bin/env bash
# Install astro-showcase to ~/.local/bin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.local/bin"
TARGET_PATH="$TARGET_DIR/astro-showcase"

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Creating $TARGET_DIR"
    mkdir -p "$TARGET_DIR"
else
    echo "$TARGET_DIR already exists"
fi

# Copy the wrapper script
cp "$SCRIPT_DIR/astro-showcase" "$TARGET_PATH"
chmod +x "$TARGET_PATH"

echo "Installed astro-showcase to $TARGET_PATH"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "Note: ~/.local/bin is not in your PATH."
    echo "Add this to your shell config (~/.bashrc, ~/.zshrc, etc.):"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
fi