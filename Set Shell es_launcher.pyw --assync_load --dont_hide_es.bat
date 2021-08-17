REG ADD "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v Shell /t REG_SZ /d "pythonw.exe %~dp0es_launcher.pyw --assync_load --dont_hide_es" /f
pause