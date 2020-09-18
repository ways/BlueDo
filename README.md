# Overview

BlueDo - Bluetooth proximity automation

![Logo](https://github.com/ways/BlueDo/blob/master/images/bluelock.png)

Lock your desktop, mute music or run any other command when leaving your PC. There are dozens of apps like this. This one just aims to make it beautiful, modern and easy.

# Requirements

sudo apt install python-gi-dev python3-pip python3-dev libgirepository1.0-dev gcc libcairo2-dev pkg-config gir1.2-gtk-3.0
pip3 install -r requirements.txt --user

# Command line options

* -e / --enable to start service on app start.
* -m / --minimize to start minimized

# Screenshots

![v3](https://github.com/ways/BlueDo/blob/master/images/v3.png)

# TODO

* Check for bluetooth, btproxipy, disable controls if missing
* Stop name scanning when minimized
* Minimize to systray
* About
* Option to run 'here' or 'away' command on exit.

# Development docs

scan for devices: bluetoothctl devices
rssi for device: hcitool rssi ff:ff:ff:ff:ff:ff (unstable)

# Inspiration

https://github.com/LukeSkywalker92/btproxipy
https://discourse.gnome.org/t/useful-documentation-for-gtk/29
