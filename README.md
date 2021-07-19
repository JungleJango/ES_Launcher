# ES_Launcher
A simple launcher to make EmulationStation (forks) for windows more reliable and enjoyable
______________________________________________________________________________________________________________________________________________________________________
Arguments options:
--es=							        | Sets ES root dir absolute path
--ro=			      				  | Sets rooms root dir. Can be absolute like "c:\rooms" or relative like "..\rooms" (..\ means one lv up relative to ES root dir)
--em=						      	  | Sets emulators dir. Same as above
--sp=							        | Sets splash screens dir. Same as above
--rt							        | Random Theme selection within themes root folder .emulationstation\themes
-e								        | Exclusive mode kills explorer.exe process to clear screen from any window then when ES is finished brings it back again
--exf							        | Exclusive Fullscreen
--novid							      | Do play any startup video or splash video
--no_boot_videos				  | Don't play startup_videos dir files
--assync_load				  	  | Loads EmulationStation in background while vlc is playing splash video
--dont_hide_es					  | Don't hide ES window while playing video on foreground for smoother transition
--play_vlc_embedded			  | Directly embeds vlc video stream in emulationstation main window. Smoother trasion but if vlc takes too long to start becomes a little messy
--resolution=1920x1080x60 | Sets Resolution before running EmulationStation width, height, frequency hz
______________________________________________________________________________________________________________________________________________________________________
emulationstation native arguments
--resolution [width] [height]   try and force a particular resolution
--gamelist-only                 skip automatic game search, only read from gamelist.xml
--ignore-gamelist               ignore the gamelist (useful for troubleshooting)
--draw-framerate                display the framerate
--no-exit                       don't show the exit option in the menu
--no-splash                     don't show the splash screen
--debug                         more logging, show console on Windows
--scrape                        scrape using command line interface
--windowed                      can be used with --resolution
--fullscreen-borderless			    depends on --windowed
--vsync [1/on or 0/off]         turn vsync on or off (default is on)
--max-vram [size]               Max VRAM to use in Mb before swapping. 0 for unlimited
--force-kid             	    	Force the UI mode to be Kid
--force-kiosk           		    Force the UI mode to be Kiosk
--force-disable-filters         Force the UI to ignore applied filters in gamelist
--home							            Force the .emulationstation folder (windows)
--help, -h                      summon a sentient, angry tuba
______________________________________________________________________________________________________________________________________________________________________
Optional "es_launcher.ini" (lowercase) file can be created with the following entries
es_dir=							  | Path
roms_root=						| Path
emuls_root=						| Path
splashs_root=					| Path
novid=							  | True or False (Default)
exclusive=						| True or False (Default)
ex_fullscreen=  			| True or False (Default)
debug=							  | True or False (Default)
random_theme=					| True or False (Default)
assync_load=    			| True or False (Default)
dont_hide_es=					| True or False (Default)
play_vlc_embedded=		| True or False (Default)
resolution=						| 1920x1080 need windowed

By default any intro.mp4 in ES root directory will be used as intro.
python 3.9.5 (win10 only) script non-standard modules dependancy:
pymsgbox
requests
playsound
pycaw
