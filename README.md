# Overview

BlueDo - Bluetooth proximity automation

![Logo](https://raw.githubusercontent.com/ways/BlueDo/master/share/icons/hicolor/256x256/apps/bluedo.png)

Lock your desktop, mute music or run any other command when leaving your PC. There are dozens of apps like this. This one just aims to make it beautiful, modern and easy.

# Maturity

Beta

# Installation

## From pip

    sudo apt install python3-pip libbluetooth-dev libappindicator3-dev playerctl
    pip3 install --upgrade bluedo

# Requirements

* sudo apt install python3-pip libbluetooth-dev playerctl
* pip3 install --user bluedo

Use these system commands:

* bluetoothctl
* loginctl
* gsettings
* amixer
* playerctl

Only tested on Ubuntu 20.04 with GNOME.

# Command line options

* -e / --enable to start service on app start.
* -m / --minimize to start minimized

# Screenshots

![v3_2](https://raw.githubusercontent.com/ways/BlueDo/master/images/v3_2.png)
![v3](https://raw.githubusercontent.com/ways/BlueDo/master/images/v3.png)

# System changes

Note that this app will make these changes to your power management:

* Enable screen lock: ```org.gnome.desktop.screensaver lock-enabled true```
* Set delay from screen blacking to locking to zero: ```org.gnome.desktop.screensaver lock-delay 0```
* Set screen saver timeout to 10 seconds when device is away, 5 minutes when device is present: ```org.gnome.desktop.session idle-delay 600```

# TODO

* Stop device scanning when minimized
* "Open bluetooth settings"
* Resume playback on "here"
* Unmute on "here"
* Figure out what freezes app sometimes. Only happends when run from codium.
* Unit tests

## For snap
* See if build config can be cut down
* Theming doesn't work right (looks ugly)
* Attempt to confine

# Development docs

* scan for devices: bluetoothctl devices
* rssi for device: hcitool rssi ff:ff:ff:ff:ff:ff (unstable)

* hard locking: lock when no signal
* soft locking: set screensaver timeout to 10 seconds when no signal

* build deb package: debuild -us -uc

# Inspiration

* https://github.com/LukeSkywalker92/btproxipy
  * bt_rssi.py is from this project and is MIT licensed.
* https://discourse.gnome.org/t/useful-documentation-for-gtk/29
