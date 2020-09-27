#!/usr/bin/env python3

import sys
import os
import time
import subprocess
import threading
import syslog

import bluedoapp

def run_user_command(self, cmd=''):
    ''' Run user supplied command '''
    syslog.syslog("%s running user command <%s>." % (self.project_name, cmd))
    subprocess.run(cmd, shell=True)

def mute(self):
    ''' Mute sound '''
    syslog.syslog("%s muting sound." % self.project_name)
    subprocess.run("amixer set Master mute > /dev/null", shell=True)

def unmute(self):
    ''' Unmute sound '''
    syslog.syslog("%s unmuting sound." % self.project_name)
    subprocess.run("amixer set Master unmute > /dev/null; amixer set Speaker unmute > /dev/null; amixer set Headphone unmute > /dev/null;", shell=True)

def pause_music(self):
    ''' Pause music '''
    syslog.syslog("%s pausing music." % self.project_name)
    subprocess.run("/usr/bin/playerctl pause 2> /dev/null", shell=True)

def resume_music(self):
    ''' Resume music '''
    syslog.syslog("%s resume music." % self.project_name)
    subprocess.run("/usr/bin/playerctl play 2> /dev/null", shell=True)

def unlock(self):
    ''' Unlock desktop session '''
    syslog.syslog("%s unlocked session." % self.project_name)

    # Reset soft lock. Set lock time to something reasonable
    cmd = "/usr/bin/gsettings set org.gnome.desktop.session idle-delay 600; "

    # Hard unlock.
    cmd += "/usr/bin/loginctl unlock-session $( loginctl list-sessions --no-legend| cut -f1 -d' ' ); "

    subprocess.run(cmd, shell=True)

def lock(self):
    ''' Lock desktop session '''
    syslog.syslog("%s soft-locked session." % self.project_name)

    # Hard lock. Is problematic if your phone refuse to connect
    #cmd = "/usr/bin/loginctl lock-session $( loginctl list-sessions --no-legend| cut -f1 -d' ' );"

    # Soft lock. Set a very short lock time, 10 seconds
    cmd = "/usr/bin/gsettings set org.gnome.desktop.screensaver lock-enabled true; " +\
        "/usr/bin/gsettings set org.gnome.desktop.session idle-delay 10; " +\
        "/usr/bin/gsettings set org.gnome.desktop.screensaver lock-delay 0; "

    subprocess.run(cmd, shell=True)

def main(args=None):
    app = bluedoapp.BlueDo()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main(args=sys.argv))
