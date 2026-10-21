#!/usr/bin/env bash
# FocusForge installer
set -e

INSTALL_DIR="$HOME/.local/share/focusforge"
BIN_DIR="$HOME/.local/bin"

echo "=== Installing FocusForge ==="
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/focusforge.py" "$INSTALL_DIR/focusforge.py"
chmod +x "$INSTALL_DIR/focusforge.py"

# Create symlink/wrapper
cat << 'EOF' > "$BIN_DIR/focusforge"
#!/bin/sh
exec python3 "$HOME/.local/share/focusforge/focusforge.py" "$@"
EOF
chmod +x "$BIN_DIR/focusforge"

echo "FocusForge installed to $BIN_DIR/focusforge"

# Hook into .bashrc if not already present
if ! grep -q "focusforge" "$HOME/.bashrc" 2>/dev/null; then
    echo "" >> "$HOME/.bashrc"
    echo "# FocusForge terminal greeting" >> "$HOME/.bashrc"
    echo "if command -v focusforge &>/dev/null; then focusforge; fi" >> "$HOME/.bashrc"
    echo "Added greeting hook to ~/.bashrc"
fi

echo "=== Installation complete! Try running: focusforge ==="
