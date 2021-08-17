REG ADD "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v Shell /t REG_SZ /d "%~dp0es_launcher.exe -s --play_vlc_embedded" /f
pause