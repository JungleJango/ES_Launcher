# ----------------------------------------Importing Modules-------------------------------------------------------------
import ctypes
import sys
import requests
import time
import win32gui
import win32con  # used to maximize minimize window
import win32process
import win32api
import subprocess as sp
from os import remove, environ, chdir, getcwd, scandir, makedirs, mkdir
from os.path import exists, isdir, isfile, join, splitext, dirname, relpath
from shutil import rmtree, move
from pymsgbox import alert, confirm
from psutil import pid_exists, Process
from datetime import datetime as dt
from playsound import playsound


# ----------------------------------------Main Function-----------------------------------------------------------------
def main():
    es_dir, emuls_root, roms_root, settings_cfg_file, startup_dir, intro_file, splashs_root, vlcargs, es_args,\
        kill_exp, random_theme, ex_fullscreen, assync_load, play_vlc_embedded, play, hide_es_while_assync_load,\
        boot_videos, resolution, current_process_hwnds = check_ini_and_args()
    # choose_env_var_or_base_var('ESdir')
    environ['ESdir'] = es_dir
    chdir(es_dir)
    es_maindir = check_es_maindir(join(es_dir, '.emulationstation'))
    es_path = check_emustation_setup(join(es_dir, 'emulationstation.exe'))
    settings_cfg_file = es_cfg_files(es_maindir, emuls_root, roms_root)
    emuls_root = set_emuls_root(emuls_root, '..\\EMULATORS')  # If in the same partition volume can be used relative paths to es.exe
    roms_root = set_roms_root(roms_root, '..\\ROMS')         #
    check_7zip(es_dir)
    check_themes_setup(join(es_maindir, 'themes'), settings_cfg_file, random_theme)
    if len(resolution) > 2:
        try:
            setdisplaysolution(resolution[0], resolution[1], resolution[2])
        except:
            alert('Resolution not supported or driver issues')
            raise SystemExit
    if kill_exp:        # KILLS EXPLORER PROCESS
        sp.call('TASKKILL /F /IM explorer.exe', startupinfo=new_startupinfo(window_hidden=True))
    if play:
        intro_file = join(es_dir, 'intro.mp4')
        startup_dir = join(es_dir, 'startup_videos')
        splashs_dir = check_splashs_setup(join(es_dir, 'splashs'))
        vlc_path = check_vlc_setup(join(es_dir, 'vlc\\vlc.exe'))
        if not ex_fullscreen:
            if '--windowed' not in es_args: es_args += ' --windowed'
            if '--fullscreen-borderless' not in es_args: es_args += ' --fullscreen-borderless'
        if assync_load:  # Loads ES in background while playing video in foregrounds
            if play_vlc_embedded:
                emustation = NewPopen(es_path + es_args)
                emustation.SetMute(True)
                startup_videos(vlc_path, intro_file, startup_dir, splashs_dir, boot_videos,
                               play_vlc_embedded, emustation.get_first_hwnd_from_pid())
                emustation.bring_window_on_top()
                emustation.SetMute(False)
                play_menu_sound('menu.wav')
                if kill_exp:   # RESTARTS EXPLORER PROCESS
                    emustation.wait()
                    sp.call('explorer.exe')
            else:
                vlcplaying = startup_videos(vlc_path, intro_file, startup_dir, splashs_dir, splashs_dir, boot_videos)
                # new_startupinfo() function sets startupinfo to hide ES if hide_es_while_assync_load is set true
                emustation = NewPopen(es_path + es_args, startupinfo=new_startupinfo(hide_es_while_assync_load))
                emustation.SetMute(True)
                vlcplaying.bring_window_on_top(once=False)
                emustation.SetMute(False)
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
    else:
        emustation = NewPopen(es_path + es_args)
        emustation.bring_window_on_top()
        if kill_exp:
            emustation.wait()
            sp.call('explorer.exe')


# ----------------------------------------------------------------------------------------------------------------------
def play_menu_sound(audio_file):
    if exists(audio_file):
        playsound(audio_file)


def new_startupinfo(window_hidden=False):
    import subprocess
    # Makes a copy of startupinfo function used to create window at program startup
    startupinfo = subprocess.STARTUPINFO()
    if window_hidden:
        # Change window creation parameter dwFlags value based on subprocess module SARTF_USESHOWWINDOW parameter
        startupinfo.dwFlags = startupinfo.dwFlags | subprocess.STARTF_USESHOWWINDOW
    return startupinfo  # Returns a new modified version of the entire STARTUPINFO() function that hides window
    # If you wish use win32gui.ShowWindow(hwnd, win32con.SW_SHOW) make it visible later on

    # Alternative version of the code
    # si = sp.STARTUPINFO()
    # si.dwFlags |= sp.STARTF_USESHOWWINDOW
    # si.wShowWindow = sp.SW_HIDE
    # return si


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
                break
        hwnd, hwnd_thread_id = hwnds[0]
        while pid_exists(self.pid):
            try:
                win32process.AttachThreadInput(script_pid, hwnd_thread_id, True)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SetFocus(hwnd)
                if once: break
            except:
                continue

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

    def SetMute(self, true_or_false):
        if true_or_false:
            self.get_audio_session().SetMute(1, None)
        else:
            self.get_audio_session().SetMute(0, None)


def choose_env_var_or_base_var(env_var):
    if getattr(sys, 'frozen', False):
        return dirname(sys.executable)
    elif __file__:
        return dirname(__file__)
    # if isdir(es_dir):
    #     environ[env_var] = es_dir
    # elif es_dir == '':
    #     var_path = environ.get(env_var)
    #     if var_path is None:
    #         environ[env_var] = es_dir = getcwd()  # Setting environment variable
    #     elif isdir(var_path):
    #         es_dir = var_path
    #     else:
    #         check_button(f'Environment Variable "ESdir" points to an invalid path. The current location '
    #                      f'{getcwd()} will be used instead.')
    #         if getattr(sys, 'frozen', False):
    #             environ[env_var] = es_dir = dirname(sys.executable)
    #         elif __file__:
    #             environ[env_var] = es_dir = dirname(__file__)
    #         choose_env_var_or_base_var(env_var)
    # else:
    #     button = check_button(f'"{es_dir}" is an invalid path for an EmulationStation directory. Check "es_dir=" entry'
    #                            'in "es_launcher.ini" file or "--es=" argument value.\nWould you like to try to create it?'
    #                            'or rather use the current directory as ES root?', title='Invalid es_dir value!',
    #                            buttons=['Yes, create it', 'Use Current Dir', 'Cancel'])
    #     if button == 'Yes, create it':
    #         makedirs(es_dir)
    #         choose_env_var_or_base_var(es_dir)
    #     elif button == 'Use Current Dir':
    #         es_dir = ''
    #         choose_env_var_or_base_var(es_dir)


