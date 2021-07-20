# ES_Launcher

_A simple launcher to make EmulationStation (forks) for windows more reliable and enjoyable_

## Arguments options:

<ul><li>--es=					|Sets ES root dir absolute path</li>
<li>--ro=			      		| Sets rooms root dir. Can be absolute like "c:\rooms" or relative like "..\rooms" (..\ means one lv up relative to ES root dir)</li>
<li>--em=						| Sets emulators dir. Same as above</li>
<li>--sp=						| Sets splash screens dir. Same as above</li>
<li>--rt						| Random Theme selection within themes root folder .emulationstation\themes</li>
<li>-e							| Exclusive mode kills explorer.exe process to clear screen from any window then when ES is finished brings it back again</li>
<li>--exf						| Exclusive Fullscreen</li>
<li>--novid						| Do play any startup video or splash video</li>
<li>--no_boot_videos			| Don't play startup_videos dir files</li>
<li>--assync_load				| Loads EmulationStation in background while vlc is playing splash video</li>
<li>--dont_hide_es				| Don't hide ES window while playing video on foreground for smoother transition</li>
<li>--play_vlc_embedded			| Directly embeds vlc video stream in emulationstation main window. Smoother trasion but if vlc takes too long to start becomes a little messy</li>
<li>--resolution=1920x1080x60	| Sets Resolution before running EmulationStation width, height, frequency hz</li></ul>

## EmulationStation native arguments:

<ul><li>--resolution [width] [height]	try and force a particular resolution</li>
<li>--gamelist-only					skip automatic game search, only read from gamelist.xml</li>
<li>--ignore-gamelist				ignore the gamelist (useful for troubleshooting)</li>
<li>--draw-framerate				display the framerate</li>
<li>--no-exit						don't show the exit option in the menu</li>
<li>--no-splash						don't show the splash screen</li>
<li>--debug							more logging, show console on Windows</li>
<li>--scrape						scrape using command line interface</li>
<li>--windowed						can be used with --resolution</li>
<li>--fullscreen-borderless			depends on --windowed</li>
<li>--vsync [1/on or 0/off]			turn vsync on or off (default is on)</li>
<li>--max-vram [size]				Max VRAM to use in Mb before swapping. 0 for unlimited</li>
<li>--force-kid						Force the UI mode to be Kid</li>
<li>--force-kiosk					Force the UI mode to be Kiosk</li>
<li>--force-disable-filters			Force the UI to ignore applied filters in gamelist</li>
<li>--home							Force the .emulationstation folder (windows)</li>
<li>--help, -h						summon a sentient, angry tuba</li></ul>

## Optional "es_launcher.ini" (lowercase) file can be created with the following entries

<ul><li>es_dir=							| Path</li>
<li>roms_root=						| Path</li>
<li>emuls_root=						| Path</li>
<li>splashs_root=					| Path</li>
<li>novid=							| True or False (Default)</li>
<li>exclusive=						| True or False (Default)</li>
<li>ex_fullscreen=					| True or False (Default)</li>
<li>debug=							| True or False (Default)</li>
<li>random_theme=					| True or False (Default)</li>
<li>assync_load=					| True or False (Default)</li>
<li>dont_hide_es=					| True or False (Default)</li>
<li>play_vlc_embedded=				| True or False (Default)</li>
<li>resolution=						| 1920x1080 need windowed</li></ul>

<li>By default any intro.mp4 in ES root directory will be used as intro.</li>
<li>python 3.9.5 (win10 only) script non-standard modules dependancy:</li>
<li>pymsgbox</li>
<li>requests</li>
<li>playsound</li>
<li>pycaw</li>
