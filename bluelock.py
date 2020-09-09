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
from gi.repository import Gtk, Gdk

class Application(Gtk.Application):
    project_name = 'bluelock'
    project_version = 0.3
    config_path = ''
    bin_path = ['/home/larsfp/.local/bin/btproxipy']
    enabled = False
    debug = False
    threshold = 0
    interval = 2
    awaycound = 5
    bt_address = 'test'
    here_command = ''
    away_command = ''
    btproxipy_pid = None
    btproxipy_proc = None
    config = None

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
    lblMessages = Gtk.Label()

    def do_activate(self):
        ''' Load config, populate UI '''

        self.load_config()

        builder = Gtk.Builder()
        builder.add_from_file("window.glade")

        self.btnEnabled = builder.get_object("btnEnabled")
        self.btnEnabled.set_active(self.enabled)
        self.btnEnabled.connect("state-set", self.on_enable_state)

        self.btnDebug = builder.get_object("btnDebug")
        self.btnDebug.set_active(self.debug)
        self.btnDebug.connect("state-set", self.on_debug_state)

        self.cbDevice = builder.get_object("cbDevice")
        self.cbDevice.append_text("%s (current)" % self.bt_address)
        self.cbDevice.set_active(0)
        for address, name in self.load_devices():
            self.cbDevice.append_text("%s (%s)" % (address, name))
        self.cbDevice.connect("changed", self.on_device_changed)

        self.sThreshold = builder.get_object("sThreshold")
        self.sThreshold.set_range(-20, 0)
        self.sThreshold.set_value(self.threshold)
        self.sThreshold.connect("value-changed", self.on_threshold_changed)

        self.sbInterval = builder.get_object("sbInterval")
        self.sbInterval.set_range(0, 60)
        self.sbInterval.set_increments(1, 1)
        self.sbInterval.set_value(self.interval)
        self.sbInterval.connect("value-changed", self.on_interval_changed)

        self.sbCount = builder.get_object("sbCount")
        self.sbCount.set_range(0, 20)
        self.sbCount.set_increments(1, 1)
        self.sbCount.set_value(self.count)
        self.sbCount.connect("value-changed", self.on_count_changed)

        self.cbAway = builder.get_object("cbAway")
        self.cbAway.append_text("%s" % self.away_command)
        self.cbAway.set_active(0)
        self.cbAway.connect("changed", self.on_away_changed)

        self.cbHere = builder.get_object("cbHere")
        self.cbHere.append_text("%s" % self.here_command)
        self.cbHere.set_active(0)
        self.cbHere.connect("changed", self.on_here_changed)

        self.btnSave = builder.get_object("btnSave")
        self.btnSave.connect("clicked", self.on_save_clicked)

        self.lblMessages = builder.get_object("lblMessages")
        #self.lblMessages.set_text('Loading bluetooth devices...')
        print(self.lblMessages.get_text())

        self.window = builder.get_object("window1")
        self.window.connect("destroy", self.on_exit_application)
        self.window.set_icon_from_file('/usr/share/icons/Yaru/256x256/apps/passwords-app.png')
        self.window.show_all()

        Gtk.main()

    def on_enable_state(self, widget, state):
        ''' When btnEnable changes state '''

        print("enable clicked! %s" % state)
        self.enabled = self.btnEnabled.get_active()
        if state:
            ''' Start service '''
            self.btproxipy_proc = subprocess.Popen(self.bin_path, close_fds=True)
            self.btproxipy_pid = self.btproxipy_proc.pid
        else:
            if self.btproxipy_pid:
                self.btproxipy_proc.terminate()
                self.btproxipy_proc.communicate()
                print("terminated. %s" % self.btproxipy_proc.returncode)

    def on_debug_state(self, widget, state):
        ''' When btnDebug changes state '''

        print("debug clicked!")
        self.debug = self.btnDebug.get_active()
        self.color_button()

    def on_save_clicked(self, button):
        ''' When btnSave is clicked '''
        self.save_config()
        self.btnSave.set_sensitive(False)
        self.lblMessages.set_text('Changes saved. Disable and enable to make active.')

    def on_exit_application(self, *args):
        self.on_enable_state(None, False) # Stop btproxipy on exit
        Gtk.main_quit()

    def on_device_changed(self, widget):
        ''' When cbDevice changes '''
        print("cbDevice changed to %s" % widget.get_active_text())
        self.bt_address = widget.get_active_text().split(' ')[0]
        self.color_button()

    def on_away_changed(self, widget):
        ''' When cbAway changes '''
        print("cbAway changed to %s" % widget.get_active_text())
        self.away_command = widget.get_active_text()
        self.color_button()

    def on_here_changed(self, widget):
        ''' When cbHere changes '''
        print("cbHere changed to %s" % widget.get_active_text())
        self.here_command = widget.get_active_text()
        self.color_button()

    def on_threshold_changed(self, widget):
        ''' When sThreshold changes '''
        print("sThreshold changed to %s" % widget.get_value())
        self.threshold = widget.get_value()
        self.color_button()

    def on_interval_changed(self, widget):
        ''' When sbInterval changes '''
        print("interval changed to %s" % widget.get_value())
        self.interval = int(widget.get_value())
        self.color_button()

    def on_count_changed(self, widget):
        ''' When sbCount changes '''
        print("count changed to %s" % widget.get_value())
        self.count = widget.get_value()
        self.color_button()

    def color_button(self):
        ''' Called any time something changes, so user can choose to save '''
        self.btnSave.set_sensitive(True)

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

        with open(self.config_path, 'w') as f:
            self.config.write(f)

    def load_config(self):
        ''' Load config '''

        config_section = 'CONFIG'
        # self.config_path = appdirs.user_config_dir(self.project_name) + '.ini'
        self.config_path = '/home/larsfp/.config/btproxipy/btproxipy.ini'

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

    def load_devices(self, dryrun=False):
        ''' Load bluetooth devices '''

        nearby_devices = []

        if dryrun:
            self.lblMessages.set_text('Loaded test devices')
            nearby_devices = [
                ('FP3', '84:cf:bf:8d:90:d4'),
                ('LAPTOP-CQOJ07IS', '64:6E:69:E8:9B:22'),
                ('[TV] TV stua', '8C:79:F5:B9:C4:BF'),
                ('[TV] tv10b', '78:BD:BC:6E:C5:A3'),
            ]
        else:
            self.lblMessages.set_text('Scanning for bluetooth devices')
            nearby_devices = bluetooth.discover_devices(lookup_names = True)
            self.lblMessages.set_text('')

        print ("found %d devices" % len(nearby_devices))

        for name, addr in nearby_devices:
            print (" %s - %s" % (addr, name))
            yield (addr, name)

def main(version):
    app = Application()
    return app.run(sys.argv)

main(1)