def scanrecurse(basedir):
    file_list = []
    for f in scandir(basedir):
        if f.is_dir():
            file_list.extend(scanrecurse(f.path))
        else:
            file_list.append(f.path)
    return file_list


def startup_videos(vlc_path, intro_file, startup_dir, splashs_dir, boot_videos, play_vlc_embedded=False, hwnd2drawon=0):
    vlcargs = ' --fullscreen --qt-fullscreen-screennumber=1 --video-on-top --no-video-title-show --no-video-deco' \
              ' --ignore-config --reset-config --reset-plugins-cache --one-instance --play-and-exit --high-priority' \
              ' -Idummy --no-mouse-events --mouse-hide-timeout=1'
    if play_vlc_embedded:
        vlcargs += ' --drawable-hwnd=' + str(hwnd2drawon)

    def play_on_vlc(vlc_path, vlcargs, videofiles_dir):
        def pickafile(dir_path_in, v_ext_list=[]):
            if len(v_ext_list) < 1:
                v_ext_list = ['.mp4', '.m4v', '.mkv', '.flv', '.avi', '.wmv', '.vob', '.mpg', '.mpeg']
            from random import randint
            videoflist = [i for i in scanrecurse(dir_path_in) for v_ext in v_ext_list if splitext(i)[1] == v_ext]
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
        <inputConfig type="keyboard" deviceName="Keyboard" deviceGUID="-1">
            <input name="a" type="key" id="13" value="1" />
            <input name="b" type="key" id="27" value="1" />
            <input name="down" type="key" id="1073741905" value="1" />
            <input name="hotkeyenable" type="key" id="1073742049" value="1" />
            <input name="left" type="key" id="1073741904" value="1" />
            <input name="leftanalogdown" type="key" id="1073741914" value="1" />
            <input name="leftanalogleft" type="key" id="1073741913" value="1" />
            <input name="leftanalogright" type="key" id="1073741915" value="1" />
            <input name="leftanalogup" type="key" id="1073741917" value="1" />
            <input name="pageup" type="key" id="51" value="1" />
            <input name="leftthumb" type="key" id="55" value="1" />
            <input name="lefttrigger" type="key" id="53" value="1" />
            <input name="right" type="key" id="1073741903" value="1" />
            <input name="rightanalogdown" type="key" id="107" value="1" />
            <input name="rightanalogleft" type="key" id="106" value="1" />
            <input name="rightanalogright" type="key" id="108" value="1" />
            <input name="rightanalogup" type="key" id="105" value="1" />
            <input name="rightshoulder" type="key" id="52" value="1" />
            <input name="rightthumb" type="key" id="56" value="1" />
            <input name="pagedown" type="key" id="54" value="1" />
            <input name="select" type="key" id="9" value="1" />
            <input name="start" type="key" id="1073741898" value="1" />
            <input name="up" type="key" id="1073741906" value="1" />
            <input name="x" type="key" id="49" value="1" />
            <input name="y" type="key" id="50" value="1" />
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
    </inputList>
    ''')
        file.close()

    def es_systems_cfg(es_maindir, emuls_root, roms_root):
        check_button(f'{es_maindir}\\es_systems.cfg \n This file will be generated now.', title='File not found!')
        with open(es_maindir + '\\es_systems.cfg', 'w+') as file:
            file.write(f'''<systemList>
    	<system>
    		<name>fba</name>
    		<fullname>Final Burn Alpha</fullname>
    		<path>{roms_root}\\fba</path>
    		<extension>.fba .zip .FBA .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fbneo_libretro.dll "%ROM_RAW%"</command>
    		<platform>arcade</platform>
    		<theme>fba</theme>
    	</system>
    	<system>
    		<name>neogeo</name>
    		<fullname>Neo Geo</fullname>
    		<path>{roms_root}\\neogeo</path>
    		<extension>.zip .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fbneo_libretro.dll "%ROM_RAW%"</command>
    		<platform>neogeo</platform>
    		<theme>neogeo</theme>
    	</system>
    	<system>
    		<name>neogeoh</name>
    		<fullname>Neo Geo Hacks</fullname>
    		<path>{roms_root}\\neogeoh</path>
    		<extension>.7z .zip .7Z .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fbneo_libretro.dll "%ROM_RAW%"</command>
    		<platform>neogeo</platform>
    		<theme>neogeo</theme>
    	</system>
    	<system>
    		<name>arcade</name>
    		<fullname>Arcade</fullname>
    		<path>{roms_root}\\arcade</path>
    		<extension>.7z .zip .7Z .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fbneo_libretro.dll "%ROM_RAW%"</command>
    		<platform>arcade</platform>
    		<theme>arcade</theme>
    	</system>
    	<system>
    		<name>mame2003</name>
    		<fullname>mame2003</fullname>
    		<path>{roms_root}\\mame2003</path>
    		<extension>.zip .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mame2003_plus_libretro.dll "%ROM_RAW%"</command>
    		<platform>arcade</platform>
    		<theme>mame</theme>
    	</system>
    	<system>
    		<name>mame</name>
    		<fullname>MAME</fullname>
    		<path>{roms_root}\\mame</path>
    		<extension>.zip .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mame_libretro.dll "%ROM_RAW%"</command>
    		<platform>arcade</platform>
    		<theme>mame</theme>
    	</system>
    	<system>
    		<name>model2</name>
    		<fullname>Sega Model 2</fullname>
    		<path>{roms_root}\\model2</path>
    		<extension>.zip .7z .7Z .ZIP</extension>
    		<command>{emuls_root}\\model2\\emulator.exe "%ROM_RAW%"</command>
    		<platform>arcade</platform>
    		<theme>mame</theme>
    	</system>
    	<system>
    		<name>model3</name>
    		<fullname>Sega Model 3</fullname>
    		<path>{roms_root}\\model3</path>
    		<extension>.zip .7z .7Z .ZIP</extension>
    		<command>{emuls_root}\\supermodel3\\supermodel.exe -res=1920x1080 -fullscreen "%ROM_RAW%"</command>
    		<platform>arcade</platform>
    		<theme>mame</theme>
    	</system>
    	<system>
    		<name>daphne</name>
    		<fullname>Daphne</fullname>
    		<path>{roms_root}\\daphne</path>
    		<extension>.daphne .sna .szx .z80 .tap .tzx .gz .udi .mgt .img .trd .scl .dsk .zip .SNA .SZX .Z80 .TAP .TZX .GZ .UDI .MGT .IMG .TRD .SCL .ZIP .DSK</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\daphne_libretro.dll "%ROM_RAW%"</command>
    		<platform>daphne</platform>
    		<theme>daphne</theme>
    	</system>
    	<system>
    		<name>astrocade</name>
    		<fullname>Astrocade</fullname>
    		<path>{roms_root}\\Astrocade</path>
    		<extension>.wsc .zip .WSC .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mess2015_libretro.dll "%ROM_RAW%"</command>
    		<platform>Astrocade</platform>
    		<theme>astrocade</theme>
    	</system>
    	<system>
    		<name>pcengine</name>
    		<fullname>TurboGrafx 16 (PC Engine)</fullname>
    		<path>{roms_root}\\pcengine</path>
    		<extension>.cue .pce .zip .CUE .PCE .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mednafen_pce_fast_libretro.dll "%ROM_RAW%"</command>
    		<platform>pcengine</platform>
    		<theme>pcengine</theme>
    	</system>
    	<system>
    		<name>pcfx</name>
    		<fullname>PC-FX</fullname>
    		<path>{roms_root}\\supergrafx</path>
    		<extension>.cue .zip .CUE .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mednafen_pcfx_libretro.dll "%ROM_RAW%"</command>
    		<platform>pcfx</platform>
    		<theme>pcfx</theme>
    	</system>
    	<system>
    		<name>openbor</name>
    		<fullname>OpenBOR</fullname>
    		<path>{roms_root}\\openbor</path>
    		<extension>.cue .zip .pak .CUE .ZIP .PAK</extension>
    		<command></command>
    		<platform>openbor</platform>
    		<theme>openbor</theme>
    	</system>
    	<system>
    		<name>mugem</name>
    		<fullname>MuGeM</fullname>
    		<path>{roms_root}\\mugem</path>
    		<extension>.exe .EXE</extension>
    		<command></command>
    		<platform>mugem</platform>
    		<theme>mugem</theme>
    	</system>
    	<system>
    		<name>naomi</name>
    		<fullname>Naomi</fullname>
    		<path>{roms_root}\\naomi</path>
    		<extension>.7z .cue .zip .7Z .CUE .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mednafen_pcfx_libretro.dll "%ROM_RAW%"</command>
    		<platform>naomi</platform>
    		<theme>naomi</theme>
    	</system>
    	<system>
    		<name>atari800</name>
    		<fullname>Atari 800</fullname>
    		<path>{roms_root}\\atari800</path>
    		<extension>.7z .ZIP .a26 .bin .rom .7Z .ZIP .A26 .BIN .ROM</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\stella_libretro.dll "%ROM_RAW%"</command>
    		<platform>atari800</platform>
    		<theme>atari800</theme>
    	</system>
    	<system>
    		<name>atari2600</name>
    		<fullname>Atari 2600</fullname>
    		<path>{roms_root}\\atari2600</path>
    		<extension>.7z .zip .a26 .bin .rom .7Z .ZIP .A26 .BIN .ROM</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\stella_libretro.dll "%ROM_RAW%"</command>
    		<platform>atari2600</platform>
    		<theme>atari2600</theme>
    	</system>
    	<system>
    		<name>atari5200</name>
    		<fullname>Atari 5200</fullname>
    		<path>{roms_root}\\atari5200</path>
    		<extension>.7z .zip .a26 .bin .rom .7Z .ZIP .A26 .BIN .ROM</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\stella_libretro.dll "%ROM_RAW%"</command>
    		<platform>atari5200</platform>
    		<theme>atari5200</theme>
    	</system>
    	<system>
    		<name>atari7800</name>
    		<fullname>Atari 7800 Prosystem</fullname>
    		<path>{roms_root}\\atari7800</path>
    		<extension>.7z .zip .a78 .bin .7Z .ZIP .A78 .BIN</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\prosystem_libretro.dll "%ROM_RAW%"</command>
    		<platform>atari7800</platform>
    		<theme>atari7800</theme>
    	</system>
    	<system>
    		<name>atarijaguar</name>
    		<fullname>Atari Jaguar</fullname>
    		<path>{roms_root}\\atarijaguar</path>
    		<extension>.7z .zip .j64 .jag .7Z .ZIP .J64 .JAG</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\virtualjaguar_libretro.dll "%ROM_RAW%"</command>
    		<platform>atarijaguar</platform>
    		<theme>atarijaguar</theme>
    	</system>
    	<system>
    		<name>atarist</name>
    		<fullname>Atari ST, STE, Falcon</fullname>
    		<path>{roms_root}\\atarist</path>
    		<extension>.7z .zip .img .rom .st .stx .IMG .ROM .ST .STX .7Z .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\hatari_libretro.dll "%ROM_RAW%"</command>
    		<platform>atarist</platform>
    		<theme>atarist</theme>
    	</system>
    	<system>
    		<name>gb</name>
    		<fullname>Game Boy</fullname>
    		<path>{roms_root}\\gb</path>
    		<extension>.gb .zip .GB .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\gambatte_libretro.dll "%ROM_RAW%"</command>
    		<platform>gb</platform>
    		<theme>gb</theme>
    	</system>
    	<system>
    		<name>gbh</name>
    		<fullname>Game Boy Hacks</fullname>
    		<path>{roms_root}\\gbh</path>
    		<extension>.7z .gbc .GBC .zip .7Z .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\gambatte_libretro.dll "%ROM_RAW%"</command>
    		<platform>gb</platform>
    		<theme>gb</theme>
    	</system>
    	<system>
    		<name>gbc</name>
    		<fullname>Game Boy Color</fullname>
    		<path>{roms_root}\\gbc</path>
    		<extension>.gbc .GBC .zip .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\gambatte_libretro.dll "%ROM_RAW%"</command>
    		<platform>gbc</platform>
    		<theme>gbc</theme>
    	</system>
    	<system>
    		<name>gba</name>
    		<fullname>Game Boy Advance</fullname>
    		<path>{roms_root}\\gba</path>
    		<extension>.gba .zip .GBA .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mgba_libretro.dll "%ROM_RAW%"</command>
    		<platform>gba</platform>
    		<theme>gba</theme>
    	</system>
    	<system>
    		<name>gbah</name>
    		<fullname>GBA Hacks</fullname>
    		<path>{roms_root}\\gba</path>
    		<extension>.7Z .gba .zip .7Z .GBA .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mgba_libretro.dll "%ROM_RAW%"</command>
    		<platform>gba</platform>
    		<theme>gba</theme>
    	</system>
    	<system>
    		<name>nds</name>
    		<fullname>Nintendo DS</fullname>
    		<path>{roms_root}\\nds</path>
    		<extension>.nds .zip .NDS .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\desmume_libretro.dll "%ROM_RAW%"</command>
    		<platform>nds</platform>
    		<theme>nds</theme>
    	</system>
    	<system>
    		<name>3ds</name>
    		<fullname>Nintendo 3DS</fullname>
    		<path>{roms_root}\\3ds</path>
    		<extension>.3ds .cia .3DS .CIA</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\citra_libretro.dll "%ROM_RAW%"</command>
    		<platform>3ds</platform>
    		<theme>3ds</theme>
    	</system>
    	<system>
    		<name>gamegear</name>
    		<fullname>Sega Gamegear</fullname>
    		<path>{roms_root}\\gamegear</path>
    		<extension>.7z .bin .gg .zip .7Z .BIN .GG .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\genesis_plus_gx_libretro.dll "%ROM_RAW%"</command>
    		<platform>gamegear</platform>
    		<theme>gamegear</theme>
    	</system>
    	<system>
    		<name>gamegearh</name>
    		<fullname>Sega Gamegear Hacks</fullname>
    		<path>{roms_root}\\ggh</path>
    		<extension>.7z .bin .gg .zip .7Z .BIN .GG .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\genesis_plus_gx_libretro.dll "%ROM_RAW%"</command>
    		<platform>gamegear</platform>
    		<theme>gamegear</theme>
    	</system>
    	<system>
    		<name>atarilynx</name>
    		<fullname>Atari Lynx</fullname>
    		<path>{roms_root}\\atarilynx</path>
    		<extension>.7z .zip .lnx .LNX .7Z .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\handy_libretro.dll "%ROM_RAW%"</command>
    		<platform>atarilynx</platform>
    		<theme>atarilynx</theme>
    	</system>
    	<system>
    		<name>ngp</name>
    		<fullname>Neo Geo Pocket</fullname>
    		<path>{roms_root}\\ngp</path>
    		<extension>.ngp .ngc .zip .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mednafen_ngp_libretro.dll "%ROM_RAW%"</command>
    		<platform>ngp</platform>
    		<theme>ngp</theme>
    	</system>
    	<system>
    		<name>ngpc</name>
    		<fullname>Neo Geo Pocket Color</fullname>
    		<path>{roms_root}\\ngpc</path>
    		<extension>.ngc .zip .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mednafen_ngp_libretro.dll "%ROM_RAW%"</command>
    		<platform>ngpc</platform>
    		<theme>ngpc</theme>
    	</system>
    	<system>
    		<name>gw</name>
    		<fullname>Game and Watch</fullname>
    		<path>{roms_root}\\gw</path>
    		<extension>.mgw .MGW .zip .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\gw_libretro.dll "%ROM_RAW%"</command>
    		<platform>gw</platform>
    		<theme>gw</theme>
    	</system>
    	<system>
    		<name>love</name>
    		<fullname>Love</fullname>
    		<path>{roms_root}\\love</path>
    		<extension>.love .LOVE</extension>
    		<command>{emuls_root}\\love\\love.exe "%ROM_RAW%"</command>
    		<platform>love</platform>
    		<theme>love</theme>
    	</system>
    	<system>
    		<name>sg-1000</name>
    		<fullname>Sega SG-1000</fullname>
    		<path>{roms_root}\\sg-1000</path>
    		<extension>.bin .sg .zip .BIN .SG .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\genesis_plus_gx_libretro.dll "%ROM_RAW%"</command>
    		<platform>sg-1000</platform>
    		<theme>sg-1000</theme>
    	</system>
    	<system>
    		<name>mastersystem</name>
    		<fullname>Sega Master System</fullname>
    		<path>{roms_root}\\mastersystem</path>
    		<extension>.bin .sms .zip .BIN .SMS .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\genesis_plus_gx_libretro.dll "%ROM_RAW%"</command>
    		<platform>mastersystem</platform>
    		<theme>mastersystem</theme>
    	</system>
    	<system>
    		<name>megadrive</name>
    		<fullname>Sega Mega Drive</fullname>
    		<path>{roms_root}\\megadrive</path>
    		<extension>.bin .gen .md .sg .smd .zip .BIN .GEN .MD .SG .SMD .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\genesis_plus_gx_libretro.dll "%ROM_RAW%"</command>
    		<platform>megadrive</platform>
    		<theme>megadrive</theme>
    	</system>
    	<system>
    		<name>genesis</name>
    		<fullname>Sega Genesis</fullname>
    		<path>{roms_root}\\genesis</path>
    		<extension>.bin .gen .md .sg .smd .zip .BIN .GEN .MD .SG .SMD .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\genesis_plus_gx_libretro.dll "%ROM_RAW%"</command>
    		<platform>genesis</platform>
    		<theme>genesis</theme>
    	</system>
    	<system>
    		<name>genh</name>
    		<fullname>Sega Genesis Hacks</fullname>
    		<path>{roms_root}\\genh</path>
    		<extension>.7z .bin .gen .md .sg .smd .zip .7Z .BIN .GEN .MD .SG .SMD .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\genesis_plus_gx_libretro.dll "%ROM_RAW%"</command>
    		<platform>genesis</platform>
    		<theme>genesis</theme>
    	</system>
    	<system>
    		<name>sega32x</name>
    		<fullname>Sega 32x</fullname>
    		<path>{roms_root}\\sega32x</path>
    		<extension>.32x .bin .md .smd .zip .32X .BIN .MD .SMD .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\genesis_plus_gx_libretro.dll "%ROM_RAW%"</command>
    		<platform>sega32x</platform>
    		<theme>sega32x</theme>
    	</system>
    	<system>
    		<name>segacd</name>
    		<fullname>Sega CD</fullname>
    		<path>{roms_root}\\segacd</path>
    		<extension>.iso .cue .chd .ISO .CUE .CHD</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\genesis_plus_gx_libretro.dll "%ROM_RAW%"</command>
    		<platform>segacd</platform>
    		<theme>segacd</theme>
    	</system>
    	<system>
    		<name>saturn</name>
    		<fullname>Sega Saturn</fullname>
    		<path>{roms_root}\\saturn</path>
    		<extension>.bin .iso .zip .mds .BIN .ISO .MDF .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\kronos_libretro.dll "%ROM_RAW%"</command>
    		<platform>saturn</platform>
    		<theme>saturn</theme>
    	</system>
    	<system>
    		<name>Dreamcast</name>
    		<fullname>Sega Dreamcast</fullname>
    		<path>{roms_root}\\dreamcast</path>
    		<extension>.chd .bin .cdi .cue .gdi .mdf .mds .BIN .CDI .CUE .GDI .MDF .MDS .CHD</extension>
    		<command>{emuls_root}\\redream\\redream.exe "%ROM_RAW%"</command>
    		<platform>dreamcast</platform>
    		<theme>dreamcast</theme>
    	</system>
    	<system>
    		<name>3do</name>
    		<fullname>3do</fullname>
    		<path>{roms_root}\\3do</path>
    		<extension>.iso .zip .chd .ISO .ZIP .CHD</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\4do_libretro.dll "%ROM_RAW%"</command>
    		<platform>3do</platform>
    		<theme>3do</theme>
    	</system>
    	<system>
    		<name>nes</name>
    		<fullname>Nintendo Entertainment System</fullname>
    		<path>{roms_root}\\nes</path>
    		<extension>.7z .nes .zip .7Z .NES .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\nestopia_libretro.dll "%ROM_RAW%"</command>
    		<platform>nes</platform>
    		<theme>nes</theme>
    	</system>
    	<system>
    		<name>nesh</name>
    		<fullname>NES Hacks</fullname>
    		<path>{roms_root}\\nesh</path>
    		<extension>.7z .nes .zip .7Z .NES .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\nestopia_libretro.dll "%ROM_RAW%"</command>
    		<platform>nes</platform>
    		<theme>nes</theme>
    	</system>
    	<system>
    		<name>fds</name>
    		<fullname>Famicom Disk System</fullname>
    		<path>{roms_root}\\fds</path>
    		<extension>.7z .fds .zip .7Z .FDS .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\nestopia_libretro.dll "%ROM_RAW%"</command>
    		<platform>fds</platform>
    		<theme>fds</theme>
    	</system>
    	<system>
    		<name>snes</name>
    		<fullname>Super Nintendo Entertainment System</fullname>
    		<path>{roms_root}\\snes</path>
    		<extension>.7z .sfc .smc .zip .SFC .SMC .ZIP .7Z</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\bsnes_hd_beta_libretro.dll "%ROM_RAW%"</command>
    		<platform>snes</platform>
    		<theme>snes</theme>
    	</system>
    	<system>
    		<name>snesh</name>
    		<fullname>SNES HACKS</fullname>
    		<path>{roms_root}\\snesh</path>
    		<extension>.7z .sfc .smc .zip .7Z .SFC .SMC .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\bsnes_hd_beta_libretro.dll "%ROM_RAW%"</command>
    		<platform>snes</platform>
    		<theme>snes-msu1</theme>
    	</system>
    	<system>
    		<name>satellaview</name>
    		<fullname>SatellaView</fullname>
    		<path>{roms_root}\\snes_satella</path>
    		<extension>.7z .sfc .smc .zip .7Z .SFC .SMC .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\bsnes_hd_beta_libretro.dll "%ROM_RAW%"</command>
    		<platform>satellaview</platform>
    		<theme>satellaview</theme>
    	</system>
    	<system>
    		<name>sufami</name>
    		<fullname>Sufami Turbo</fullname>
    		<path>{roms_root}\\snes_sufami</path>
    		<extension>.7z .sfc .smc .zip .7Z .SFC .SMC .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\bsnes_hd_beta_libretro.dll "%ROM_RAW%"</command>
    		<platform>console</platform>
    		<theme>sufami</theme>
    	</system>
    	<system>
    		<name>cps1</name>
    		<fullname>Capcom Play System</fullname>
    		<path>{roms_root}\\cps1</path>
    		<extension>.zip .7z .ZIP .7Z</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fbalpha_libretro.dll "%ROM_RAW%"</command>
    		<platform>Arcade</platform>
    		<theme>cps1</theme>
    	</system>
    	<system>
    		<name>cps2</name>
    		<fullname>Capcom Play System II</fullname>
    		<path>{roms_root}\\cps2</path>
    		<extension>.zip .7z .ZIP .7Z</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fbalpha_libretro.dll "%ROM_RAW%"</command>
    		<platform>Arcade</platform>
    		<theme>cps2</theme>
    	</system>
    	<system>
    		<name>cps3</name>
    		<fullname>Capcom Play System III</fullname>
    		<path>{roms_root}\\cps3</path>
    		<extension>.zip .7z .ZIP .7Z</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fbalpha_libretro.dll "%ROM_RAW%"</command>
    		<platform>Arcade</platform>
    		<theme>cps3</theme>
    	</system>
    	<system>
    		<name>n64</name>
    		<fullname>Nintendo 64</fullname>
    		<path>{roms_root}\\n64</path>
    		<extension>.7z .n64 .v64 .z64 .zip .N64 .V64 .Z64 .ZIP .7Z</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mupen64plus_next_libretro.dll "%ROM_RAW%"</command>
    		<platform>n64</platform>
    		<theme>n64</theme>
    	</system>
    	<system>
    		<name>gc</name>
    		<fullname>Nintendo GameCube</fullname>
    		<path>{roms_root}\\gc</path>
    		<extension>.iso .ISO .gcm .GCM</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\dolphin_libretro.dll "%ROM_RAW%"</command>
    		<platform>gc</platform>
    		<theme>gc</theme>
    	</system>
    	<system>
    		<name>wii</name>
    		<fullname>Nintendo Wii</fullname>
    		<path>{roms_root}\\wii</path>
    		<extension>.iso .ISO</extension>
    		<command>"{emuls_root}\\dolphin\\dolphin.exe" -e "%ROM_RAW%"</command>
    		<platform>wii</platform>
    		<theme>wii</theme>
    	</system>
    	<system>
    		<name>pokemini</name>
    		<fullname>Pokemon Mini</fullname>
    		<path>{roms_root}\\pokemini</path>
    		<extension>.min .zip .7z .ZIP .7Z .MIN</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\pokemini_libretro.dll "%ROM_RAW%"</command>
    		<platform>Hand Held</platform>
    		<theme>pokemini</theme>
    	</system>
    	<system>
    		<name>ps2</name>
    		<fullname>Playstation 2</fullname>
    		<path>{roms_root}\\ps2</path>
    		<extension>.bin .cue .iso .mds .cso .BIN .CUE .ISO .MDS. CSO</extension>
    		<command>{emuls_root}\\pcsx2\\pcsx2.exe --portable --nogui --fullscreen "%ROM_RAW%"</command>
    		<platform>ps2</platform>
    		<theme>ps2</theme>
    	</system>
    	<system>
    		<name>ps3</name>
    		<fullname>Playstation 3</fullname>
    		<path>{roms_root}\\ps3</path>
    		<extension>.vbs .bin .VBS .BIN</extension>
    		<command>"%ROM_RAW%"</command>
    		<platform>ps3</platform>
    		<theme>ps3</theme>
    	</system>
    	<system>
    		<name>psp</name>
    		<fullname>Playstation Portable</fullname>
    		<path>{roms_root}\\psp</path>
    		<extension>.cso .iso .CSO .ISO</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\ppsspp_libretro.dll "%ROM_RAW%"</command>
    		<platform>psp</platform>
    		<theme>psp</theme>
    	</system>
    	<system>
    		<name>pspminis</name>
    		<fullname>Playstation Portable Minis</fullname>
    		<path>{roms_root}\\psp_minis</path>
    		<extension>.cso .iso .CSO .ISO</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\ppsspp_libretro.dll "%ROM_RAW%"</command>
    		<platform>psp minis</platform>
    		<theme>psp</theme>
    	</system>
    	<system>
    		<name>psx</name>
    		<fullname>Playstation</fullname>
    		<path>{roms_root}\\psx</path>
    		<extension>.chd .cue .iso .pbp .CUE .ISO .PBP .CHD</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mednafen_psx_hw_libretro.dll "%ROM_RAW%"</command>
    		<platform>psx</platform>
    		<theme>psx</theme>
    	</system>
    	<system>
    		<name>msx</name>
    		<fullname>MSX</fullname>
    		<path>{roms_root}\\msx</path>
    		<extension>.7z .zip .col .dsk .mx1 .mx2 .rom .7Z .ZIP .COL .DSK .MX1 .MX2 .ROM</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fmsx_libretro.dll "%ROM_RAW%"</command>
    		<platform>msx</platform>
    		<theme>msx</theme>
    	</system>
    	<system>
    		<name>msxturbo</name>
    		<fullname>MSX Turbo</fullname>
    		<path>{roms_root}\\msxturbo</path>
    		<extension>.7z .zip .col .dsk .mx1 .mx2 .rom .7Z .ZIP .COL .DSK .MX1 .MX2 .ROM</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fmsx_libretro.dll "%ROM_RAW%"</command>
    		<platform>msx</platform>
    		<theme>msx</theme>
    	</system>
    	<system>
    		<name>msx2</name>
    		<fullname>MSX2</fullname>
    		<path>{roms_root}\\msx2</path>
    		<extension>.7z .zip .col .dsk .mx1 .mx2 .rom .7Z .ZIP .COL .DSK .MX1 .MX2 .ROM</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fmsx_libretro.dll "%ROM_RAW%"</command>
    		<platform>msx</platform>
    		<theme>msx2</theme>
    	</system>
    	<system>
    		<name>msx2plus</name>
    		<fullname>MSX</fullname>
    		<path>{roms_root}\\msx2plus</path>
    		<extension>.7z .ZIP .col .dsk .mx1 .mx2 .rom .7Z .ZIP .COL .DSK .MX1 .MX2 .ROM</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fmsx_libretro.dll "%ROM_RAW%"</command>
    		<platform>msx</platform>
    		<theme>msx2</theme>
    	</system>
    	<system>
    		<name>scummvm</name>
    		<fullname>ScummVM</fullname>
    		<path>{roms_root}\\scummvm</path>
    		<extension>.bat .BAT</extension>
    		<command>"{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\scummvm_libretro.dll "%ROM_RAW%"</command>
    		<platform>pc</platform>
    		<theme>scummvm</theme>
    	</system>
    	<system>
    		<name>colecovision</name>
    		<fullname>ColecoVision</fullname>
    		<path>{roms_root}\\coleco</path>
    		<extension>.bin .gam .vec .BIN .GAM .VEC .zip .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\bluemsx_libretro.dll "%ROM_RAW%"</command>
    		<platform>ColecoVision</platform>
    		<theme>ColecoVision</theme>
    	</system>
    	<system>
    		<name>zmachine</name>
    		<fullname>ZMachine</fullname>
    		<path>{roms_root}\\zmachine</path>
    		<extension>.7z .ZIP .dat .DAT .7Z .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fuse_libretro.dll "%ROM_RAW%"</command>
    		<platform>zmachine</platform>
    		<theme>zmachine</theme>
    	</system>
    	<system>
    		<name>zxspectrum</name>
    		<fullname>ZX Spectrum</fullname>
    		<path>{roms_root}\\zxspectrum</path>
    		<extension>sna .szx .z80 .tap .tzx .gz .udi .mgt .img .trd .scl .dsk SNA .SZX .Z80 .TAP .TZX .GZ .UDI .MGT .IMG .TRD .SCL .DSK</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\fuse_libretro.dll "%ROM_RAW%"</command>
    		<platform>zxspectrum</platform>
    		<theme>zxspectrum</theme>
    	</system>
    	<system>
    		<name>vectrex</name>
    		<fullname>Vectrex</fullname>
    		<path>{roms_root}\\vectrex</path>
    		<extension>.bin .gam .vec .BIN .GAM .VEC</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\vecx_libretro.dll "%ROM_RAW%"</command>
    		<platform>vectrex</platform>
    		<theme>vectrex</theme>
    	</system>
    	<system>
    		<name>videopac</name>
    		<fullname>Odyssey 2 / Videopac</fullname>
    		<path>{roms_root}\\videopac</path>
    		<extension>.zip .7z .bin .BIN .ZIP .7Z</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\o2em_libretro.dll "%ROM_RAW%"</command>
    		<platform>videopac</platform>
    		<theme>videopac</theme>
    	</system>
    	<system>
    		<name>intellivision</name>
    		<fullname>Mattle / Intellivision</fullname>
    		<path>{roms_root}\\intellivision</path>
    		<extension>.zip .7z .bin .BIN .ZIP .7Z</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\freeintv_libretro.dll "%ROM_RAW%"</command>
    		<platform>videopac</platform>
    		<theme>videopac</theme>
    	</system>
    	<system>
    		<name>gameandwatch</name>
    		<fullname>Game And Watch</fullname>
    		<path>{roms_root}\\gameandwatch</path>
    		<extension>.mgw .zip .MGW .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\gw_libretro.dll "%ROM_RAW%"</command>
    		<platform>gameandwatch</platform>
    		<theme>gameandwatch</theme>
    	</system>
    	<system>
    		<name>virtualboy</name>
    		<fullname>Virtual Boy</fullname>
    		<path>{roms_root}\\virtualboy</path>
    		<extension>.vb .zip .VB .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mednafen_vb_libretro.dll "%ROM_RAW%"</command>
    		<platform>virtualboy</platform>
    		<theme>virtualboy</theme>
    	</system>
    		<system>
    		<name>c64</name>
    		<fullname>Commodore 64</fullname>
    		<path>{roms_root}\\c64</path>
    		<extension>.7z .zip .crt .d64 .g64 .t64 .tap .x64 .CRT .D64 .G64 .T64 .TAP .X64 .7Z .ZIP</extension>
    		<command>{emuls_root}\\winvice\\x64.exe "%ROM_RAW%"</command>
    		<platform>c64</platform>
    		<theme>c64</theme>
    	</system>
    	<system>
    		<name>amiga</name>
    		<fullname>Amiga</fullname>
    		<path>{roms_root}\\amiga</path>
    		<extension>.adf .ADF</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\puae_libretro.dll "%ROM_RAW%"</command>
    		<platform>amiga</platform>
    		<theme>amiga</theme>
    	</system>
    	<system>
    		<name>amstradcpc</name>
    		<fullname>Amstrad CPC</fullname>
    		<path>{roms_root}\\amstradcpc</path>
    		<extension>.7z .zip .7Z .ZIP</extension>
    		<command>"{emuls_root}\\retroarch\\cores\\cap32_libretro.dll" -e "%ROM_RAW%"</command>
    		<platform>amstradcpc</platform>
    		<theme>amstradcpc</theme>
    	</system>
    	<system>
    		<name>apple2</name>
    		<fullname>Apple II</fullname>
    		<path>{roms_root}\\apple2</path>
    		<extension>.7z .zip .7Z .ZIP</extension>
    		<command>"{emuls_root}\\retroarch\\cores\\cap32_libretro.dll" -e "%ROM_RAW%"</command>
    		<platform>apple2</platform>
    		<theme>apple2</theme>
    	</system>
    	<system>
    		<name>x68000</name>
    		<fullname>Sharp x68000</fullname>
    		<path>{roms_root}\\x68000</path>
    		<extension>.7z .zip .7Z .ZIP</extension>
    		<command>"{emuls_root}\\retroarch\\cores\\px68k_libretro.dll" -e "%ROM_RAW%"</command>
    		<platform>x68000</platform>
    		<theme>x68000</theme>
    	</system>
    	<system>
    		<name>wonderswan</name>
    		<fullname>Wonderswan</fullname>
    		<path>{roms_root}\\wonderswan</path>
    		<extension>.ws .zip .WS .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mednafen_wswan_libretro.dll "%ROM_RAW%"</command>
    		<platform>wonderswan</platform>
    		<theme>wonderswan</theme>
    	</system>
    	<system>
    		<name>wonderswancolor</name>
    		<fullname>WonderSwanColor</fullname>
    		<path>{roms_root}\\wonderswancolor</path>
    		<extension>.ws .zip .WS .ZIP</extension>
    		<command>{emuls_root}\\retroarch\\retroarch.exe -L {emuls_root}\\retroarch\\cores\\mednafen_wswan_libretro.dll "%ROM_RAW%"</command>
    		<platform>wonderswancolor</platform>
    		<theme>wonderswancolor</theme>
    	</system>
    	<system>
    		<name>ports</name>
    		<fullname>Ported Games</fullname>
    		<path>{roms_root}\\ports</path>
    		<extension>.vbs .VBS</extension>
    		<command>"%ROM_RAW%"</command>
    		<platform>ports</platform>
    		<theme>ports</theme>
    	</system>
    	<system>
    		<name>pc</name>
    		<fullname>PC (x86)</fullname>
    		<path>{roms_root}\\pc</path>
    		<extension>.bat .BAT</extension>
    		<command>"%ROM_RAW%"</command>
    		<platform>pc</platform>
    		<theme>pc</theme>
    	</system>
    	<system>
    		<name>systemoptions</name>
    		<fullname>System Options</fullname>
    		<path>{roms_root}\\options</path>
    		<extension>.vbs .bat .lnk .exe .pyw .VBS .BAT .LNK .EXE .PYW</extension>
    		<command>"%ROM_RAW%"</command>
    		<platform>options</platform>
    		<theme>options</theme>
    	</system>
    </systemList>''')
        file.close()

    def es_settings_cfg(es_maindir):
        check_button(f'{es_maindir}\\es_settings.cfg \n This file will be generated now.', title='File not found!')
        with open(es_maindir + '\\es_settings.cfg', 'w+') as file:
            file.write(f'''<?xml version="1.0"?>
    <config>
    	<bool name="CaptionsCompatibility" value="false" />
    	<bool name="ClockMode12" value="false" />
    	<bool name="EnableSounds" value="true" />
    	<bool name="HideWindow" value="true" />
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
    	<bool name="VideoAudio" value="true" />
    	<bool name="audio.bgmusic" value="true" />
    	<bool name="updates.enabled" value="false" />
    	<int name="MaxVRAM" value="100" />
    	<int name="MusicVolume" value="60" />
    	<int name="ScraperResizeWidth" value="400" />
    	<int name="ScreenSaverSwapImageTimeout" value="5000" />
    	<int name="ScreenSaverTime" value="60000" />
    	<int name="recent.sort" value="7" />
    	<string name="CollectionSystemsAuto" value="all,favorites,recent" />
    	<string name="DefaultGridSize" value="7 2" />
    	<string name="ExePath" value="emulationstation.exe" />
    	<string name="FolderViewMode" value="having multiple games" />
    	<string name="HiddenSystems" value="" />
    	<string name="Language" value="pt_BR" />
    	<string name="LastSystem" value="neogeo" />
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
    	<string name="subset.staticEffect" value="crt" />
    	<string name="subset.swapAmbiance" value="setMediaLibrary" />
    	<string name="subset.swapColor" value="orange" />
    	<string name="subset.swapVideoEffect" value="videoEffectBump" />
    	<string name="subset.systemView" value="menuVertLeft" />
    	<string name="updates.type" value="beta" />
    </config>
    ''')
        file.close()
        return es_maindir + '\\es_settings.cfg'

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


def check_ini_and_args():
    es_dir = emuls_root = roms_root = settings_cfg_file = ''
    startup_dir = intro_file = splashs_root = vlcargs = es_args = ''
    kill_exp = random_theme = ex_fullscreen = assync_load = play_vlc_embedded = False
    play = hide_es_while_assync_load = boot_videos = True
    resolution = []
    current_process_hwnds = []

    def check_entry_es_ini(value_in, ini_entry):
        if isdir(value_in):
            return value_in
        else:
            alert(f'es_launcher.ini {ini_entry} entry value has a invalid directory path:\n{value_in}'
                  , 'es_launcher.ini error!')
            raise SystemExit

    if isfile('es_launcher.ini'):
        with open('es_launcher.ini', 'r') as config_ini:
            for line in config_ini:
                if '=' in line:
                    entry, value = line.lower().split('=', 1)  # normalizing text then spliting 1 time by char '=' in 2
                    entry = entry.strip()  # Removing edge spaces and new line characters,
                    value = value.strip()
                    if entry == 'assync_load' and value == 'true': assync_load = True
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
            elif arg == '-e': kill_exp = True
            elif arg == '--exf': ex_fullscreen = True
            elif arg == '--rt': random_theme = True
            elif arg == '--play_vlc_embedded': play_vlc_embedded = True
            elif arg == '--no_boot_videos': boot_videos = False
            elif arg == '--assync_load': assync_load = True
            elif arg == '--dont_hide_es': hide_es_while_assync_load = False
            else:
                es_args += ' ' + arg

    if not isdir(es_dir) or es_dir == '':
        if getattr(sys, 'frozen', False):
            es_dir = dirname(sys.executable)  # if converted to executable this will be used
        elif __file__:
            es_dir = dirname(__file__)

    return es_dir, emuls_root, roms_root, settings_cfg_file, startup_dir,\
        intro_file, splashs_root, vlcargs, es_args, kill_exp, random_theme, ex_fullscreen,\
        assync_load, play_vlc_embedded, play, hide_es_while_assync_load, boot_videos, resolution,\
        current_process_hwnds


def extract_contents2(file_path, temp_dir='!Temp_Dir', dest_dir='.\\Default_destination'):
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
        if 1 == dir_count > file_count <= 0:
            return count_dirandfiles(dir_path)
        return last_dir_path

    if exists(temp_dir):
        rmtree(temp_dir)  # Cleaning any leftover
        mkdir(temp_dir)
    else:
        mkdir(temp_dir)
    sp.run(f'7za.exe x "{file_path}" -o"{temp_dir}" -y')  # Using 7zip command line
    new_temp_dir = count_dirandfiles(temp_dir)
    move_files_recur(new_temp_dir, dest_dir)
    rmtree(temp_dir)


def move_files_recur(path_loc, dest_path):
    if dest_path[-1:] != '\\':
        dest_path += '\\'
    if not isdir(dest_path):
        makedirs(dest_path)
    if isdir(path_loc) and isdir(dest_path):
        scandir_ob = scandir(path_loc)
        for item in scandir_ob:
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


def download_binary_r(url_in, file_name='filedownloaded.zip'):
    bin_data_resp = requests.get(url_in, stream=True)
    with open(file_name, 'wb') as file:
        for chunk in bin_data_resp.iter_content(chunk_size=1048576):
            if chunk:
                file.write(chunk)
    file.close()


def replace_line(file_path, str2find, new_line_content):
    with open(file_path, 'r') as settings_file:
        file_copy = [new_line_content if str2find in line else line for line in settings_file]
    settings_file.close()

    with open(file_path, 'w+') as settings_file:
        for item in file_copy:
            settings_file.write(item)
    settings_file.close()


def check_button(text='', title='', buttons=''):
    button = confirm(text, title)
    if button is None or button.lower() == 'cancel':
        raise SystemExit
    else:
        return button


def check_7zip(path):
    if not exists(join(path, '7za.exe')) or not exists(join(path, '7za.dll')) or not exists(join(path, '7zxa.dll')):
        alert('7zip command executable file was not found!\nThere should be present 3 files 7za.exe, 7za.dll and '
              '7zxa.dll. An archive will be downloaded containing these files but you will need to extract it manually '
              f'in EmulationStation root directory:\n{path}.', title="ERROR! 7zip files not found.")
        download_binary_r('https://www.7-zip.org/a/7z1900-extra.7z', '7zip.7z')
        raise SystemExit


def check_vlc_setup(vlc_path_in):
    if isfile(vlc_path_in):
        return vlc_path_in
    else:
        check_button(f'VLC files not found on "{vlc_path_in}"! Will be downloaded now. All credits goes to '
                     f'VLC devs team.')
        download_binary_r('http://download.videolan.org/pub/videolan/vlc/last/win32/vlc-3.0.11-win32.7z',
                          'VLC.zip')
        extract_contents2('VLC.zip', dest_dir=dirname(vlc_path_in))
        return check_vlc_setup(vlc_path_in)


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


def set_emuls_root(path, default_path):
    if path == '':
        return default_path
    elif not exists(path):
        try:
            makedirs(path)
        except:
            alert(f'Could\'nt crate Emulators dir at location "{path}"', 'Error in set_emuls_root()')
            raise SystemExit
        return set_emuls_root(path, default_path)
    else:
        return path


def set_roms_root(path, default_path):
    if path == '':
        return default_path
    elif not exists(path):
        try:
            makedirs(path)
        except:
            alert(f'Could\'nt crate Roms dir at location "{path}"', 'Error in set_roms_root()')
            raise SystemExit
        return set_roms_root(path, default_path)
    else:
        return path


def check_emustation_setup(es_path_in):
    if isfile(es_path_in):
        return es_path_in
    else:
        check_button(f'emulationstation.exe file not found on "{es_path_in}". It will be downloaded now from '
                     'Fabricecaruso github "https://github.com/fabricecaruso". All Credits goes to him.')
        download_binary_r('https://github.com/fabricecaruso/batocera-emulationstation/releases/download/'
                          'continuous-beta/EmulationStation-Win32.zip', 'EmulationStation-Win32.zip')
        extract_contents2('EmulationStation-Win32.zip', dest_dir=dirname(es_path_in))
        return check_emustation_setup(es_path_in)


def check_themes_setup(path, settings_cfg_file_in, randomize):
    def randomize_themes(path):
        from random import randint
        themes_list = [item.name for item in scandir(path) if item.is_dir]
        return themes_list[randint(0, len(themes_list) - 1)]

    if isdir(path):
        if randomize:
            theme_selected = randomize_themes(path)
            replace_line(settings_cfg_file_in, '"ThemeSet" value=',
                         f'    <string name="ThemeSet" value="{theme_selected}" />')
    else:
        check_button(f'Themes directory not found on "{path}". It will be created now and populated with '
                     'ComicBook theme from the author TMNTturtleguy "https://github.com/TMNTturtleguy/". '
                     'All credits goes to him.')
        makedirs(path)
        download_binary_r('https://github.com/TMNTturtleguy/es-theme-ComicBook/archive/master.zip', 'ComicBook.zip')
        extract_contents2('ComicBook.zip', dest_dir=path + '\\ComicBook')
        check_themes_setup(path, settings_cfg_file_in, randomize)


def check_es_maindir(path):
    if isdir(path):
        return path
    else:
        check_button(f'Main ES subdirectory ".emulationstation" not found here:\n"{path}"\n'
                     f'Would you like to create it?', title='ES Subdirectory ERROR!')
        makedirs(path)
        return check_es_maindir(path)  # check again if it now exists


def check_splashs_setup(path):
    if isdir(path):
        return path
    else:
        check_button(f'Splashs videos directory not found on "{path}". It will be create now and populated '
                     'with some splashs videos from the author ehettervik "https://github.com/ehettervik/"'
                     '. All credits goes to him.')
        makedirs(path)
        download_binary_r('https://github.com/ehettervik/retropie-splash-videos/archive/master.zip',
                          'splashs.zip')
        extract_contents2('splashs.zip', dest_dir=path)
        return check_splashs_setup(path)


def setdisplaysolution(width, height, fhz):
    import pywintypes

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

    mode_required = (32, int(width), int(height), int(fhz))
    devmode = display_modes[mode_required]
    try:
        win32api.ChangeDisplaySettings(devmode, 0)
    except 'KeyError':
        alert('setdisplayresolution error!')


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


# ---------------------------------------Execution Pipeline-------------------------------------------------------------
if is_admin():  # Re-run the program with admin rights | Note that this trick uses the first argument of sys.argv
    main()
else:           # Use sys.argv[1:] (ignore first element) if you plan to convert to .exe else sys.argv only.
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
raise SystemExit
