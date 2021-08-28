# Overview

BlueDo - Bluetooth proximity automation

![Logo](https://raw.githubusercontent.com/ways/BlueDo/master/images/bluedo.png)

Lock your desktop, mute music or run any other command when leaving your PC. There are dozens of apps like this. This one just aims to make it beautiful, modern and easy.

# Maturity

Beta

# Installation

## From pip

    sudo apt install python3-pip libbluetooth-dev libappindicator3-dev playerctl
    pip3 install --upgrade bluedo

# Requirements

Needs bluetoothctl ~5.50 or newer.

Use these system commands:

* bluetoothctl
* loginctl
* gsettings
* amixer
* playerctl

Only tested on Ubuntu 20.04-21.04 with GNOME.

# Command line options

* -e / --enable to start service on app start.
* -m / --minimize to start minimized

# Configuration

There are lots more options in the config file. Feel free to tune.

# Screenshots

![v53](https://raw.githubusercontent.com/ways/BlueDo/master/images/v53.png)
![v49](https://raw.githubusercontent.com/ways/BlueDo/master/images/v49.png)
![v49_advanced](https://raw.githubusercontent.com/ways/BlueDo/master/images/v49_advanced.png)
![v3_2](https://raw.githubusercontent.com/ways/BlueDo/master/images/v3_2.png)
![v3](https://raw.githubusercontent.com/ways/BlueDo/master/images/v3.png)

# System changes

Note that this app will make these changes to your power management:

* Enable screen lock: ```org.gnome.desktop.screensaver lock-enabled true```
* Set delay from screen blacking to locking to zero: ```org.gnome.desktop.screensaver lock-delay 0```
* Set screen saver timeout to 10 seconds when device is away, 5 minutes when device is present: ```org.gnome.desktop.session idle-delay 600```

# TODO

* Default lock / unlock ON.
* Keep two instances from running at the same time.
* Minimize to tray, instead of having both minimize and minimize to tray.
* Stop device scanning when minimized
* Change to dynamic widget layout instead of fixed.
* Change preferences button to proper burger menu.
* Move media files to some other dir?
* Unit tests

# Development docs

* scan for devices: bluetoothctl devices
* rssi for device: hcitool rssi ff:ff:ff:ff:ff:ff (unstable)
* Version below .56 needs Python < 3.9

* hard locking: lock when no signal
* soft locking: set screensaver timeout to 10 seconds when no signal

# Inspiration

* https://github.com/LukeSkywalker92/btproxipy
  * bt_rssi.py is from this project and is MIT licensed.
* https://discourse.gnome.org/t/useful-documentation-for-gtk/29
* Black/white icons in app from https://material.io
