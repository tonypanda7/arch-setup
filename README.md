# 🐧 Arch Linux System Configuration & Hardware Fixes

Personal Arch Linux configuration, hardware driver fixes (Audio & Fingerprint), and custom productivity tools for an HP Laptop running KDE Plasma.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 💻 Hardware Profile

- **Device:** HP Laptop (Device Subsystem `8bfd`)
- **CPU / Platform:** Intel Core (Raptor Lake)
- **Audio Controller:** Intel Corporation Raptor Lake-P/U/H cAVS (`sof-audio-pci-intel-tgl`)
- **Fingerprint Reader:** Elan Microelectronics Corp. ELAN:ARM-M4 (`04f3:0c00`)
- **Desktop Environment:** KDE Plasma (Wayland)
- **Shell:** Bash

---

## 📂 Repository Contents

| Directory | Description |
|---|---|
| [`audio/`](audio/) | Fix for Intel Raptor Lake audio/speakers using PipeWire, WirePlumber, and Sound Open Firmware (`sof-firmware`). |
| [`fingerprint/`](fingerprint/) | PKGBUILD and setup guide for the Elan `04f3:0c00` fingerprint scanner using community `elanmoc2` driver + `glib2-devel` fixes. |
| [`focusforge/`](focusforge/) | Terminal productivity dashboard & task guardian (zero-dependency Python + SQLite with `.bashrc` hook). |
| [`dotfiles/`](dotfiles/) | Shell configuration (`.bashrc`) and path setup. |

---

## 🚀 Quick Setup Guides

### 1. Audio Fix (Intel Raptor Lake SOF)
Modern Intel laptops need Sound Open Firmware to drive internal speakers.
```bash
cd audio
chmod +x setup-audio.sh
./setup-audio.sh
sudo reboot
```
See the [Audio README](audio/README.md) for verification and ALSA unmuting steps.

### 2. Fingerprint Reader (`04f3:0c00`)
Standard `libfprint` does not detect this sensor. This setup builds Davide Depau's patched driver:
```bash
cd fingerprint
chmod +x setup-fingerprint.sh
./setup-fingerprint.sh
fprintd-enroll
```
See the [Fingerprint README](fingerprint/README.md) for PAM login and `sudo` configuration.

### 3. FocusForge Productivity Dashboard
Displays your goals and tasks every time a terminal opens:
```bash
cd focusforge
chmod +x install.sh
./install.sh
```
See the [FocusForge README](focusforge/README.md) for usage and CLI commands.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
