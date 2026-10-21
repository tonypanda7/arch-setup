# Audio Configuration (Intel Raptor Lake + PipeWire)

## Hardware
- **Audio Controller:** Intel Corporation Raptor Lake-P/U/H cAVS
- **Kernel Driver:** `sof-audio-pci-intel-tgl`
- **Subsystem:** Hewlett-Packard Company Device 8bfd

## Issue
On a fresh Arch Linux install, speakers or internal audio output are not detected out of the box because modern Intel chips require Sound Open Firmware (SOF) and UCM topology configurations.

## Solution

### 1. Run the setup script
```bash
chmod +x setup-audio.sh
./setup-audio.sh
```

Or install manually:
```bash
sudo pacman -S --needed pipewire pipewire-pulse pipewire-alsa wireplumber sof-firmware alsa-firmware alsa-ucm-conf
systemctl --user enable --now pipewire pipewire-pulse wireplumber
```

### 2. Reboot
Reboot your machine for the kernel to initialize Sound Open Firmware:
```bash
sudo reboot
```

### 3. Verification & Volume
```bash
# Check if sinks/speakers are listed
wpctl status

# If muted in ALSA:
alsamixer
```
