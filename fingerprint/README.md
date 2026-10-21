# ELAN 04f3:0c00 Fingerprint Reader Driver (Arch Linux)

## Hardware
- **Sensor:** `04f3:0c00 Elan Microelectronics Corp. ELAN:ARM-M4`
- **Known in:** HP laptops (e.g. Pavilion, Envy, Victus)

## Problem
Standard `libfprint` does not support USB ID `04f3:0c00`. Running `fprintd-enroll` yields:
```text
Impossible to enroll: GDBus.Error:net.reactivated.Fprint.Error.NoSuchDevice: No devices available
```

Additionally, building community drivers on modern Arch Linux fails with:
```text
Program /usr/bin/glib-mkenums found: NO
```
because Arch split `glib-mkenums` into `glib2-devel`.

## Solution

This repository includes a tested `PKGBUILD` that builds Davide Depau's `elanmoc2-working` driver with `glib2-devel` configured.

### 1. Build and Install
```bash
cd fingerprint
makepkg -si
```
*(Accept prompt to replace existing `libfprint`).*

### 2. Restart the Service
```bash
sudo systemctl restart fprintd
```

### 3. Enroll Your Fingerprint
Do **NOT** use `sudo` (or it will enroll for root instead of your user):
```bash
fprintd-enroll -f right-index-finger
```
Tap your finger repeatedly until it prints `enroll-completed`.

Verify it:
```bash
fprintd-verify
```

### 4. Enable PAM Authentication for Login & Sudo

#### For `sudo`:
Edit `/etc/pam.d/sudo`:
```text
auth      sufficient pam_fprintd.so
```
Add it as the first line of the file.

#### For Login & Lock Screen:
Edit `/etc/pam.d/system-auth`:
Add `auth sufficient pam_fprintd.so` right before `auth required pam_unix.so`.
