' EchoKids English - 1-Click Silent Desktop Launcher
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Current directory
strDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Check if port 8000 is already active
Set oExec = WshShell.Exec("powershell -NoProfile -Command ""Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1""")
strPid = Trim(oExec.StdOut.ReadAll())

' If server is not running, launch python app.py silently (0 = hidden window)
If strPid = "" Then
    WshShell.CurrentDirectory = strDir
    WshShell.Run "python app.py", 0, False
    WScript.Sleep 2000
End If

' Open default browser to the platform
WshShell.Run "http://localhost:8000"
