#!/usr/bin/env python3

import sys
import appdirs
import configparser
import bluetooth

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Application(Gtk.Application):
    project_name = 'btproxipy'
    config_path = None
    enabled = True
    debug = False
    threshold = 0
    interval = 2
    awaycound = 5
    bt_address = 'test'
    here_command = ''
    away_command = ''
    #bt_devices = Gtk.ListStore(int, str)

    window = Gtk.Window()
    btnEnabled = Gtk.Button()
    btnDebug = Gtk.Button()
    btnSave = Gtk.Button()
    cbDevice = Gtk.ComboBoxText()
    sThreshold = Gtk.Scale()

    def do_activate(self):
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

        self.btnSave = builder.get_object("btnSave")
        self.btnSave.connect("activate", self.on_save_clicked)

        self.window = builder.get_object("window1")
        self.window.connect("destroy", self.on_exit_application)
        self.window.set_icon_from_file('/usr/share/icons/Adwaita/48x48/devices/computer.png')
        self.window.show_all()
        Gtk.main()

    def on_enable_clicked(self, widget, state):
        print("enable clicked!")
        self.enabled = self.btnEnabled.get_active()

    def on_debug_clicked(self, widget, state):
        print("debug clicked!")
        self.debug = self.btnDebug.get_active()

    def on_save_clicked(self, button):
        print("save clicked!")

    def on_exit_application(self, *args):
        Gtk.main_quit()

    def load_config(self):
        # self.config_path = appdirs.user_config_dir(self.project_name) + '.ini'
        self.config_path = '/home/larsfp/.config/' + self.project_name + '/' + self.project_name + '.ini'

        print ("Loading config from %s" % self.config_path)

        config = configparser.ConfigParser(interpolation=None)
        config.read(self.config_path)
        self.debug = config.get('CONFIG', 'debug')
        self.bt_address = config.get('CONFIG', 'bt_adress')
        self.threshold = config.getint('CONFIG', 'threshold')

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