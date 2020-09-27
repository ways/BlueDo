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
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, Gio, GLib, GdkPixbuf, AppIndicator3

try:
    from bluedo.bt_rssi import BluetoothRSSI
except ImportError:
    from bt_rssi import BluetoothRSSI

class Application(Gtk.Application):
    project_name = 'bluedo'
    project_version = .39
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
        self.builder.add_from_file(os.path.dirname(os.path.realpath(__file__)) + "/window.glade")

        self.button_enabled = self.builder.get_object("button_enabled")
        self.combo_device = self.builder.get_object("combo_device")
        self.entry_away = self.builder.get_object("entry_away")
        self.entry_here = self.builder.get_object("entry_here")
        self.check_hereunlock = self.builder.get_object("check_hereunlock")
        self.check_hererun = self.builder.get_object("check_hererun")
        self.check_resume = self.builder.get_object("check_resume")
        self.check_unmute = self.builder.get_object("check_unmute")
        self.check_awaylock = self.builder.get_object("check_awaylock")
        self.check_awaypause = self.builder.get_object("check_awaypause")
        self.check_awaymute = self.builder.get_object("check_awaymute")
        self.check_awayrun = self.builder.get_object("check_awayrun")
        self.menuitem_advanced = self.builder.get_object("menuitem_advanced")
        self.menuitem_minimize = self.builder.get_object("menuitem_minimize")
        self.dropdown_menu = self.builder.get_object("dropdown_menu")
        self.menuitem_enable = self.builder.get_object("menuitem_enable")
        self.label_info = self.builder.get_object("label_info")

        # Load config, then populate widgets
        self.load_config()
        if self.bt_address:
            self.combo_device.append_text("%s (%s)" % (self.bt_name, self.bt_address))
            self.combo_device.set_active(0)

        if len(self.bt_address) > 0:
            self.button_enabled.set_active(self.enabled)
            self.menuitem_enable.set_active(self.enabled)
        else: 
            self.button_enabled.set_sensitive(False)
            self.menuitem_enable.set_sensitive(False)

        self.entry_away.set_text("%s" % self.away_command)
        self.entry_here.set_text("%s" % self.here_command)

        # Icon
        self.icon_path = os.path.dirname(os.path.realpath(__file__)) + "/bluedo.png"

        self.window = self.builder.get_object("main_window")
        try:
            self.window.set_icon_from_file(self.icon_path)
        except gi.repository.GLib.Error:
            print("Unable to find icon %s"  % self.icon_path)

        self.on_enable_state(self.button_enabled, self.enabled)

        # Signals
        self.builder.connect_signals(self)
        self.handler_id = self.menuitem_enable.connect("toggled", self.menuitemenable_clicked)

        self.window.show_all()

        # Check for dependencies
        try:
            subprocess.run("which playerctl > /dev/null", shell=True, check=True)
            self.check_awaypause.set_sensitive(True)
            self.check_resume.set_sensitive(True)
        except subprocess.CalledProcessError:
            self.check_awaypause.set_sensitive(False)
            self.check_awaypause.set_label("Pause music - Install playerctl to enable this option")
            self.check_resume.set_sensitive(False)
            self.check_resume.set_label("Unpause music - Install playerctl to enable this option")

        # Menu for about, advanced
        self.menuitem_advanced.set_active(self.advanced)
        self.advanced_clicked(self.menuitem_advanced)

        # Tray icon
        indicator = AppIndicator3.Indicator.new("customtray", self.icon_path, AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        indicator.set_menu(self.dropdown_menu)

        if self.minimized:
            self.menuitem_minimize.set_active(True)
            self.window.hide()

        self.start_scan()

        Gtk.main()

    def on_enable_state(self, widget, state):
        ''' When btnEnable changes state, start and stop pings'''

        if state == self.menuitem_enable.get_active():
            # Called from menu
            pass
        else:
            # Set by user or config
            with self.menuitem_enable.handler_block(self.handler_id):
                self.menuitem_enable.set_active(state)

        syslog.syslog("%s enabled %s." % (self.project_name,state))
        self.enabled = state

        if state:
            # Start service
            if len(self.bt_address) == 0:
                self.button_enabled.set_sensitive(False)
                self.menuitem_enable.set_sensitive(False)
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
        ''' When combo_device changes '''
        text = ''
        try:
            text = self.combo_device.get_active_text().strip()
        except AttributeError:
            pass

        if len(text) == 0:
            self.button_enabled.set_sensitive(False)
            self.menuitem_enable.set_sensitive(False)
        else:
            #print("combo_device changed to %s" % text)
            newaddress = text.split()[-1].replace('(', '').replace(')', '')
            newname = text.replace(newaddress, '').replace('(', '').replace(')', '')

            if newaddress != self.bt_address:
                self.bt_address = newaddress
                self.bt_name = newname
                self.button_enabled.set_sensitive(True)
                self.menuitem_enable.set_sensitive(True)
                self.save_config()

    def on_away_changed(self, widget):
        ''' When entry_away changes '''
        self.away_command = widget.get_text()
        #print("entry_away changed to %s" % self.away_command)
        self.save_config()

    def on_here_changed(self, widget):
        ''' When entry_here changes '''
        self.here_command = widget.get_text()
        #print("entry_here changed to %s" % self.here_command)
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
        self.config.set(self.config_section, 'here_unlock', str(self.check_hereunlock.get_active()))
        self.config.set(self.config_section, 'here_run', str(self.check_hererun.get_active()))
        self.config.set(self.config_section, 'away_lock', str(self.check_awaylock.get_active()))
        self.config.set(self.config_section, 'away_run', str(self.check_awayrun.get_active()))
        self.config.set(self.config_section, 'away_mute', str(self.check_awaymute.get_active()))
        self.config.set(self.config_section, 'away_pause', str(self.check_awaypause.get_active()))
        self.config.set(self.config_section, 'advanced', str(self.advanced))
        self.config.set(self.config_section, 'minimized', str(self.minimized))

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
            self.check_hereunlock.set_active(True)
        if "true" in self.config.get(self.config_section, 'here_run', fallback='false').lower():
            self.check_hererun.set_active(True)
        if "true" in self.config.get(self.config_section, 'away_lock', fallback='false').lower():
            self.check_awaylock.set_active(True)
        if "true" in self.config.get(self.config_section, 'away_mute', fallback='false').lower():
            self.check_awaymute.set_active(True)
        if "true" in self.config.get(self.config_section, 'away_pause', fallback='false').lower():
            self.check_awaypause.set_active(True)
        if "true" in self.config.get(self.config_section, 'away_run', fallback='false').lower():
            self.check_awayrun.set_active(True)
        if "true" in self.config.get(self.config_section, 'advanced', fallback='false').lower():
            self.advanced = True
        if "true" in self.config.get(self.config_section, 'minimized', fallback='false').lower():
            self.minimized = True

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
                if line == 'No default controller available\n':
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

            # Save contents of combo_device, clear and reset
            newscan = self.scan_bluetooth()

            if len(newscan) == 0:
                self.disable_all()
            else:
                self.enable_all()

            if newscan != self.nearby_devices:
                self.nearby_devices = newscan
                current = self.combo_device.get_active_text() or ''
                self.combo_device.remove_all()
                self.combo_device.append_text(current)
                self.combo_device.set_active(0)

                for address, name in newscan:
                    self.combo_device.append_text("%s (%s)" % (address, name))

            time.sleep(5)

    def disable_all(self):
        self.button_enabled.set_sensitive(False)
        self.menuitem_enable.set_sensitive(False)
        self.label_info.set_text("Bluetooth disabled")

    def enable_all(self):
        self.button_enabled.set_sensitive(True)
        self.menuitem_enable.set_sensitive(True)
        self.label_info.set_text("Device should already be paired with computer.")

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
            rssi = -99
            try:
                b = BluetoothRSSI(addr=addr)
                rssi = b.get_rssi()
                levelSignal.set_value(10+rssi)
            except (TypeError, Exception):
                levelSignal.set_value(0)

            if self.debug:
                syslog.syslog("addr: {}, rssi: {}, lost_pings {}".format(addr, rssi, lost_pings))

            if rssi is None or rssi < threshold:
                if self.debug:
                    print("L", end='')

            if self.enabled:
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

        if self.check_hereunlock.get_active():
            self.unlock()

        if self.check_hererun.get_active():
            self.run_user_command(cmd=self.entry_here.get_text())

    def away_callback(self):
        if self.debug:
            print("A", end='')

        if self.check_awaylock.get_active():
            self.lock()

        if self.check_awaymute.get_active():
            self.mute()

        if self.check_awaypause.get_active():
            self.pause_music()

        if self.check_awayrun.get_active():
            self.run_user_command(cmd=self.entry_away.get_text())

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
        dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_size(self.icon_path, 256, 256))
        dialog.connect('response', lambda dialog, data: dialog.destroy())
        dialog.show_all()

    def advanced_clicked(self, state):
        ''' Show advancd options '''

        menuitem_advanced = self.builder.get_object("menuitem_advanced")
        self.advanced = menuitem_advanced.get_active()

        check_hererun = self.builder.get_object("check_hererun")
        entry_here = self.builder.get_object("entry_here")
        check_awayrun = self.builder.get_object("check_awayrun")
        entry_away = self.builder.get_object("entry_away")

        check_hererun.set_visible(self.advanced)
        entry_here.set_visible(self.advanced)
        check_awayrun.set_visible(self.advanced)
        entry_away.set_visible(self.advanced)

        if not self.advanced:
            check_hererun.set_active(self.advanced)
            check_awayrun.set_active(self.advanced)

        self.save_config()

    def minimize_clicked(self, state):
        ''' Toggle minimize to tray '''

        self.minimized = self.menuitem_minimize.get_active()


        if self.minimized:
            self.window.hide()
        else:
            self.window.show()

        self.save_config()

    def menuitemenable_clicked(self, state):
        ''' Toggle enable '''
        self.button_enabled.set_active(not self.button_enabled.get_active())

def main(args=None):
    app = Application()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main(args=sys.argv))
