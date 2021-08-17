# ----------------------------------------Importing Modules-------------------------------------------------------------
import ctypes
import sys
import requests                                                                 # pip install requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup  # pip install bs4
import xml.etree.ElementTree as ElementTree
import time
import win32gui                                                                 # pip install win32gui
import win32con                                                                 # used to maximize minimize window
import win32process
import win32api
import subprocess as sp
from os import remove, environ, chdir, scandir, makedirs, mkdir
from os.path import exists, isdir, isfile, join, splitext, dirname, realpath
from psutil import pid_exists, process_iter, Process                            # pip install psutil
from shutil import rmtree, move
from datetime import datetime as dt
from pymsgbox import alert, confirm                                             # pip install pymsgbox
from playsound import playsound                                                 # pip install playsound


# ----------------------------------------Main Function-----------------------------------------------------------------
def main():
    es_dir, emuls_root, roms_root, settings_cfg_file, startup_dir, intro_file, splashs_root, vlcargs, es_args,\
        kill_exp, random_theme, ex_fullscreen, assync_load, play_vlc_embedded, play, hide_es_while_assync_load,\
        boot_videos, resolution, current_process_hwnds = check_ini_and_args()
    if not isdir(es_dir) or es_dir == '':
        environ['ESdir'] = es_dir = new_getcwd()
    check_7zip(es_dir)
    es_path = check_es_files(join(es_dir, 'emulationstation.exe'))
    es_maindir = check_es_maindir(join(es_dir, '.emulationstation'))
    emuls_root = set_emuls_root(emuls_root)  # If in the same partition volume, relative paths can be used
    roms_root = set_roms_root(roms_root)     #
    settings_cfg_file = es_cfg_files(es_maindir, emuls_root, roms_root)
    themes_root = check_themes_setup(join(es_maindir, 'themes'), settings_cfg_file)
    if kill_exp:
        terminate_process('explorer.exe;emulationstation.exe;vlc.exe')
    else:
        terminate_process('emulationstation.exe;vlc.exe')
    if random_theme:
        randomize_themes(themes_root, settings_cfg_file)
    setdisplaysolution(resolution)
    if not play:
        emustation = NewPopen(es_path + es_args)
        emustation.bring_window_on_top()
        if kill_exp:
            emustation.wait()
            sp.call('explorer.exe')
    else:
        intro_file = join(es_dir, 'intro.mp4')
        startup_dir = join(es_dir, 'startup_videos')
        splashs_dir = check_splashs_setup(join(es_dir, 'splashs'))
        vlc_path = check_vlc_setup(join(es_dir, 'vlc\\vlc.exe'))
        if not ex_fullscreen:
            if '--windowed' not in es_args: es_args += ' --windowed'
            if '--fullscreen-borderless' not in es_args: es_args += ' --fullscreen-borderless'
        if play_vlc_embedded:  # Loads ES in background while playing video in foreground
            if '--no-splash' not in es_args: es_args += ' --no-splash'
            emustation = NewPopen(es_path + es_args)
            emustation.setmute(True)
            vlc_playing = startup_videos(vlc_path, intro_file, startup_dir, splashs_dir, boot_videos,
                                         play_vlc_embedded, emustation.get_first_hwnd_from_pid())
            while pid_exists(vlc_playing.pid):  # checks if emulationstation is still alive (not prematurally killed)
                if pid_exists(emustation.pid):
                    time.sleep(0.005)
                else:
                    vlc_playing.terminate()
                    raise SystemExit
            emustation.bring_window_on_top()
            emustation.setmute(False)
            play_menu_sound('menu.wav')
            if kill_exp:  # RESTARTS EXPLORER PROCESS
                emustation.wait()
                sp.call('explorer.exe')
        elif assync_load:
            # new_startupinfo() function sets startupinfo to hide ES if hide_es_while_assync_load is set true
            vlcplaying = startup_videos(vlc_path, intro_file, startup_dir, splashs_dir, boot_videos)
            emustation = NewPopen(es_path + es_args, startupinfo=new_startupinfo(hide_es_while_assync_load))
            emustation.setmute(True)
            vlcplaying.bring_window_on_top(once=False)
            emustation.setmute(False)
            emustation.unhide_window()  # only usefull if it starts with hidden window
            emustation.bring_window_on_top()  # Bring on top with focus on
            play_menu_sound('menu.wav')
            if kill_exp:  # RESTARTS EXPLORER PROCESS
                emustation.wait()
                sp.call('explorer.exe')
        else:
            startup_videos(vlc_path, intro_file, startup_dir, splashs_dir, boot_videos).bring_window_on_top(once=False)
            emustation = NewPopen(es_path + es_args)
            emustation.bring_window_on_top()
            play_menu_sound('menu.wav')
            if kill_exp:
                emustation.wait()
                sp.call('explorer.exe')


# ----------------------------------------------------------------------------------------------------------------------
def terminate_process(names=''):
    def getpid(process_name):
        return [proc.pid for proc in process_iter() if proc.name() == process_name]

    names_list = [name.strip().lower() for name in names.split(';')]
    for p in process_iter():
        for name in names_list:
            if p.name() == name:
                pids = getpid(name)
                if len(pids) > 0:
                    for pid in pids:
                        Process(int(pid)).terminate()


def check_ini_and_args():
    es_dir = emuls_root = roms_root = settings_cfg_file = ''
    startup_dir = intro_file = splashs_root = vlcargs = es_args = ''
    kill_exp = random_theme = ex_fullscreen = assync_load = play_vlc_embedded = False
    play = hide_es_while_assync_load = boot_videos = True
    resolution = []
    current_process_hwnds = []
    global silent

    def check_entry_es_ini(value_in, ini_entry):
        if isdir(value_in):
            return value_in
        else:
            alert(f'es_launcher.ini {ini_entry} entry value has a invalid directory path:\n{value_in}',
                  'es_launcher.ini error!')
            raise SystemExit

    if isfile('es_launcher.ini'):
        with open('es_launcher.ini', 'r') as config_ini:
            for line in config_ini:
                if '=' in line:
                    entry, value = line.lower().split('=', 1)  # normalizing text then spliting 1 time by char '=' in 2
                    entry = entry.strip()  # Removing edge spaces and new line characters,
                    value = value.strip()
                    if entry == 'assync_load' and value == 'true': assync_load = True
                    elif entry == 'silent' and value == 'true': silent = True
                    elif entry == 'dont_hide_es' and value == 'true': hide_es_while_assync_load = False
                    elif entry == 'es_dir': es_dir = check_entry_es_ini(value, 'es_dir')
                    elif entry == 'emuls_root': emuls_root = check_entry_es_ini(value, 'emuls_root')
                    elif entry == 'roms_root': roms_root = check_entry_es_ini(value, 'roms_root')
                    elif entry == 'splashs_root': splashs_root = check_entry_es_ini(value, 'splashs_root')
                    elif entry == 'boot_videos' and value == 'false': boot_videos = False
                    elif entry == 'novid' and value == 'false': play = False
                    elif entry == 'play_vlc_embedded' and value == 'true': play_vlc_embedded = True
                    elif entry == 'exclusive' and value == 'true': kill_exp = True
                    elif entry == 'random_theme' and value == 'true': random_theme = True
                    elif entry == 'ex_fullscreen' and value == 'true': ex_fullscreen = True
                    elif entry == 'debug' and value == 'true':
                        if '--debug' not in es_args: es_args += ' --debug'
                    elif entry == 'vsync' and value == 'true':
                        if '--vsync' not in es_args: es_args += ' --vsync'
                    elif entry == 'fullscreen-borderless' and value == 'true':
                        if '--fullscreen-borderless' not in es_args: es_args += ' --fullscreen-borderless'
                    elif entry == 'resolution':
                        if 'x' in value:
                            width, height, fhz = value.split('x', 2)
                            width = width.strip()
                            height = height.strip()
                            fhz = fhz.strip()
                            if width.isdigit() and height.isdigit() and fhz.isdigit():
                                resolution = width, height, fhz
        config_ini.close()
    # ------------------------------------------- Checking Arguments ---------------------------------------------------
    for arg in sys.argv[1:]:  # sys.argv[1:] means it will ignore first element if it is converted to .exe
        arg = arg.lower()
        if '=' in arg:
            arg, value = arg.split('=', 1)
            if arg == '--es': es_dir = value
            elif arg == '--sp': splashs_root = value
            elif arg == '--em': emuls_root = value
            elif arg == '--ro': roms_root = value
            elif arg == '--resolution':
                def msg_alert(valuex):
                    alert(f'Argument --resolution has a value not supported: {valuex}', 'Argument error!')
                    raise SystemExit
                if 'x' in value:
                    wid_hei_fhz = value.split('x', 2)
                    if len(wid_hei_fhz) > 2:
                        if wid_hei_fhz[0].isdigit() and wid_hei_fhz[1].isdigit() and wid_hei_fhz[2].isdigit():
                            resolution = wid_hei_fhz
                        else: msg_alert(value)
                    else: msg_alert(value)
                else: msg_alert(value)
        else:
            if arg == '--novid': play = False
            if arg == '--silent' or arg == '-s': silent = True
            elif arg == '-e': kill_exp = True
            elif arg == '--exf': ex_fullscreen = True
            elif arg == '--rt': random_theme = True
            elif arg == '--play_vlc_embedded': play_vlc_embedded = True
            elif arg == '--no_boot_videos': boot_videos = False
            elif arg == '--assync_load': assync_load = True
            elif arg == '--dont_hide_es': hide_es_while_assync_load = False
            else: es_args += ' ' + arg

    return es_dir, emuls_root, roms_root, settings_cfg_file, startup_dir,\
        intro_file, splashs_root, vlcargs, es_args, kill_exp, random_theme, ex_fullscreen,\
        assync_load, play_vlc_embedded, play, hide_es_while_assync_load, boot_videos, resolution,\
        current_process_hwnds


