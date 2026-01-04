# Flow Arch

Flow Arch is a custom Arch Linux ISO configuration featuring the Calamares installer and a Hyprland desktop environment.

## Overview
This project provides the configuration and scripts necessary to build a live Arch Linux ISO with a polished, pre-configured environment.

## Features
- **Base System:** Arch Linux (Pure)
- **Installer:** Calamares for easy installation
- **Desktop Environment:** Hyprland (Wayland compositor)
- **Configuration:** Includes custom dotfiles and scripts for a ready-to-use experience

## Building the ISO

### Prerequisites
To build this ISO, you need an Arch Linux system (or Arch-based derivative) with the `archiso` package installed.

```bash
sudo pacman -S archiso
```

### Build Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/flow-arch.git
   cd flow-arch
   ```

2. **Navigate to the archiso directory:**
   ```bash
   cd archiso
   ```

3. **Run the build script:**
   ```bash
   sudo ./build.sh
   ```
   *Note: The build process requires root privileges to create the filesystem and package artifacts.*

4. **Locate the ISO:**
   Once the build completes, the ISO file will be available in the `out/` directory:
   ```
   archiso/out/flow-arch-YYYY.MM.DD-x86_64.iso
   ```

## Usage
- **Live Boot:** Flash the ISO to a USB drive using a tool like Etcher or `dd`, then boot from it.
- **Testing:** You can test the ISO in a virtual machine (e.g., QEMU/KVM, VirtualBox).

## Credits
This project is built upon the foundations of the Arch Linux Calamares Installer (ALCI).