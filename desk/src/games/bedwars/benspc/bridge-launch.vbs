' bridge-launch.vbs - the GlimBridge task runs this through wscript.exe so bridge.ps1 starts with NO window at all
' (powershell -WindowStyle Hidden alone still flashes a console on the desktop). Waits for bridge.ps1 to exit.
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File ""C:\Users\benja\glim-bedwars\bridge.ps1""", 0, True