def play_menu_sound(audio_file):
    if exists(audio_file):
        playsound(audio_file)


def new_startupinfo(window_hidden=False):
    import subprocess
    startupinfo = subprocess.STARTUPINFO()
    if window_hidden:
        startupinfo.dwFlags = startupinfo.dwFlags | subprocess.STARTF_USESHOWWINDOW
    return startupinfo
    # If you wish use win32gui.ShowWindow(hwnd, win32con.SW_SHOW) make it visible later on

    # Alternative version of the code
    # si = sp.STARTUPINFO()
    # si.dwFlags |= sp.STARTF_USESHOWWINDOW
    # si.wShowWindow = sp.SW_HIDE
    # return si


def replace_line(file_path, str2find, new_line_content):
    with open(file_path, 'r') as settings_file:
        file_copy = [new_line_content if str2find in line else line for line in settings_file]
    settings_file.close()

    with open(file_path, 'w+') as settings_file:
        for item in file_copy:
            settings_file.write(item)
    settings_file.close()


def scandir_recursivelly(basedir):
    items_list = []
    files_list = []
    dirs_list = []
    for item in scandir(basedir):
        items_list.append(item)
        if item.is_dir():
            dirs_list.append(item.path)
            items, files, dirs = scandir_recursivelly(item.path)
            items_list.extend(items)
            files_list.extend(files)
            dirs_list.extend(dirs)
        else:
            files_list.append(item.path)
    return items_list, files_list, dirs_list


class NewPopen(sp.Popen):
    def bring_window_on_top(self, once=True):
        script_pid = win32api.GetCurrentThreadId()
        hwnds = []
        timer = time.time()
        while pid_exists(self.pid) or (time.time() - timer) <= 5:
            def callback_hwnds(window_handle, hwnds):
                if win32gui.IsWindow(window_handle) and win32gui.IsWindowEnabled(window_handle)\
                        and win32gui.IsWindowVisible(window_handle):
                    thread_id, process_id = win32process.GetWindowThreadProcessId(window_handle)
                    if process_id == self.pid:
                        hwnds.append([window_handle, thread_id])

            win32gui.EnumWindows(callback_hwnds, hwnds)  # Exception can be bypassed with try: except:
            if len(hwnds) > 0:  # Finishes the while loop if hwnds list is not empty
                hwnd, hwnd_thread_id = hwnds[0]
                while pid_exists(self.pid):
                    try:
                        win32process.AttachThreadInput(script_pid, hwnd_thread_id, True)
                        win32gui.SetForegroundWindow(hwnd)
                        win32gui.SetFocus(hwnd)
                        if once: break
                    except:
                        pass
                break

    first_hwnd = None

    def get_first_hwnd_from_pid(self):  # Returns a single int that contains the fist hwnd id found
        def callback_hwnds(hwnd, _):  # _ variable is generally used as unusable variable in, other words, ignorable
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd):
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                if process_id == self.pid:
                    self.first_hwnd = hwnd
                    return False  # Forces EnumWindow to stop searching but raise exception. Can be bypassed with try
        # fist_hwnd is used as second argument ("extra", see doc) and updated inside callback funcion
        try:
            win32gui.EnumWindows(callback_hwnds, None)
        except:
            pass
        if win32gui.IsWindow(self.first_hwnd) and win32gui.IsWindowEnabled(self.first_hwnd):
            return self.first_hwnd
        else:
            alert(f'{Process(self.pid).name()}, has no valid handler that IsWindow() and IsWindowEnabled()')
            raise SystemExit

    def get_hwnds_from_pid(self):    # Returns a list of int values
        def callback_hwnds(hwnd, list2populate):
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd):
                thread_id, process_id = win32process.GetWindowThreadProcessId(hwnd)
                if process_id == self.pid:
                    list2populate.append(hwnd)
        hwnds_list = []
        if pid_exists(self.pid):
            # On every EnunWindows Call hwnds_list_internal is updated by callback function (read EnumWindows Doc)
            win32gui.EnumWindows(callback_hwnds, hwnds_list)  # will populate hwnds_list_internal
            if isinstance(hwnds_list, list) and len(hwnds_list) > 0:
                return hwnds_list
            else:
                alert(f'{Process(self.pid).name()}, has no handler that IsWindow() and IsWindowEnabled()')
                raise SystemExit

    def hide_window(self):
        hwnds = self.get_hwnds_from_pid()
        for hwnd in hwnds:
            if pid_exists(self.pid) and win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)

    def unhide_window(self):
        hwnds = self.get_hwnds_from_pid()
        for hwnd in hwnds:
            if pid_exists(self.pid) and not win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

    def get_audio_session(self):
        from pycaw.pycaw import AudioUtilities
        timer0 = time.time()
        while AudioUtilities.GetProcessSession(self.pid) is None and pid_exists(self.pid):
            if time.time() - timer0 >= 60.0:
                alert('1min Timeout rewhile waiting for emulstation process to be acessible.', 'ES_Launcher Error!')
                raise SystemExit
        return AudioUtilities.GetProcessSession(self.pid).SimpleAudioVolume

    def setmute(self, true_or_false):
        if true_or_false:
            self.get_audio_session().SetMute(1, None)
        else:
            self.get_audio_session().SetMute(0, None)


def startup_videos(vlc_path, intro_file, startup_dir, splashs_dir, boot_videos, play_vlc_embedded=False, hwnd2drawon=0):
    # Optional --file-caching=1000 --reset-config
    vlcargs = ' --fullscreen --qt-fullscreen-screennumber=1 --video-on-top --no-video-title-show --no-video-deco' \
              ' --ignore-config --one-instance --high-priority --no-lua -Idummy --play-and-exit' \
              ' --no-mouse-events --mouse-hide-timeout=1 --plugins-cache --no-plugins-scan --no-reset-plugins-cache'
    if play_vlc_embedded:
        vlcargs += ' --drawable-hwnd=' + str(hwnd2drawon)

    def play_on_vlc(vlc_path, vlcargs, videofiles_dir):
        def pickafile(dir_path_in, ext_list=['.mp4', '.m4v', '.mkv', '.flv', '.avi', '.wmv', '.mpg', '.mpeg']):
            from random import randint
            videoflist = [i for i in scandir_recursivelly(dir_path_in)[1] for ext in ext_list if splitext(i)[1] == ext]
            if isinstance(videoflist, list) and len(videoflist) > 0:
                return videoflist[randint(0, len(videoflist) - 1)]
            else:
                alert(f'No video file found inside {dir_path_in}')
                raise SystemExit
        if '&' in videofiles_dir:
            videos2play = [pickafile(dir_path) for dir_path in videofiles_dir.split('&')]
            videos_str = str()
            for file_path in videos2play:
                videos_str += f'"{file_path}" '
            return NewPopen(f'"{vlc_path}" {vlcargs} {videos_str}')
        else:
            return NewPopen(f'"{vlc_path}" {vlcargs} "{pickafile(videofiles_dir)}"')

    if exists(intro_file):
        return play_on_vlc(vlc_path, vlcargs, intro_file)
    elif exists(startup_dir) and boot_videos:
        return play_on_vlc(vlc_path, vlcargs, startup_dir + '&' + splashs_dir)
    else:
        return play_on_vlc(vlc_path, vlcargs, splashs_dir)  # Returns NewPopen Object


