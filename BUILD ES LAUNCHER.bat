pip install --upgrade pyinstaller
RMDIR /S /Q "__pycache__"
RMDIR /S /Q "build"
RMDIR /S /Q "dist"
pyinstaller -w -F "es_launcher.pyw"
del "es_launcher.spec"
RMDIR /S /Q "__pycache__"
RMDIR /S /Q "build"
move "dist\es_launcher.exe" "."
RMDIR /S /Q "dist"
pause