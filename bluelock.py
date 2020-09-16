#!/usr/bin/env python3

import sys
import os
import time
import signal
import subprocess
from threading import Thread

import appdirs
import configparser
import bluetooth

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib

class Application(Gtk.Application):
    project_name = 'blocker'
    project_version = 1.1
    config_path = ''
    bin_path = ['/home/larsfp/.local/bin/btproxipy']

    builder = None
    enabled = False
    debug = False
    threshold = 0
    interval = 2
    awaycound = 5
    bt_address = ''
    here_command = ''
    away_command = ''
    btproxipy_pid = None
    btproxipy_proc = None
    config = None
    shutdown = False # Signal background processes to shut down
    minimized = False # Start up minimized

    # GUI
    window = Gtk.Window()
    btnEnabled = Gtk.Button()
    liststoreDevices = Gtk.ListStore()
    cbDevice = Gtk.ComboBox()
    entryAway = Gtk.Entry()
    entryHere = Gtk.Entry()
    spinnerScanning = Gtk.Spinner()
    chkHereUnlock = Gtk.CheckButton()
    chkHereRun = Gtk.CheckButton()
    chkAwayLock = Gtk.CheckButton()
    chkAwayRun = Gtk.CheckButton()
    chkAwayMute = Gtk.CheckButton()
    chkAwayPause = Gtk.CheckButton()

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id='no.graph.blocker',
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
        self.builder.add_from_file("window.glade")

        self.btnEnabled = self.builder.get_object("btnEnabled")
        #self.btnEnabled.set_active(self.enabled)

        self.cbDevice = self.builder.get_object("cbDevice")
        self.entryAway = self.builder.get_object("entryAway")
        self.entryHere = self.builder.get_object("entryHere")
        self.spinnerScanning = self.builder.get_object("spinnerScanning")
        self.chkHereUnlock = self.builder.get_object("chkHereUnlock")
        self.chkHereRun = self.builder.get_object("chkHereRun")
        self.chkAwayLock = self.builder.get_object("chkAwayLock")
        self.chkAwayPause = self.builder.get_object("chkAwayPause")
        self.chkAwayMute = self.builder.get_object("chkAwayMute")
        self.chkAwayRun = self.builder.get_object("chkAwayRun")

        # Load config, then populate widgets
        self.load_config()
        if self.bt_address:
            self.cbDevice.append_text(self.bt_address)
            self.cbDevice.set_active(0)
        self.entryAway.set_text("%s" % self.away_command)
        self.entryHere.set_text("%s" % self.here_command)
        # liststoreDevices = self.cbDevice.get_model()
        # print(liststoreDevices.get_column_type(0))
        # for row in liststoreDevices:
        #     print(row)
        #     for c in row:
        #         print (c)
        #         if 'current' in c:
        #             break

        self.window = self.builder.get_object("window1")
        #self.window.set_icon_from_file('./images/bluelock.png')

        self.on_enable_state(self.btnEnabled, self.enabled)

        # Signals
        self.builder.connect_signals(self)

        self.window.show_all()

        if self.minimized:
            self.window.iconify()

        self.spinnerScanning.start()
        self.start_scan()

        Gtk.main()

    def on_enable_state(self, widget, state):
        ''' When btnEnable changes state '''

        print("Enable changed to <%s>" % state)
        self.enabled = state
        if state:
            ''' Start service '''
            if len(self.bt_address) == 0:
                #self.btnEnabled.set_active(False)
                self.btnEnabled.set_sensitive(False)
            else:
                self.btproxipy_proc = subprocess.Popen(self.bin_path, close_fds=True)
                self.btproxipy_pid = self.btproxipy_proc.pid
        else:
            if self.btproxipy_pid:
                self.btproxipy_proc.terminate()
                self.btproxipy_proc.communicate()
                print("terminated. %s" % self.btproxipy_proc.returncode)

    def on_exit_application(self, *args):
        self.shutdown = True
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
            print("cbDevice changed to %s" % text)
            self.bt_address = text.split()[-1].replace('(', '').replace(')', '')
            self.btnEnabled.set_sensitive(True)
            self.save_config()

    def on_away_changed(self, widget):
        ''' When entryAway changes '''
        self.away_command = widget.get_text()
        print("entryAway changed to %s" % self.away_command)
        self.save_config()

    def on_here_changed(self, widget):
        ''' When entryHere changes '''
        self.here_command = widget.get_text()
        print("entryHere changed to %s" % self.here_command)
        self.save_config()

    def on_chkbutton_changed(self, widget):
        ''' When a CheckButton changes '''
        print("CheckButton %s changed to %s" % (widget.get_name(), widget.get_active()))
        self.save_config()

    def save_config(self):
        ''' Save config '''

        config_section = 'CONFIG'
        #self.config.add_section(config_section)
        self.config.set(config_section, 'debug', self.debug)
        self.config.set(config_section, 'bt_adress', self.bt_address)
        self.config.set(config_section, 'threshold', str(self.threshold))
        self.config.set(config_section, 'interval', str(self.interval))
        self.config.set(config_section, 'awaycount', str(self.count))
        self.config.set(config_section, 'away_command', self.away_command)
        self.config.set(config_section, 'here_command', self.here_command)

        self.config.set(config_section, 'here_unlock', str(self.chkHereUnlock.get_active()))
        self.config.set(config_section, 'here_run', str(self.chkHereRun.get_active()))
        self.config.set(config_section, 'away_lock', str(self.chkAwayLock.get_active()))
        self.config.set(config_section, 'away_run', str(self.chkAwayRun.get_active()))
        self.config.set(config_section, 'away_mute', str(self.chkAwayMute.get_active()))
        self.config.set(config_section, 'away_pause', str(self.chkAwayPause.get_active()))

        print("Saving config to %s" % self.config_path)
        with open(self.config_path, 'w') as f:
            self.config.write(f)

    def load_config(self):
        ''' Load config '''

        config_section = 'CONFIG'
        self.config_path = appdirs.user_config_dir('btproxipy') + '/btproxipy.ini'
        print ("Loading config from %s" % self.config_path)

        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(self.config_path)
        self.debug = self.config.get(config_section, 'debug')
        self.bt_address = self.config.get(config_section, 'bt_adress')
        self.threshold = self.config.getint(config_section, 'threshold')
        self.interval = self.config.getint(config_section, 'interval')
        self.count = self.config.getint(config_section, 'awaycount')
        self.away_command = self.config.get(config_section, 'away_command')
        self.here_command = self.config.get(config_section, 'here_command')
        try:
            if "true" in self.config.get(config_section, 'here_unlock').lower():
                self.chkHereUnlock.set_active(True)
        except configparser.NoOptionError:
            pass
        try:
            if "true" in self.config.get(config_section, 'here_run').lower():
                self.chkHereRun.set_active(True)
        except configparser.NoOptionError:
            pass
        try:
            if "true" in self.config.get(config_section, 'away_lock').lower():
                self.chkAwayLock.set_active(True)
        except configparser.NoOptionError:
            pass
        try:
            if "true" in self.config.get(config_section, 'away_mute').lower():
                self.chkAwayMute.set_active(True)
        except configparser.NoOptionError:
            pass
        try:
            if "true" in self.config.get(config_section, 'away_pause').lower():
                self.chkAwayPause.set_active(True)
        except configparser.NoOptionError:
            pass
        try:
            if "true" in self.config.get(config_section, 'away_run').lower():
                self.chkAwayRun.set_active(True)
        except configparser.NoOptionError:
            pass

    def load_devices(self, dryrun=False):
        ''' Load bluetooth devices '''

        nearby_devices = []

        if dryrun:
            nearby_devices = [
                ('FP3', '84:cf:bf:8d:90:d4'),
                ('LAPTOP-CQOJ07IS', '64:6E:69:E8:9B:22'),
                ('[TV] TV stua', '8C:79:F5:B9:C4:BF'),
                ('[TV] tv10b', '78:BD:BC:6E:C5:A3'),
            ]
        else:
            #self.lblMessages.set_text('Scanning for bluetooth devices')
            try:
                nearby_devices = bluetooth.discover_devices(lookup_names = True)
            except bluetooth.BluetoothError as err:
                print ("bluetoothError %s" % err)
                return None
            except OSError as err:
                print ("oserror %s" % err)
                self.disable_all()
                print('Error: bluetooth off?')
                return None

        for name, addr in nearby_devices:
            print ("* %s - %s" % (addr, name))
            yield (addr, name)

    def start_scan(self):
        t = Thread(target = self.background_scan) 
        t.start()

    def background_scan(self):
        while True:
            if self.shutdown:
                break

            print("Scanning for devices")
            self.spinnerScanning.start()

            # Save contents of cbdevice, clear and reset

            # liststoreDevices = self.cbDevice.get_model()
            # for row in liststoreDevices:
            #     print(row)
                # for c in row:
                #     print (c)
                #     if 'current' in c:
                #         break

            current = self.cbDevice.get_active_text() or ''
            self.cbDevice.remove_all()
            self.cbDevice.append_text(current)
            self.cbDevice.set_active(0)

            for address, name in self.load_devices():
                self.cbDevice.append_text("%s (%s)" % (address, name))
            self.spinnerScanning.stop()
            time.sleep(10)

    def disable_all(self):
        self.btnEnabled.set_sensitive(False)

    def do_command_line(self, command_line):
        ''' Commandline options '''

        options = command_line.get_options_dict()
        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if "enable" in options:
            print("Enable argument recieved: %s" % options["enable"])
            self.enabled = True
        if "minimize" in options:
            print("minimize argument recieved: %s" % options["minimize"])
            self.minimized = True

        self.activate()
        return 0

def main(args):
    app = Application()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main(sys.argv))