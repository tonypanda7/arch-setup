#!/usr/bin/env bash
# Audio setup script for Arch Linux (Intel Raptor Lake / SOF Audio + PipeWire)
set -e

echo "=== Installing PipeWire and Sound Open Firmware (SOF) ==="
sudo pacman -S --needed pipewire pipewire-pulse pipewire-alsa wireplumber sof-firmware alsa-firmware alsa-ucm-conf

echo "=== Enabling user-level PipeWire services ==="
systemctl --user enable --now pipewire pipewire-pulse wireplumber

echo "=== Done! Please reboot your machine to load Sound Open Firmware ==="
echo "After rebooting, check status with: wpctl status"
