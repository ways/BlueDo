#!/usr/bin/env python3

import sys
import os
#import appdirs
import configparser
import bluetooth
import signal
import subprocess

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Application(Gtk.Application):
    project_name = 'bluelock'
    project_version = 0.2
    config_path = ''
    bin_path = ''
    enabled = False
    debug = False
    threshold = 0
    interval = 2
    awaycound = 5
    bt_address = 'test'
    here_command = ''
    away_command = ''
    btproxipy_pid = None
    #bt_devices = Gtk.ListStore(int, str)

    window = Gtk.Window()
    btnEnabled = Gtk.Button()
    btnDebug = Gtk.Button()
    btnSave = Gtk.Button()
    cbDevice = Gtk.ComboBoxText()
    sThreshold = Gtk.Scale()
    sbInterval = Gtk.ScaleButton()
    sbCount = Gtk.ScaleButton()
    cbAway = Gtk.ComboBoxText()
    cbHere = Gtk.ComboBoxText()

    def do_activate(self):
        ''' Load config, populate UI '''

        self.load_config()

        builder = Gtk.Builder()
        builder.add_from_file("window.glade")
        #builder.connect_signals(Handler())

        self.btnEnabled = builder.get_object("btnEnabled")
        self.btnEnabled.set_active(self.enabled)
        self.btnEnabled.connect("state-set", self.on_enable_clicked)

        self.btnDebug = builder.get_object("btnDebug")
        self.btnDebug.set_active(self.debug)
        self.btnDebug.connect("state-set", self.on_debug_clicked)

        self.cbDevice = builder.get_object("cbDevice")
        self.cbDevice.append_text("%s (current)" % self.bt_address)
        self.cbDevice.set_active(0)
        for address, name in self.load_devices():
            self.cbDevice.append_text("%s (%s)" % (address, name))

        self.sThreshold = builder.get_object("sThreshold")
        self.sThreshold.set_range(-20, 0)
        self.sThreshold.set_value(self.threshold)

        self.sbInterval = builder.get_object("sbInterval")
        self.sbInterval.set_range(0, 60)
        self.sbInterval.set_value(self.interval)

        self.sbCount = builder.get_object("sbCount")
        self.sbCount.set_range(0, 20)
        self.sbCount.set_value(self.count)

        self.cbAway = builder.get_object("cbAway")
        self.cbAway.append_text("%s (current)" % self.away_command)
        self.cbAway.set_active(0)

        self.cbHere = builder.get_object("cbHere")
        self.cbHere.append_text("%s (current)" % self.here_command)
        self.cbHere.set_active(0)

        self.btnSave = builder.get_object("btnSave")
        self.btnSave.connect("activate", self.on_save_clicked)

        self.window = builder.get_object("window1")
        self.window.connect("destroy", self.on_exit_application)
        self.window.set_icon_from_file('/usr/share/icons/Adwaita/48x48/devices/computer.png')
        self.window.show_all()
        Gtk.main()

    def on_enable_clicked(self, widget, state):
        print("enable clicked! %s" % state)
        self.enabled = self.btnEnabled.get_active()
        if state:
            ''' Start service '''
            proc = subprocess.Popen(self.bin_path)
            self.btproxipy_pid = proc.pid
            proc.communicate()
        else:
            if self.btproxipy_pid:
                os.kill(self.btproxipy_pid, signal.SIGTERM)

    def on_debug_clicked(self, widget, state):
        print("debug clicked!")
        self.debug = self.btnDebug.get_active()

    def on_save_clicked(self, button):
        print("save clicked!")

    def on_exit_application(self, *args):
        Gtk.main_quit()

    def load_config(self):
        # self.config_path = appdirs.user_config_dir(self.project_name) + '.ini'
        self.config_path = '/home/larsfp/.config/btproxipy/btproxipy.ini'
        self.bin_path = ['/home/larsfp/.local/bin/btproxipy', '&']

        print ("Loading config from %s" % self.config_path)

        config = configparser.ConfigParser(interpolation=None)
        config.read(self.config_path)
        self.debug = config.get('CONFIG', 'debug')
        self.bt_address = config.get('CONFIG', 'bt_adress')
        self.threshold = config.getint('CONFIG', 'threshold')
        self.interval = config.getint('CONFIG', 'interval')
        self.count = config.getint('CONFIG', 'awaycount')
        self.away_command = config.get('CONFIG', 'away_command')
        self.here_command = config.get('CONFIG', 'here_command')

        print("threshold %s" % self.threshold)

    def load_devices(self, dryrun=True):
        ''' Load bluetooth devices '''

        nearby_devices = []

        if dryrun:
            nearby_devices = [
                ('LAPTOP-CQOJ07IS', '64:6E:69:E8:9B:22'),
                ('[TV] TV stua', '8C:79:F5:B9:C4:BF'),
                ('[TV] tv10b', '78:BD:BC:6E:C5:A3'),
            ]
        else:
            nearby_devices = bluetooth.discover_devices(lookup_names = True)

        print ("found %d devices" % len(nearby_devices))

        for name, addr in nearby_devices:
            print (" %s - %s" % (addr, name))
            yield (addr, name)

def main(version):
    app = Application()
    return app.run(sys.argv)

main(1)