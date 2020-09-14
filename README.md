# Overview

Frontend for btproxipy.

This app will read btproxipy's config file, and allow you to change values, manage service.

# Requirements

apt install python-gi-dev libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
pip3 install -r requirements.txt

# Command line options

* -e / --enable to start service on app start.
* -m / --minimize to start minimized

# Inspiration

https://github.com/LukeSkywalker92/btproxipy

# TODO

* Quiet startup parameter
* Example commands: lock screen, mute sound, play sound
* Lazy loading of bluetooth devices
* Show current rssi, connection status
* Look for renegade btproxipy procs and kill them
* About
* Option to run 'here' or 'away' command on exit.
* Consider implementing btproxipy code directly, instead of being a frontend.

links
https://discourse.gnome.org/t/useful-documentation-for-gtk/29