def es_cfg_files(es_maindir_in, emuls_root_in, roms_root_in):
    def es_input_cfg(es_maindir):
        check_button(f'{es_maindir}\\es_input.cfg \n This file will be generated now.', title='File not found!')
        with open(es_maindir + '\\es_input.cfg', 'w+') as file:
            file.write('''<?xml version="1.0"?>
<inputList>
    <inputConfig type="joystick" deviceName="Wireless Controller" deviceGUID="4c05c405000000000000504944564944">
        <input name="a" type="button" id="1" value="1" />
        <input name="b" type="button" id="2" value="1" />
        <input name="down" type="hat" id="0" value="4" />
        <input name="hotkeyenable" type="button" id="12" value="1" />
        <input name="left" type="hat" id="0" value="8" />
        <input name="leftanalogdown" type="axis" id="1" value="1" />
        <input name="leftanalogleft" type="axis" id="0" value="-1" />
        <input name="leftanalogright" type="axis" id="0" value="1" />
        <input name="leftanalogup" type="axis" id="1" value="-1" />
        <input name="leftshoulder" type="button" id="4" value="1" />
        <input name="leftthumb" type="button" id="10" value="1" />
        <input name="lefttrigger" type="button" id="6" value="1" />
        <input name="right" type="hat" id="0" value="2" />
        <input name="rightanalogdown" type="axis" id="5" value="1" />
        <input name="rightanalogleft" type="axis" id="2" value="-1" />
        <input name="rightanalogright" type="axis" id="2" value="1" />
        <input name="rightanalogup" type="axis" id="5" value="-1" />
        <input name="pageup" type="button" id="5" value="1" />
        <input name="rightthumb" type="button" id="11" value="1" />
        <input name="pagedown" type="button" id="7" value="1" />
        <input name="select" type="button" id="8" value="1" />
        <input name="start" type="button" id="9" value="1" />
        <input name="up" type="hat" id="0" value="1" />
        <input name="x" type="button" id="3" value="1" />
        <input name="y" type="button" id="0" value="1" />
    </inputConfig>
    <inputConfig type="joystick" deviceName="DUALSHOCK®4 USB Wireless Adaptor" deviceGUID="4c05a00b000000000000504944564944">
        <input name="a" type="button" id="1" value="1" />
        <input name="b" type="button" id="2" value="1" />
        <input name="down" type="hat" id="0" value="4" />
        <input name="hotkeyenable" type="button" id="12" value="1" />
        <input name="left" type="hat" id="0" value="8" />
        <input name="leftanalogdown" type="axis" id="1" value="1" />
        <input name="leftanalogleft" type="axis" id="0" value="-1" />
        <input name="leftanalogright" type="axis" id="0" value="1" />
        <input name="leftanalogup" type="axis" id="1" value="-1" />
        <input name="leftshoulder" type="button" id="4" value="1" />
        <input name="leftthumb" type="button" id="10" value="1" />
        <input name="lefttrigger" type="button" id="6" value="1" />
        <input name="right" type="hat" id="0" value="2" />
        <input name="rightanalogdown" type="axis" id="5" value="1" />
        <input name="rightanalogleft" type="axis" id="2" value="-1" />
        <input name="rightanalogright" type="axis" id="2" value="1" />
        <input name="rightanalogup" type="axis" id="5" value="-1" />
        <input name="pageup" type="button" id="5" value="1" />
        <input name="rightthumb" type="button" id="11" value="1" />
        <input name="pagedown" type="button" id="7" value="1" />
        <input name="select" type="button" id="8" value="1" />
        <input name="start" type="button" id="9" value="1" />
        <input name="up" type="hat" id="0" value="1" />
        <input name="x" type="button" id="3" value="1" />
        <input name="y" type="button" id="0" value="1" />
    </inputConfig>
    <inputConfig type="joystick" deviceName="XInput Controller #1" deviceGUID="78696e70757401000000000000000000">
        <input name="a" type="button" id="0" value="1" />
        <input name="b" type="button" id="1" value="1" />
        <input name="down" type="hat" id="0" value="4" />
        <input name="hotkeyenable" type="button" id="10" value="1" />
        <input name="left" type="hat" id="0" value="8" />
        <input name="leftanalogdown" type="axis" id="1" value="1" />
        <input name="leftanalogleft" type="axis" id="0" value="-1" />
        <input name="leftanalogright" type="axis" id="0" value="1" />
        <input name="leftanalogup" type="axis" id="1" value="-1" />
        <input name="leftshoulder" type="button" id="4" value="1" />
        <input name="leftthumb" type="button" id="8" value="1" />
        <input name="lefttrigger" type="axis" id="2" value="1" />
        <input name="right" type="hat" id="0" value="2" />
        <input name="rightanalogdown" type="axis" id="4" value="1" />
        <input name="rightanalogleft" type="axis" id="3" value="-1" />
        <input name="rightanalogright" type="axis" id="3" value="1" />
        <input name="rightanalogup" type="axis" id="4" value="-1" />
        <input name="rightshoulder" type="button" id="5" value="1" />
        <input name="rightthumb" type="button" id="9" value="1" />
        <input name="righttrigger" type="axis" id="5" value="-1" />
        <input name="select" type="button" id="6" value="1" />
        <input name="start" type="button" id="7" value="1" />
        <input name="up" type="hat" id="0" value="1" />
        <input name="x" type="button" id="3" value="1" />
        <input name="y" type="button" id="2" value="1" />
    </inputConfig>
    <inputConfig type="joystick" deviceName="PS4 Controller" deviceGUID="030000004c050000a00b000000016800">
        <input name="a" type="button" id="0" value="1" />
        <input name="b" type="button" id="1" value="1" />
        <input name="down" type="button" id="12" value="1" />
        <input name="hotkey" type="button" id="15" value="1" />
        <input name="joystick1left" type="axis" id="0" value="-1" />
        <input name="joystick1up" type="axis" id="1" value="-1" />
        <input name="joystick2left" type="axis" id="2" value="-1" />
        <input name="joystick2up" type="axis" id="3" value="-1" />
        <input name="l2" type="axis" id="4" value="1" />
        <input name="l3" type="button" id="7" value="1" />
        <input name="left" type="button" id="13" value="1" />
        <input name="pagedown" type="button" id="10" value="1" />
        <input name="pageup" type="button" id="9" value="1" />
        <input name="r2" type="axis" id="5" value="1" />
        <input name="r3" type="button" id="8" value="1" />
        <input name="right" type="button" id="14" value="1" />
        <input name="select" type="button" id="4" value="1" />
        <input name="start" type="button" id="6" value="1" />
        <input name="up" type="button" id="11" value="1" />
        <input name="x" type="button" id="3" value="1" />
        <input name="y" type="button" id="2" value="1" />
    </inputConfig>
    <inputConfig type="keyboard" deviceName="Keyboard" deviceGUID="-1">
        <input name="a" type="key" id="13" value="1" />
        <input name="b" type="key" id="8" value="1" />
        <input name="down" type="key" id="1073741905" value="1" />
        <input name="hotkey" type="key" id="1073741897" value="1" />
        <input name="joystick1left" type="key" id="1073741913" value="1" />
        <input name="joystick1up" type="key" id="1073741917" value="1" />
        <input name="joystick2left" type="key" id="104" value="1" />
        <input name="joystick2up" type="key" id="117" value="1" />
        <input name="l2" type="key" id="1073742053" value="1" />
        <input name="l3" type="key" id="1073742049" value="1" />
        <input name="left" type="key" id="1073741904" value="1" />
        <input name="pagedown" type="key" id="1073741902" value="1" />
        <input name="pageup" type="key" id="1073741899" value="1" />
        <input name="r2" type="key" id="1073742052" value="1" />
        <input name="r3" type="key" id="1073742048" value="1" />
        <input name="right" type="key" id="1073741903" value="1" />
        <input name="select" type="key" id="9" value="1" />
        <input name="start" type="key" id="1073741898" value="1" />
        <input name="up" type="key" id="1073741906" value="1" />
        <input name="x" type="key" id="32" value="1" />
        <input name="y" type="key" id="102" value="1" />
    </inputConfig>
</inputList>''')
        file.close()

    def es_settings_cfg(es_maindir):
        check_button(f'{es_maindir}\\es_settings.cfg \n This file will be generated now.', title='File not found!')
        with open(es_maindir + '\\es_settings.cfg', 'w+') as file:
            file.write(f'''<?xml version="1.0"?>
<config>
    <bool name="CaptionsCompatibility" value="false" />
    <bool name="ClockMode12" value="false" />
    <bool name="EnableSounds" value="true" />
    <bool name="LocalArt" value="true" />
    <bool name="ParseGamelistOnly" value="true" />
    <bool name="PreloadUI" value="true" />
    <bool name="PublicWebAccess" value="false" />
    <bool name="SaveGamelistsOnExit" value="false" />
    <bool name="ScrapeBoxBack" value="true" />
    <bool name="ScrapeFanart" value="true" />
    <bool name="ScrapeManual" value="false" />
    <bool name="ScrapeMap" value="true" />
    <bool name="ScrapeVideos" value="true" />
    <bool name="ScreenSaverOmxPlayer" value="true" />
    <bool name="ScreenSaverVideoMute" value="true" />
    <bool name="ShowHelpPrompts" value="false" />
    <bool name="ShowHiddenFiles" value="true" />
    <bool name="ShowManualIcon" value="false" />
    <bool name="ShowNetworkIndicator" value="true" />
    <bool name="ShowOnlyExit" value="false" />
    <bool name="ShowParentFolder" value="false" />
    <bool name="ShowSaveStates" value="false" />
    <bool name="SlideshowScreenSaverRecurse" value="true" />
    <bool name="SlideshowScreenSaverStretch" value="true" />
    <bool name="SortAllSystems" value="false" />
    <bool name="VideoAudio" value="false" />
    <bool name="updates.enabled" value="false" />
    <int name="MaxVRAM" value="1000" />
    <int name="MusicVolume" value="60" />
    <int name="ScraperResizeWidth" value="400" />
    <int name="ScreenSaverSwapImageTimeout" value="5000" />
    <int name="ScreenSaverTime" value="60000" />
    <int name="recent.sort" value="7" />
    <string name="CollectionSystemsAuto" value="all,favorites,recent" />
    <string name="DefaultGridSize" value="7 2" />
    <string name="ExePath" value="emulationstation.exe" />
    <string name="FolderViewMode" value="always" />
    <string name="GamelistViewStyle" value="video" />
    <string name="Language" value="en_US" />
    <string name="LastSystem" value="3do" />
    <string name="LogLevel" value="disabled" />
    <string name="PowerSaverMode" value="disabled" />
    <string name="SaveGamelistsMode" value="on exit" />
    <string name="ScreenSaverBehavior" value="random video" />
    <string name="ScreenSaverGameInfo" value="start &amp; end" />
    <string name="ShowFlags" value="auto" />
    <string name="SlideshowScreenSaverBackgroundAudioFile" value="D:/EmulationStation Portable/.emulationstation/slideshow/audio/slideshow_bg.wav" />
    <string name="SlideshowScreenSaverImageDir" value="D:/EmulationStation Portable/.emulationstation/slideshow/image" />
    <string name="SortSystems" value="" />
    <string name="ThemeSet" value="RVGM-BT-Theme" />
    <string name="UIMode_passkey" value="uuddlrlrba" />
    <string name="subset.gamelistInfoColor" value="gamelistInfoDarth" />
    <string name="subset.swapAmbiance" value="setMediaLibrary" />
    <string name="subset.swapColor" value="orange" />
    <string name="subset.swapVideoEffect" value="videoEffectBump" />
    <string name="subset.systemView" value="menuVertLeft" />
    <string name="updates.type" value="beta" />
</config>''')
        file.close()
        return es_maindir + '\\es_settings.cfg'

    def es_systems_cfg(es_maindir, emuls_root_in, roms_root_in):
        check_button(f'{es_maindir}\\es_systems.cfg \n This file will be generated now.', title='File not found!')
        gen_es_systems_cfg(roms_root=roms_root_in, emus_root=emuls_root_in, es_systems_loc=es_maindir)

    if not exists(es_maindir_in):
        makedirs(es_maindir_in)
    if not exists(join(es_maindir_in, 'es_input.cfg')):
        es_input_cfg(es_maindir_in)
    if not exists(join(es_maindir_in, 'es_systems.cfg')):
        es_systems_cfg(es_maindir_in, emuls_root_in, roms_root_in)
    if not exists(join(es_maindir_in, 'es_settings.cfg')):
        es_settings_cfg(es_maindir_in)
    else:
        return join(es_maindir_in, 'es_settings.cfg')


