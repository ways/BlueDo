# Overview

BlueDo - Bluetooth proximity automation

![Logo](https://github.com/ways/BlueDo/blob/master/images/bluelock.png)

Lock your desktop, mute music or run any other command when leaving your PC. There are dozens of apps like this. This one just aims to make it beautiful, modern and easy.

# Maturity

Alpha

# Requirements

sudo apt install python-gi-dev python3-pip python3-dev libgirepository1.0-dev gcc libcairo2-dev pkg-config gir1.2-gtk-3.0 playerctl
pip3 install -r requirements.txt --user

Use these system commands:
* bluetoothctl
* amixer
* loginctl
* playerctl

# Command line options

* -e / --enable to start service on app start.
* -m / --minimize to start minimized

# Screenshots

![v3](https://github.com/ways/BlueDo/blob/master/images/v3.png)

# TODO

* Check for bluetooth, disable controls if missing
* Stop device scanning when minimized
* Minimize to systray
* Run 'here' command on exit and disable.
* Unit tests
* Preliminary icon is a mashup of two icons from Yaru. Find out license, or replace.

# Development docs

* scan for devices: bluetoothctl devices
* rssi for device: hcitool rssi ff:ff:ff:ff:ff:ff (unstable)

* hard locking: lock when no signal
* soft locking: set screensaver timeout to 1 minute when no signal

# Inspiration

* https://github.com/LukeSkywalker92/btproxipy
* https://discourse.gnome.org/t/useful-documentation-for-gtk/29
