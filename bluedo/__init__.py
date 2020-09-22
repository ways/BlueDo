#!/usr/bin/env python3

import sys
import os
import time
import subprocess
import threading

import appdirs
import configparser
import syslog

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib, GdkPixbuf

try:
    from bluedo.bt_rssi import BluetoothRSSI
except ImportError:
    from bt_rssi import BluetoothRSSI

PKGDATA_DIR="." #/usr/share/no.graph.bluedo"

class Application(Gtk.Application):
    project_name = 'bluedo'
    project_version = .3
    config_path = appdirs.user_config_dir('bluedo') + '/bluedo.ini'
    config_section = 'CONFIG'

    builder = None
    enabled = False
    debug = False
    threshold = 0
    interval = 4
    away_count = 5
    advanced = False
    bt_address = ''
    bt_name = ''
    here_command = ''
    away_command = ''
    config = None
    minimized = False # Start up minimized
    nearby_devices = []
    ping_thread = None
    ping_stop = True
    scan_stop = False # Signal background device scan to shut down

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id='no.graph.bluedo',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs
        )
        self.window = None

        # Command line options https://python-gtk-3-tutorial.readthedocs.io/en/latest/application.html
        self.add_main_option(
            "enable",
            ord("e"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Enable service at start",
            None,
        )
        self.add_main_option(
            "minimize",
            ord("m"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Minimize window at start",
            None,
        )

    def do_activate(self):
        ''' Load config, populate UI '''

        # Load widgets from glade file
        self.builder = Gtk.Builder()
        self.builder.add_from_file(PKGDATA_DIR + "/window.glade")

        self.btnEnabled = self.builder.get_object("btnEnabled")
        self.cbDevice = self.builder.get_object("cbDevice")
        self.entryAway = self.builder.get_object("entryAway")
        self.entryHere = self.builder.get_object("entryHere")
        self.chkHereUnlock = self.builder.get_object("chkHereUnlock")
        self.chkHereRun = self.builder.get_object("chkHereRun")
        self.chkAwayLock = self.builder.get_object("chkAwayLock")
        self.chkAwayPause = self.builder.get_object("chkAwayPause")
        self.chkAwayMute = self.builder.get_object("chkAwayMute")
        self.chkAwayRun = self.builder.get_object("chkAwayRun")
        self.advanced_menuitem = self.builder.get_object("advanced_menuitem")

        # Load config, then populate widgets
        self.load_config()
        if self.bt_address:
            self.cbDevice.append_text("%s (%s)" % (self.bt_name, self.bt_address))
            self.cbDevice.set_active(0)

        if len(self.bt_address) > 0:
            self.btnEnabled.set_active(self.enabled)
        else: 
            self.btnEnabled.set_sensitive(False)

        self.entryAway.set_text("%s" % self.away_command)
        self.entryHere.set_text("%s" % self.here_command)

        self.window = self.builder.get_object("main_window")
        try:
            self.window.set_icon_from_file(PKGDATA_DIR + "/share/icons/hicolor/256x256/apps/bluedo.png")
        except gi.repository.GLib.Error:
            print("Unable to find icon in %s"  % PKGDATA_DIR)

        self.on_enable_state(self.btnEnabled, self.enabled)

        # Signals
        self.builder.connect_signals(self)

        self.window.show_all()

        # Menu for about, advanced
        self.advanced_menuitem.set_active(self.advanced)
        self.advanced_clicked(self.advanced_menuitem)

        # Systray
        #self.statusicon = self.builder.get_object("statusicon")
        
        if self.minimized:
            self.window.iconify()

        self.start_scan()

        Gtk.main()

    # def status_clicked(self,status):
    #     #unhide the window
    #     self.show_all()
    #     self.statusicon.set_tooltip("the window is visible")

    def on_enable_state(self, widget, state):
        ''' When btnEnable changes state, start and stop pings'''

        syslog.syslog("%s enabled %s." % (self.project_name,state))
        self.enabled = state
        if state:
            # Start service
            if len(self.bt_address) == 0:
                #self.btnEnabled.set_active(False)
                self.btnEnabled.set_sensitive(False)
            else:
                if self.ping_stop:
                    self.ping_stop = False
                    self.ping_thread = self.start_thread()

        else:
            self.ping_stop = True
            self.here_callback()

    def on_exit_application(self, *args):
        self.scan_stop = True
        self.on_enable_state(None, False) # Stop btproxipy on exit
        Gtk.main_quit()

    def on_device_changed(self, widget):
        ''' When cbDevice changes '''
        text = ''
        try:
            text = self.cbDevice.get_active_text().strip()
        except AttributeError:
            pass

        if len(text) == 0:
            self.btnEnabled.set_sensitive(False)
        else:
            #print("cbDevice changed to %s" % text)
            newaddress = text.split()[-1].replace('(', '').replace(')', '')
            newname = text.replace(newaddress, '').replace('(', '').replace(')', '')

            if newaddress != self.bt_address:
                self.bt_address = newaddress
                self.bt_name = newname
                self.btnEnabled.set_sensitive(True)
                self.save_config()

    def on_away_changed(self, widget):
        ''' When entryAway changes '''
        self.away_command = widget.get_text()
        #print("entryAway changed to %s" % self.away_command)
        self.save_config()

    def on_here_changed(self, widget):
        ''' When entryHere changes '''
        self.here_command = widget.get_text()
        #print("entryHere changed to %s" % self.here_command)
        self.save_config()

    def on_chkbutton_changed(self, widget):
        ''' When a CheckButton changes '''
        #print("CheckButton %s changed to %s" % (widget.get_name(), widget.get_active()))
        self.save_config()

    def save_config(self):
        ''' Save config '''

        if not self.config.has_section(self.config_section):
            self.config.add_section(self.config_section)

        self.config.set(self.config_section, 'debug', str(self.debug))
        self.config.set(self.config_section, 'bt_address', self.bt_address)
        self.config.set(self.config_section, 'threshold', str(self.threshold))
        self.config.set(self.config_section, 'interval', str(self.interval))
        self.config.set(self.config_section, 'away_count', str(self.away_count))
        self.config.set(self.config_section, 'away_command', self.away_command)
        self.config.set(self.config_section, 'here_command', self.here_command)

        self.config.set(self.config_section, 'bt_name', self.bt_name)
        self.config.set(self.config_section, 'here_unlock', str(self.chkHereUnlock.get_active()))
        self.config.set(self.config_section, 'here_run', str(self.chkHereRun.get_active()))
        self.config.set(self.config_section, 'away_lock', str(self.chkAwayLock.get_active()))
        self.config.set(self.config_section, 'away_run', str(self.chkAwayRun.get_active()))
        self.config.set(self.config_section, 'away_mute', str(self.chkAwayMute.get_active()))
        self.config.set(self.config_section, 'away_pause', str(self.chkAwayPause.get_active()))
        self.config.set(self.config_section, 'advanced', str(self.advanced))

        #if self.debug:
            #print("Saving config to %s" % self.config_path)
        with open(self.config_path, 'w') as f:
            self.config.write(f)

    def load_config(self):
        ''' Load config '''

        #if self.debug:
        #    print ("Loading config from %s" % self.config_path)

        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(self.config_path)

        if not os.path.isdir(os.path.dirname(self.config_path)):
            os.mkdir(os.path.dirname(self.config_path))

        if not self.config.has_section(self.config_section):
            self.config.add_section(self.config_section)

        self.debug = self.config.get(self.config_section, 'debug', fallback=False)
        self.bt_address = self.config.get(self.config_section, 'bt_address', fallback='')
        self.threshold = self.config.getint(self.config_section, 'threshold', fallback=-4)
        self.interval = self.config.getint(self.config_section, 'interval', fallback=5)
        self.away_count = self.config.getint(self.config_section, 'away_count', fallback=3)
        self.away_command = self.config.get(self.config_section, 'away_command', fallback='')
        self.here_command = self.config.get(self.config_section, 'here_command', fallback='')
        self.bt_name = self.config.get(self.config_section, 'bt_name', fallback='(current)')
        if "true" in self.config.get(self.config_section, 'here_unlock', fallback='false').lower():
            self.chkHereUnlock.set_active(True)
        if "true" in self.config.get(self.config_section, 'here_run', fallback='false').lower():
            self.chkHereRun.set_active(True)
        if "true" in self.config.get(self.config_section, 'away_lock', fallback='false').lower():
            self.chkAwayLock.set_active(True)
        if "true" in self.config.get(self.config_section, 'away_mute', fallback='false').lower():
            self.chkAwayMute.set_active(True)
        if "true" in self.config.get(self.config_section, 'away_pause', fallback='false').lower():
            self.chkAwayPause.set_active(True)
        if "true" in self.config.get(self.config_section, 'away_run', fallback='false').lower():
            self.chkAwayRun.set_active(True)
        if "true" in self.config.get(self.config_section, 'advanced', fallback='false').lower():
            self.advanced = True

    def scan_bluetooth(self, dryrun=False):
        ''' Load bluetooth devices '''

        cmd = ['/usr/bin/bluetoothctl', 'devices']
        devices = []

        if dryrun:
            self.devices = [
                ('FP3', '84:cf:bf:8d:90:d4'),
                ('[TV] TV stua', '8C:79:F5:B9:C4:BF'),
                ('[TV] tv10b', '78:BD:BC:6E:C5:A3'),
            ]
        else:
            proc = subprocess.Popen(
                args=cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            for line in iter(proc.stdout.readline, b''):
                if line.strip() == '': # iter calls until output is ''
                    break
                addr = line.split()[1]
                name = ' '.join(line.split()[2:])
                devices += [(name, addr)]

            proc.communicate() # Allow cmd to exit cleanly
        return devices

    def start_scan(self):
        t = threading.Thread(target = self.background_scan) 
        t.start()

    def background_scan(self):
        while True:
            if self.scan_stop:
                break

            # Save contents of cbdevice, clear and reset
            newscan = self.scan_bluetooth()
            if newscan != self.nearby_devices:
                self.nearby_devices = newscan
                current = self.cbDevice.get_active_text() or ''
                self.cbDevice.remove_all()
                self.cbDevice.append_text(current)
                self.cbDevice.set_active(0)

                for address, name in newscan:
                    self.cbDevice.append_text("%s (%s)" % (address, name))

            time.sleep(5)

    def disable_all(self):
        self.btnEnabled.set_sensitive(False)

    def do_command_line(self, command_line):
        ''' Parse app startup commandline arguments '''

        options = command_line.get_options_dict()
        options = options.end().unpack()

        if "enable" in options:
            self.enabled = True
        if "minimize" in options:
            self.minimized = True

        self.activate()
        return 0

    def start_thread(self):
        thread = threading.Thread(
            target=self.bluetooth_listen,
            args=(),
            kwargs={
                'addr': self.bt_address,
                'threshold': self.threshold,
                'here_callback': self.here_callback,
                'away_callback': self.away_callback
            }
        )
        
        thread.daemon = True # Daemonize
        thread.start() # Start the thread
        return thread

    def bluetooth_listen(self, addr, threshold, here_callback, away_callback):
        ''' Ping selected bluetooth device. Perform actions based on RSSI. '''

        levelSignal = self.builder.get_object("levelSignal")
        lost_pings = 0

        while not self.ping_stop:
            b = BluetoothRSSI(addr=addr)
            rssi = b.get_rssi()
            try:
                levelSignal.set_value(10+rssi)
            except TypeError:
                levelSignal.set_value(0)
                rssi = -99

            if self.debug:
                syslog.syslog("addr: {}, rssi: {}, lost_pings {}".format(addr, rssi, lost_pings))

            if rssi is None or rssi < threshold:
                if self.debug:
                    print("L", end='')

                lost_pings += 1
                if lost_pings == self.away_count:
                    #lost_pings = 0
                    away_callback()
            elif lost_pings > 0:
                lost_pings = 0
                here_callback()
            else:
                if self.debug:
                    print("P", end='')

            time.sleep(self.interval)

    def here_callback(self):
        if self.debug:
            print("H", end='')

        if self.chkHereUnlock.get_active():
            self.unlock()

        if self.chkHereRun.get_active():
            self.run_user_command(cmd=self.entryHere.get_text())

    def away_callback(self):
        if self.debug:
            print("A", end='')

        if self.chkAwayLock.get_active():
            self.lock()

        if self.chkAwayMute.get_active():
            self.mute()

        if self.chkAwayPause.get_active():
            self.pause_music()

        if self.chkAwayRun.get_active():
            self.run_user_command(cmd=self.entryAway.get_text())

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

    def run_user_command(self, cmd=''):
        ''' Run user supplied command '''
        syslog.syslog("%s running user command <%s>." % (self.project_name, cmd))
        subprocess.run(cmd, shell=True)

    def mute(self):
        ''' Mute sound '''
        syslog.syslog("%s muting sound." % self.project_name)
        subprocess.run("amixer set Master mute > /dev/null", shell=True)

        # unmute: amixer set Master unmute; amixer set Speaker unmute; amixer set Headphone unmute

    def pause_music(self):
        ''' Pause music '''
        syslog.syslog("%s pausing music." % self.project_name)
        subprocess.run("/usr/bin/playerctl pause 2> /dev/null", shell=True)

    def about_clicked(self, widget):
        ''' Show about dialog '''

        dialog = Gtk.AboutDialog()
        dialog.set_title("About")
        dialog.set_name(self.project_name)
        dialog.set_version(str(self.project_version))
        dialog.set_comments("Bluetooth proximity automation")
        dialog.set_website("https://github.com/ways/BlueDo")
        dialog.set_authors(["Lars Falk-Petersen"])
        dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_size("share/icons/hicolor/256x256/apps/bluedo.png", 256, 256))
        dialog.connect('response', lambda dialog, data: dialog.destroy())
        dialog.show_all()

    def advanced_clicked(self, state):
        ''' Show advancd options '''

        advanced_menuitem = self.builder.get_object("advanced_menuitem")
        self.advanced = advanced_menuitem.get_active()

        chkHereRun = self.builder.get_object("chkHereRun")
        entryHere = self.builder.get_object("entryHere")
        chkAwayRun = self.builder.get_object("chkAwayRun")
        entryAway = self.builder.get_object("entryAway")

        chkHereRun.set_visible(self.advanced)
        entryHere.set_visible(self.advanced)
        chkAwayRun.set_visible(self.advanced)
        entryAway.set_visible(self.advanced)

        if not self.advanced:
            chkHereRun.set_active(self.advanced)
            chkAwayRun.set_active(self.advanced)

        self.save_config()


def main(args=None):
    app = Application()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main(args=sys.argv))