def gen_es_systems_cfg(systems_list=[],
                       roms_root='..\\Roms',
                       emus_root='..\\Emulators',
                       emu_exe_path='..\\Emulators\\Retroarch\\retroarch.exe',
                       emu_args='-L "..\\Emulators\\Retroarch\\Cores\\bsnes_hd_beta_libretro.dll"',
                       es_systems_loc=''):
    def add_system(tag='system', sub_tag_list=['fullname', 'name', 'platform', 'theme', 'extension', 'path', 'command'],
                   values_list=[]):
        def enum_extensions(extensions=''):
            filtered_extensions = ''
            for ext in sorted(list(set(extensions.lower().replace(' ', '').split('.')))):
                if ext != '':
                    filtered_extensions += '.' + ext + " ." + ext.upper() + " "
            return filtered_extensions.strip()

        parent_tag = ElementTree.Element(tag)
        if len(sub_tag_list) == len(values_list) == 7:
            if not isinstance(values_list[1], str) or values_list[1] == '':
                values_list[1] = values_list[0].lower()
            if not isinstance(values_list[2], str) or values_list[2] == '':
                values_list[2] = values_list[1].lower()
            if not isinstance(values_list[3], str) or values_list[3] == '':
                values_list[3] = values_list[2].lower()
            if not isinstance(values_list[4], str) or values_list[4] == '' or '.' not in values_list[4]:
                values_list[4] = ".7z .7Z .zip .ZIP"
            else:
                values_list[4] = enum_extensions(values_list[4])
            if "%ROM_RAW%" not in values_list[6]:
                values_list[6] += ' "%ROM_RAW%"'
            for index in range(0, len(sub_tag_list)):
                sub_element = ElementTree.SubElement(parent_tag, sub_tag_list[index])
                sub_element.text = values_list[index]
        else:
            alert(f'size of sub_elements_list: {len(sub_tag_list)} doesn\'t match or is missing values'
                  f'values_list: {len(values_list)}')
            raise SystemExit

        return parent_tag

    def _pretty_print(current, parent=None, index=-1, depth=0):
        for i, node in enumerate(current):
            _pretty_print(node, current, i, depth+1)
        if parent is not None:
            if index == 0:
                parent.text = '\n'+('\t'*depth)
            else:
                parent[index-1].tail = '\n'+('\t'*depth)
            if index == len(parent)-1:
                current.tail = '\n'+('\t'*(depth-1))

    root = ElementTree.Element("systemList")
    for system in systems_list:
        root.append(system)

    root.append(
        add_system(values_list=['Final Burn Alpha', 'fba', '', '', '', join(roms_root, "fba"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fbalpha_libretro.dll"']))
    root.append(add_system(values_list=['Final Burn Neo', 'fbn', '', '', '', join(roms_root, "fbn"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fbneo_libretro.dll"']))
    root.append(
        add_system(values_list=['Capcom Play System I', 'cps1', '', '', '', join(roms_root, "cps1"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fbalpha_libretro.dll"']))
    root.append(
        add_system(values_list=['Neo Geo', 'neogeo', '', '', '', join(roms_root, "neogeo"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fbalpha_libretro.dll"']))
    root.append(
        add_system(values_list=['Classic Arcade', 'arcade', '', '', '', join(roms_root, "neogeo"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fbalpha_libretro.dll"']))
    root.append(
        add_system(values_list=['Capcom Play System II', 'cps2', '', '', '', join(roms_root, "cps2"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fbalpha_libretro.dll"']))
    root.append(
        add_system(values_list=['Capcom Play System III', 'cps3', '', '', '', join(roms_root, "cps3"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fbalpha_libretro.dll"']))
    root.append(add_system(values_list=['Multiple Arcade Machine Emulator', 'mame', '', '', '', join(roms_root, "mame"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mame_libretro.dll"']))
    root.append(
        add_system(values_list=['M.A.M.E. 2003', 'mame2003', '', '', '', join(roms_root, "mame2003"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mame2003_libretro.dll"']))
    root.append(
        add_system(values_list=['M.A.M.E. 2003+', 'mame2003plus', '', '', '', join(roms_root, "mame2003plus"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mame2003_libretro.dll"']))
    root.append(
        add_system(values_list=['M.A.M.E. 2010', 'mame2010', '', '', '', join(roms_root, "mame2010"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mame2010_libretro.dll"']))
    root.append(
        add_system(values_list=['M.A.M.E. 2012', 'mame2012', '', '', '', join(roms_root, "mame2012"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mame2012_libretro.dll"']))
    root.append(
        add_system(values_list=['M.A.M.E. 2015', 'mame2015', '', '', '', join(roms_root, "mame2015"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mame2015_libretro.dll"']))
    root.append(
        add_system(values_list=['M.A.M.E. 2016', 'mame2016', '', '', '', join(roms_root, "mame2016"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mame2016_libretro.dll"']))
    root.append(
        add_system(values_list=['Sega Naomi', 'naomi', '', '', '.7z .cue .zip', join(roms_root, "naomi"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\flycast_libretro.dll"']))
    root.append(
        add_system(values_list=['Sega Naomi II', 'naomi2', '', '', '.7z .cue .zip', join(roms_root, "naomi2"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\flycast_libretro.dll"']))
    root.append(
        add_system(values_list=['AtomisWave', '', '', '', '.7z .cue .zip .chd .gd .bin', join(roms_root, "atomiswave"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\flycast_libretro.dll"']))
    root.append(
        add_system(values_list=['Astrocade', '', '', '', '.7z .wsc .zip', join(roms_root, "astrocade"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mess2015_libretro.dll"']))
    root.append(
        add_system(values_list=['Daphne', '', '', '', '.daphne.sna.szx.z80.tap.tzx.gz.udi.mgt.img.trd.scl.dsk.zip.7z',
                                join(roms_root, "daphne"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\daphne_libretro.dll"']))
    root.append(
        add_system(values_list=['Sega Model II', 'model2', '', '', '', join(roms_root, "model2"), emu_exe_path]))
    root.append(
        add_system(values_list=['Sega Model III', 'model3', '', '', '', join(roms_root, "model3"), emu_exe_path]))
    root.append(
        add_system(
            values_list=['Nintendo Entertainment System', 'nes', '', '', '.7z .fds .fig .mgd .nes .sfc .smc .swc .zip',
                         join(roms_root, "nes"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\nestopia_libretro.dll"']))
    root.append(

        add_system(
            values_list=['Famicom Disk System', 'fds', '', '', '.7z .fds .zip', join(roms_root, "fds"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\nestopia_libretro.dll"']))
    root.append(
        add_system(values_list=['Super Nintendo Entertainment System', 'snes', '', '', '.smc .sfc .7z .zip',
                                join(roms_root, "snes"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\bsnes_hd_beta_libretro.dll"']))
    root.append(
        add_system(values_list=['Nintendo Satellaview', 'satellaview', '', '', '.smc .sfc .7z .zip',
                                join(roms_root, "satellaview"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\bsnes_hd_beta_libretro.dll"']))
    root.append(
        add_system(values_list=['Sufami Turbo', 'sufami', '', '', '.smc .sfc .7z .zip',
                                join(roms_root, "sufami"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\snes9x_libretro.dll"']))
    root.append(add_system(values_list=['Nintendo 64', 'n64', '', '', '.7z .n64 .v64 .z64 .zip', join(roms_root, "n64"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\snes9x_libretro.dll"']))
    root.append(
        add_system(values_list=['Nintendo Game Cube', 'gc', '', '', '.iso .gcm .gcz .wbfs .ciso',
                                join(roms_root, "gc"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\dolphin_libretro.dll"']))
    root.append(
        add_system(values_list=['Nintendo Wii', 'wii', '', '', '.iso .gcm .gcz .wbfs .ciso',
                                join(roms_root, "wii"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\dolphin_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Sony Playstation', 'psx', '', '', '.iso .bin .chd .cue .pbp', join(roms_root, "psx"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mednafen_psx_hw_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Sony Playstation 2', 'ps2', '', '', '.iso .isz .chd .cso', join(roms_root, "ps2"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\pcsx2_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Sony Playstation Portable ', 'psp', '', '', '.iso .cso', join(roms_root, "psp"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\ppsspp_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Playstation Portable Mini', 'pspmini', '', '', '.iso .cso', join(roms_root, "pspmini"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\ppsspp_libretro.dll"']))

    root.append(
        add_system(
            values_list=['Sega Mega Drive', 'megadrive', '', '', '.7z .md .smd .zip', join(roms_root, "megadrive"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\genesis_plus_gx_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Sega genesis', 'genesis', '', '', '.7z .md .smd .zip', join(roms_root, "genesis"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\genesis_plus_gx_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Sega SG-1000', 'sg1000', '', '', '.7z .bin .sg .zip', join(roms_root, "sg1000"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\genesis_plus_gx_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Sega Master System', 'sms', '', '', '.7z .bin .sms .zip', join(roms_root, "sms"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\genesis_plus_gx_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Sega CD', 'segacd', '', '', '.bin .chd .cue .iso', join(roms_root, "segacd"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\genesis_plus_gx_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Sega Saturn', 'saturn', '', '', '.bin .chd .cue .iso', join(roms_root, "saturn"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\kronos_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Sega Dreamcast', 'dreamcast', '', '', '.bin .chd .cue .iso', join(roms_root, "dreamcast"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\flycast_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Panasonic 3do', '3do', '', '', '.bin .chd .cue .iso', join(roms_root, "3do"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\opera_libretro.dll"']))
    root.append(
        add_system(values_list=['Sega 32X', '32x', '', '', '.32x .7z .bin .md .smd .zip', join(roms_root, "32x"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\picodrive_libretro.dll"']))
    root.append(
        add_system(values_list=['Apple II', 'apple2', '', '', '.7z .dsk .zip', join(roms_root, "apple2"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\cap32_libretro.dll"']))
    root.append(add_system(values_list=['MSX', '', '', '', '.7z .col .dsk .mx1 .mx2 .rom .zip', join(roms_root, "msx"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fmsx_libretro.dll"']))
    root.append(
        add_system(values_list=['MSX2', '', '', '', '.7z .col .dsk .mx1 .mx2 .rom .zip', join(roms_root, "msx2"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fmsx_libretro.dll"']))
    root.append(add_system(values_list=['ZX Spectrum', 'zxspectrum', '', '',
                                        '.7z.dsk.gz.img.mgt.scl.sna.szx.tap.trd.tzx.udi.z80.zip',
                                        join(roms_root, "zxspectrum"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fuse_libretro.dll"']))
    root.append(add_system(values_list=['Odyssey2', 'odssey2', '', '', '.7z .bin .zip', join(roms_root, "odssey2"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fuse_libretro.dll"']))
    root.append(add_system(values_list=['Amiga', '', '', '', '.7z.adf.adz.dms.exe.rp9.zip', join(roms_root, "amiga"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fuse_libretro.dll"']))
    root.append(add_system(values_list=['Sharp x68000', 'x68000', '', '', '.7z .dim .zip', join(roms_root, "x68000"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fuse_libretro.dll"']))
    root.append(add_system(values_list=['Commodore 64', 'c64', '', '', '.7z .zip .crt .d64 .g64 .t64 .tap .x64',
                                        join(roms_root, "c64"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fuse_libretro.dll"']))
    root.append(add_system(values_list=['Videopac', '', '', '', '.7z .bin .zip', join(roms_root, "videopac"),
                                        f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\fuse_libretro.dll"']))
    root.append(
        add_system(values_list=['TurboGrafx 16 (PC Engine)', 'pcengine', '', '', '.7z .cue .pce .zip',
                                join(roms_root, "pcengine"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mednafen_pce_libretro.dll"']))
    root.append(
        add_system(values_list=['PC-FX', 'supergrafx', '', '', '.7z .cue .pce .zip', join(roms_root, "pcfx"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mednafen_pce_libretro.dll"']))
    root.append(
        add_system(values_list=['Colecovision', 'coleco', '', '', '.7z .bin .gam .vec .zip', join(roms_root, "coleco"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\bluemsx_libretro.dll"']))
    root.append(
        add_system(values_list=['Vectrex', '', '', '', '.7z .bin .gam .vec .zip', join(roms_root, "vectrex"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\vecx_libretro.dll"']))
    root.append(
        add_system(values_list=['Amistrad CPC', '', '', '', '.7z .bin .gam .vec .zip', join(roms_root, "amstradcpc"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\cap32_libretro.dll"']))
    root.append(
        add_system(values_list=['Atari 800', 'atari800', '', '', '.7z .bin .rom .zip', join(roms_root, "atari800"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\stella_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Atari 2600', 'atari2600', '', '', '.7z .a26 .bin .rom .zip', join(roms_root, "atari2600"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\stella_libretro.dll"']))
    root.append(
        add_system(values_list=['Atari 5200', 'atari5200', '', '', '.7z.a52.bas.bin.xex.atr.xfd.dcm.atr.gz.xfd.gz.zip',
                                join(roms_root, "atari5200"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\stella_libretro.dll"']))
    root.append(
        add_system(values_list=['Atari 7800', 'atari7800', '', '', '.7z .a78 .bin .zip', join(roms_root, "atari7800"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\prosystem_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Atari Jaguar', 'atarijaguar', '', '', '.7z .j64 .jag .zip', join(roms_root, "atarijaguar"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\virtualjaguar_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Atari ST', 'atarist', '', '', '.7z.ctr.img.ipf.rom.st.stx.zip', join(roms_root, "atarist"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\hatari_libretro.dll"']))
    root.append(
        add_system(values_list=['M.U.G.E.M. ', 'mugem', '', '', '.exe', join(roms_root, "mugem"), '"%ROM_RAW%"']))
    root.append(
        add_system(values_list=['Game Boy', 'gb', '', '', '.7z .bin .gb .rom .zip', join(roms_root, "gb"),
                                f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\vbam_libretro.dll"']))
    root.append(
            add_system(values_list=['Game Boy Color', 'gbc', '', '', '.7z .bin .gbc .rom .zip', join(roms_root, "gbc"),
                                    f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\vbam_libretro.dll"']))
    root.append(
            add_system(
                values_list=['Virtual Boy', 'virtualboy', '', '', '.7z.bin.gbc.rom.zip', join(roms_root, "virtualboy"),
                             f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mednafen_vb_libretro.dll"']))
    root.append(
            add_system(values_list=['Game Boy Advance', 'gba', '', '', '.7z.bin.gba.rom.zip', join(roms_root, "gba"),
                                    f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\vbam_libretro.dll"']))
    root.append(
            add_system(
                values_list=['Nintendo DS', 'nds', '', '', '.7z .nds .zip', join(roms_root, "nds"),
                             f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\desmume_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Nintendo 3DS', '3ds', '', '', '.3ds .7z .cia .zip', join(roms_root, "3ds"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\citra_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Game Gear', 'gamegear', '', '', '.7z .bin .gg .zip', join(roms_root, "gamegear"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\genesis_plus_gx_libretro.dll"']))
    root.append(
        add_system(
            values_list=['WonderSwan', '', '', '', '.7z .ws .zip', join(roms_root, "wonderswan"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mednafen_wswan_libretro.dll"']))
    root.append(
        add_system(
            values_list=['WonderSwan Color', 'wonderswancolor', '', '', '.7z.ws.zip',
                         join(roms_root, "wonderswancolor"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mednafen_wswan_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Atari Lynx', 'atarilynx', '', '', '.7z .lnx .zip', join(roms_root, "atarilynx"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\handy_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Neo Geo Pocket', 'ngp', '', '', '.7z .ngp .zip', join(roms_root, "ngp"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mednafen_ngp_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Neo Geo Pocket Color', 'ngpc', '', '', '.7z .ngc .zip', join(roms_root, "ngpc"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\mednafen_ngp_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Pokemon Mini', 'pokemini', '', '', '.7z .ngc .zip', join(roms_root, "pokemini"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\pokemini_libretro.dll"']))
    root.append(
        add_system(
            values_list=['PC', 'pc', '', '', '.bat .exe .py .pyw .vbs', join(roms_root, "PC"),
                         f'"{emu_exe_path}" -L "..\\Emulators\\Retroarch\\Cores\\pokemini_libretro.dll"']))
    root.append(
        add_system(
            values_list=['Ports', '', '', '', '.bat .exe .py .pyw .vbs', join(roms_root, "ports"),
                         '%ROM_RAW%']))
    root.append(
        add_system(
            values_list=['System Options', 'options', '', '', '.bat .exe .py .pyw .vbs', join(roms_root, "options"),
                         '%ROM_RAW%']))

    _pretty_print(root)  # adds new lines and indentation for reliable readability
    # ElementTree.dump(root)  # prints root elements tree for checking
    ElementTree.ElementTree(root).write(join(es_systems_loc, 'es_systems.cfg'), xml_declaration=True, encoding="UTF-8")


def extract_contents2(file_path, dest_dir='.', temp_dir='!Temp_Dir'):
    def count_dirandfiles(dir_path):
        temp_scan = scandir(dir_path)
        last_dir_path = dir_path
        dir_count = file_count = 0
        for item in temp_scan:
            if item.is_dir():
                dir_count += 1
                dir_path = item.path
            else:
                file_count += 1
        if 1 == dir_count > file_count == 0:
            return count_dirandfiles(dir_path)
        else:
            return last_dir_path

    def move_files_recur(path_loc, dest_path):
        if not isdir(dest_path):
            makedirs(dest_path)
        if isdir(path_loc) and isdir(dest_path):
            for item in scandir(path_loc):
                if item.is_dir():
                    move_files_recur(item.path, join(dest_path, item.name))
                else:
                    future_file_path = join(dest_path, item.name)
                    if exists(future_file_path):
                        try:
                            remove(future_file_path)
                        except:
                            alert(f'The file "{future_file_path}" could not be removed')
                    move(item.path, dest_path)
        else:
            alert('Alert Message: "dest_dir" or "path_loc" variable input is not a valid directory and/or path')

    if exists(temp_dir):
        rmtree(temp_dir)  # Cleaning any leftover
    mkdir(temp_dir)
    global silent
    sp.run(f'7za.exe x "{file_path}" -o"{temp_dir}" -y', startupinfo=new_startupinfo(silent))  # Using 7zip command line
    new_temp_dir = count_dirandfiles(temp_dir)
    move_files_recur(new_temp_dir, dest_dir)
    rmtree(temp_dir)
    remove(file_path)


def get_files_urls(url):
    # domain_name = urlparse(url).netloc  # Like buildbot.libretro.com
    file_urls = set()  # all URLs of `url`
    domain_name = urlparse(url).netloc  # domain name of the URL without the protocol
    soup = BeautifulSoup(requests.get(url).content, "html.parser")
    for a_tag in soup.findAll("a"):
        href = a_tag.attrs.get("href")
        if href == "" or href is None:  # if href is a empty tag then skips to next for loop
            continue
        url_found = urljoin(url, href)  # join the URL if it's relative (not absolute link)
        url_parsed = urlparse(url_found)  # remove URL GET parameters, URL fragments, etc.
        if bool(url_parsed.scheme) and bool(url_parsed.netloc):  # Checks whether `url` is a valid URL.
            url_reconstructed = url_parsed.scheme + "://" + url_parsed.netloc + url_parsed.path
            if domain_name not in url_reconstructed:
                # print(f'{YELLOW}[!] External link: {url_reconstructed}{RESET}')
                continue
            else:
                # print(f'{GREEN}[*] Internal link: {url_reconstructed}{RESET}')
                if href[-4:] == '.zip' or href[-3:] == '.7z':
                    file_urls.add(url_reconstructed)
        else:
            # print(f'{RED}[!] This is not valid URL: {url_found}{RESET}')
            continue
    return file_urls


def download_binary_r(url_in, file_dest=str()):
    file_name = url_in[url_in.rfind('/') + 1:]
    file_path = join(file_dest, file_name)
    if '\\' not in file_dest:
        curdir = new_getcwd()
        if file_dest == '':
            file_path = join(curdir, file_name)
        else:
            file_path = join(curdir, file_dest)

    bin_data_resp = requests.get(url_in, stream=True)
    with open(file_path, 'wb') as file:
        for chunk in bin_data_resp.iter_content(chunk_size=1048576):
            if chunk:
                file.write(chunk)
    file.close()
    return file_path


def check_button(text='', title='', buttons=['OK', 'Cancel']):
    if not silent:
        button = confirm(text, title, buttons)
        if button is None or button.lower() == 'cancel':
            raise SystemExit
        else:
            return button


def set_emuls_root(path, default_path='..\\EMULATORS'):
    def check_retroarch(retroarch_path):
        retroarch_dir = dirname(retroarch_path)
        if not exists(retroarch_dir):
            try:
                makedirs(retroarch_dir)
            except:
                alert(f"Could not crate directory {retroarch_dir}")
                raise SystemExit
            check_retroarch(retroarch_path)
        elif not exists(retroarch_path):
            check_button(f'RetroArch not found! on path {retroarch_path}, Would like to download it?')
            downloadedfile = download_binary_r('http://buildbot.libretro.com/nightly/windows/x86_64/RetroArch.7z')
            extract_contents2(downloadedfile, retroarch_dir)
            # ---------------------------------------Downloading Assets-----------------------------------------------
            file_urls = get_files_urls("http://buildbot.libretro.com/assets/frontend/")
            for file_url in file_urls:
                downloadedfile = download_binary_r(file_url)
                filename = splitext(downloadedfile[downloadedfile.rfind('\\') + 1:])[0]
                if filename == 'assets':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'assets'))
                elif filename == 'autoconfig':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'autoconfig'))
                elif filename == 'cheats':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'cheats'))
                elif filename == 'database-cursors':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'database\\cursors'))
                elif filename == 'database-rdb':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'database\\rdb'))
                elif filename == 'info':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'info'))
                elif filename == 'overlays':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'overlays'))
                elif filename == 'shaders_cg':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'shaders\\shaders_cg'))
                elif filename == 'shaders_glsl':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'shaders\\shaders_glsl'))
                elif filename == 'shaders_slang':
                    extract_contents2(downloadedfile, join(retroarch_dir, 'shaders\\shaders_slang'))
                else:
                    remove(downloadedfile)
            # --------------------------------------------------------------------------------------------------------
            downloadedfile = download_binary_r('http://buildbot.libretro.com/nightly/windows/x86_64/RetroArch_cores.7z')
            extract_contents2(downloadedfile, join(retroarch_dir, 'cores'))
            # -----------------------------------Finishing Messages---------------------------------------------------
            check_button(f'For OBVIOUS resons I can\'t give you bios/system files for cores that need it to work '
                         f'properlly. On that regard "Google is your frined" ;)', buttons=['OK'])
        # -----------------------------------Retroarch Settings---------------------------------------------------
        retroarch_cfg = join(retroarch_dir, 'retroarch.cfg')
        if not exists(retroarch_cfg):
            configs = '''audio_volume = "0.000000"
                         video_fullscreen = "true"
                         video_windowed_fullscreen = "true"
                         video_window_show_decorations = "false"
                         video_windowed_position_height = "720"
                         video_windowed_position_width = "1280"
                         video_monitor_index = "1"
                         video_smooth = "true"
                         video_threaded = "false"
                         video_vsync = "true"
                         vulkan_gpu_index = "0"'''.splitlines()
            # Optionals: video_refresh_rate = "60.000000"; video_driver = "vulkan"; video_filter = ""
            configs = [(setting.strip(), value.strip()) for setting, value in [line.split('=') for line in configs]]
            with open(retroarch_cfg, 'w+') as new_retroarch_cfg:
                for setting, value in configs:
                    new_retroarch_cfg.write(f'{setting} = {value}\n')
            new_retroarch_cfg.close()

    if path == '':
        return set_emuls_root(default_path)
    elif not exists(path):
        check_button(f'"{realpath(path)}" does not exists. Would you like to crate it?', 'Error in set_emuls_root()')
        try:
            makedirs(default_path)
        except:
            raise SystemExit
        return set_emuls_root(path, default_path)
    else:
        check_retroarch(join(path, "RetroArch\\retroarch.exe").lower())
        return path


def set_roms_root(path, default_path='..\\ROMS'):
    if path == '':
        return set_roms_root(default_path)
    elif not exists(path):
        check_button(f'"{realpath(path)}" does not exists. Would you like to crate it?', 'Error in set_roms_root()')
        try:
            makedirs(default_path)
        except:
            alert(f'Could\'nt crate Roms dir at location "{path}"', 'Error in set_roms_root()')
            raise SystemExit
        return set_roms_root(path, default_path)
    else:
        return path


def check_7zip(path, temp_dir='7zip_files'):
    if not exists(join(path, '7za.exe')):
        temp_dir_path = join(path, temp_dir)
        if exists(temp_dir_path):  # Cleaning lefovers if exists
            rmtree(temp_dir_path)
        file_path_1 = download_binary_r('https://www.7-zip.org/a/7za920.zip')  # ZIP file can be unpacked by pyunpack
        file_path_2 = download_binary_r('https://www.7-zip.org/a/7z1900-extra.7z')  # 7z file need 7za.exe to unpack
        from pyunpack import Archive
        archive = Archive(file_path_1)
        archive.extractall_zipfile(temp_dir_path)
        f7za_files = [file.path for file in scandir(temp_dir_path) if file.name.lower() == '7za.exe']
        move(f7za_files[0], join(path, '7za.exe'))
        rmtree(temp_dir_path)
        remove(file_path_1)
        sp.run(f'7za.exe x "{file_path_2}" -o"{temp_dir_path}" -y', startupinfo=alt_startupinfo)  # Using 7zip command line
        f7za_files = [file.path for file in scandir(temp_dir_path) if file.name.lower() == '7za.exe' or
                      file.name.lower() == '7za.dll' or file.name.lower() == '7zxa.dll']
        for file in f7za_files:
            filename = file[file.rfind('\\') + 1:]
            move(file, join(path, filename))  # overwrite current outdated version of 7za.exe on the same location
        rmtree(temp_dir_path)
        remove(file_path_2)
        check_7zip(path)  # check again if 7za.exe is now found


def check_es_files(path):
    if isfile(path):
        return path
    else:
        check_button(f'emulationstation.exe file not found on "{path}". It will be downloaded now from '
                     'Fabricecaruso github "https://github.com/fabricecaruso". All Credits goes to him.',
                     'emulationstation.exe not found!')
        file_path = download_binary_r('https://github.com/fabricecaruso/batocera-emulationstation/releases/download/'
                                      'continuous-beta/EmulationStation-Win32.zip')
        extract_contents2(file_path, dirname(path))
        return check_es_files(path)


def check_es_maindir(path):
    if isdir(path):
        return path
    else:
        check_button(f'Main ES subdirectory ".emulationstation" not found here:\n"{path}"\n'
                     f'Would you like to create it?', title='ES Subdirectory ERROR!')
        makedirs(path)
        return check_es_maindir(path)  # check again if it now exists


def check_splashs_setup(path):
    def checkfiles(dir_path_in, v_ext_list=['.mp4', '.m4v', '.mkv', '.flv', '.avi', '.wmv', '.vob', '.mpg', '.mpeg']):
        videoflist = [i for i in scandir_recursivelly(dir_path_in)[1] for v_ext in v_ext_list if splitext(i)[1] == v_ext]
        if len(videoflist) > 0:
            return True
        else:
            return False

    if isdir(path):
        if checkfiles(path):
            return path
        else:
            check_button(f'No video file found inside {path}. Download a sample video from BATOCERA Team?')
            # file_path = download_binary_r('https://github.com/ehettervik/retropie-splash-videos/archive/master.zip')
            # extract_contents2(file_path, path)
            urls = """https://batocera.org/videos/boot/Batocera%20%23Skull%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%205.24%20Officiel%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20ACTION%2080_S%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Arcade%20Machine%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20ARCADE%20PUNK%20WARS%20%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Back%20to%20Game%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20BLUE%20GPU%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/Batocera%20Bulles%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Bumper%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20CARTON%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Cinema%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20CLUB%20Slash%20Screen%20officiel%20.mp4
            https://batocera.org/videos/boot/Batocera%20Comic%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Comic%20Games%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Cubic%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20CubiX%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20DBZ%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20DBZ%20SHORT%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20DC%20COMIC%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Digital%20%2301%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Digital%20%2302%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Digital%20%2303%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Digital%20%2304%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Digital%20%2305%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Dirty%20Smoke%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20DUBSTEP%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20EDM%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Epic%20Fantasy%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20ERROR%20DAMAGE%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/Batocera%20Fighters%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20GALLERY%20STATION%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20GAMING%20PAD%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20GEOMETRIC%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20GOLD%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Hight%20Tech%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20HUB%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20IMAGINE%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20JETONS%20GAMES%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Led%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Level%20UP%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20LUXURY%20METAL%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Marvellous%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20MATRIX%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Merry%20Christmass%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Minecraft%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/Batocera%20MiniCakeTv%20Anniversary%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20MONSTER%20MATRIX%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20MULTI%20GAMES%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20NIGHT%20CITY%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Old%20TV%2080_S%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Pac%20Man%20(40th%20Anniversary)%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Panth%c3%a8re%20Noir%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Particules%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20PINK%20GPU%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Room%20Digital%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20SHORT%20TRIANGULAR%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20SKY%20SIGNAL%20BATMAN%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20SPACE%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Space%20Distortion%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Speed%20Energy%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Stadium%202%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Stadium%20by%20Snakervill%20.mp4
            https://batocera.org/videos/boot/BATOCERA%20Star%20Wars%20bySnakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20STEAMPUNK%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Storm%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Symphonie%20Wars%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20TECHNO%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Techno%20Cube%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20The%20Rock%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20THINGS%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2301%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2302%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2303%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2304%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2305%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2306%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2307%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2308%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2309%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tiitre%20%2310%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Tron%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20UFO%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%201%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%202%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%203%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%204%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%205%20by%20Snakervillmp4.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%206%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%207%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%208%20by%20Snakervillmp4.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%209%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BAtocera%20VINTAGE%2010%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20VORTEX%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Wave%20Retro%2001%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Wave%20Retro%2002%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Wave%20Retro%2003%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20WAVE%20RETRO%203D%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Wave%20Retro%2004%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Wave%20Retro%2005%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Wave%20Retro%2006%20by%20Snakervill.mp4
            https://batocera.org/videos/boot/BATOCERA%20Wish%20by%20Snakervill.mp4"""
            splash_urls = urls.split('\n')
            file_path = download_binary_r(
                "https://batocera.org/videos/boot/BATOCERA%20GALLERY%20STATION%20by%20Snakervill.mp4")
            move(file_path, join(path, file_path[file_path.rfind('\\') + 1:]).replace('%20', ' '))
            return check_splashs_setup(path)
    else:
        check_button(f'Splashs videos directory not found on "{path}". It will be create now')
        makedirs(path)
        return check_splashs_setup(path)


def check_vlc_setup(vlc_path_in):
    vlc_dir = dirname(vlc_path_in)
    if isfile(vlc_path_in):
        if not exists(join(vlc_dir, 'plugins\\plugins.dat')):
            sp.run(f'"{join(vlc_dir, "vlc-cache-gen.exe")}" plugins', startupinfo=alt_startupinfo)
        return vlc_path_in
    else:
        check_button(f'VLC files not found on "{vlc_path_in}"! Will be downloaded now. All credits goes to '
                     f'VLC devs team.')
        # file_path = download_binary_r('https://get.videolan.org/vlc/3.0.16/win32/vlc-3.0.16-win32.zip')
        file_path = download_binary_r('https://artifacts.videolan.org/vlc/nightly-win64-llvm/20210723-0425/vlc-4.0.0-dev-win64-832b8519.7z')
        extract_contents2(file_path, dirname(vlc_path_in))
        if not exists(join(vlc_dir, 'plugins\\plugins.dat')):
            sp.run(f'"{join(vlc_dir, "vlc-cache-gen.exe")}" plugins', startupinfo=alt_startupinfo)
        return check_vlc_setup(vlc_path_in)


def check_themes_setup(path, settings_cfg_file_in):
    if not isdir(path):
        check_button(f'Themes directory not found on "{path}". It will be created now')
        makedirs(path)
        return check_themes_setup(path, settings_cfg_file_in)
    elif len([item.name for item in scandir(path) if item.is_dir]) == 0:
        check_button(f'"{path}" is empty. It will be populated with RVGM-BT-Theme from the author Darknior '
                     f'"https://github.com/Darknior/". All credits goes to him.')
        file_path = download_binary_r('https://github.com/Darknior/RVGM-BT-Theme/archive/refs/tags/1.96.zip')
        extract_contents2(file_path, join(path, 'RVGM-BT-Theme'))
        return check_themes_setup(path, settings_cfg_file_in)
    else:
        return path


def randomize_themes(path, settings_cfg_file_in):
    from random import randint
    themes_list = [item.name for item in scandir(path) if item.is_dir]
    replace_line(settings_cfg_file_in, '"ThemeSet" value=',
                 f'    <string name="ThemeSet" value="{themes_list[randint(0, len(themes_list) - 1)]}" />')


def setdisplaysolution(resolution):
    import pywintypes
    if len(resolution) > 2:
        display_modes = {}
        n = 0
        while True:
            try:
                devmode = win32api.EnumDisplaySettings(None, n)
            except pywintypes.error:
                break
            else:
                key = (devmode.BitsPerPel, devmode.PelsWidth, devmode.PelsHeight, devmode.DisplayFrequency)
                display_modes[key] = devmode
                n += 1

        # for item in display_modes.items():
        #     print(item)

        mode_required = (32, int(resolution[0]), int(resolution[1]), int(resolution[2]))
        devmode = display_modes[mode_required]
        try:
            win32api.ChangeDisplaySettings(devmode, 0)
        except 'KeyError':
            alert('setdisplayresolution error!')
            raise SystemExit


def log_print(str_in, is_header=False, logfile='log.txt', mode=0, nchars=120, char=' '):
    # from datetime import datetime as dt
    if not isinstance(str_in, str):
        str_in = str(str_in)
    if '\n' in str_in:
        str_in = str_in.splitlines()

    if mode == 0 or mode == 2:
        if is_header:
            if isinstance(str_in, list):
                print(f"{char * nchars}")
                for line in str_in:
                    print(f"{line.center(nchars, char)}")
                print(f"{char * nchars}")
            else:
                print(f"{char * nchars}\n{str_in.center(nchars, char)}\n{char * nchars}")
        else:
            if isinstance(str_in, list):
                for line in str_in:
                    print(f"{dt.now().strftime('%H:%M:%S')}| {line}")
            else:
                print(f"{dt.now().strftime('%H:%M:%S')}| {str_in}")

    if 0 <= mode < 2:
        with open(logfile, 'a+') as log_txt:
            if is_header:
                if isinstance(str_in, list):
                    log_txt.write(f"{char * nchars}\n")
                    for line in str_in:
                        log_txt.write(f"{line.center(nchars, char)}\n")
                    log_txt.write(f"{char * nchars}\n")
                else:
                    log_txt.write(f"{char * nchars}\n{str_in.center(nchars, char)}\n{char * nchars}\n")
            else:
                if isinstance(str_in, list):
                    for line in str_in:
                        log_txt.write(f"{dt.now().strftime('%H:%M:%S')}| {line}\n")
                else:
                    log_txt.write(f"{dt.now().strftime('%H:%M:%S')}| {str_in}\n")
        log_txt.close()


def new_getcwd():
    if getattr(sys, 'frozen', False):
        return dirname(sys.executable)  # if converted to executable this will be used
    elif __file__:
        return dirname(__file__)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


# ---------------------------------------Execution Pipeline-------------------------------------------------------------
if is_admin():  # Re-run the program with admin rights | Note that this trick uses the first argument of sys.argv
    chdir(new_getcwd())  # it is necessary when loading from another location like as Winlogon Explorer Shell option
    # ---------------Global Vars--------------------------
    silent = False  # Global var
    alt_startupinfo = new_startupinfo(window_hidden=True)
    # ------------------ Main Function ------------------
    main()
else:           # Use sys.argv[1:] (ignore first element) if you plan to convert to .exe else sys.argv only.
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
raise SystemExit
