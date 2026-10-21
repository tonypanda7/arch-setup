#!/usr/bin/env bash
# Setup script for ELAN 04f3:0c00 Fingerprint Reader on Arch Linux
set -e

echo "=== Installing dependencies ==="
sudo pacman -S --needed base-devel git glib2-devel fprintd

echo "=== Building and installing patched libfprint ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
makepkg -si --noconfirm

echo "=== Restarting fprintd service ==="
sudo systemctl restart fprintd

echo "=== Setup complete! ==="
echo "Now enroll your finger by running:"
echo "    fprintd-enroll"
echo "Then test with:"
echo "    fprintd-verify"
