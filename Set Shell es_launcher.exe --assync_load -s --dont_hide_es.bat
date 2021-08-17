REG ADD "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v Shell /t REG_SZ /d "%~dp0es_launcher.exe --assync_load -s --dont_hide_es" /f
pause