#!/bin/bash

# sudo apt install devscripts dh-python debhelper

# Doesn't work:
#debuild --no-tgz-check

# Works, I think
dpkg-buildpackage -us -uc -ui