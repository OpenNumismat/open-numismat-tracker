[Setup]
AppName=NumismatTracker
AppId=NumismatTracker
AppVersion=0.0.1
DefaultDirName={pf}\NumismatTracker
DefaultGroupName=NumismatTracker
UninstallDisplayIcon={app}\NumismatTracker.exe
OutputDir="."
OutputBaseFilename="NumismatTracker-0.0.1"
AllowNoIcons=yes
AppCopyright=Copyright 2013 by Vitaly Ignatov
AppPublisher=Janis

[Languages]
Name: en; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: license_en.txt
Name: ru; MessagesFile: "compiler:Languages\Russian.isl"; InfoBeforeFile: license_ru.txt
Name: uk; MessagesFile: "compiler:Languages\Ukrainian.isl"; InfoBeforeFile: license_uk.txt
Name: es; MessagesFile: "compiler:Languages\Spanish.isl"; InfoBeforeFile: license_es.txt
Name: hu; MessagesFile: "compiler:Languages\Hungarian.isl"; InfoBeforeFile: license_en.txt

[CustomMessages]
en.sendReport=Send a reports to author's web-site if any error occured
ru.sendReport=Посылать отчет разработчику при возникновении ошибки
uk.sendReport=Відправляти звіт про помилки автору
es.sendReport=Enviar un informe al autor del sitio web si cualquier error
hu.sendReport=Hiba elkuldese a keszitonek

[Files]
Source: "..\build\exe.win32-3.2\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\build\exe.win32-3.2\db\reference_en.ref"; DestDir: "{userdocs}\NumismatTracker"; DestName: "reference.ref"; Languages: en; Flags: confirmoverwrite
Source: "..\build\exe.win32-3.2\db\reference_ru.ref"; DestDir: "{userdocs}\NumismatTracker"; DestName: "reference.ref"; Languages: ru; Flags: confirmoverwrite
Source: "..\build\exe.win32-3.2\db\reference_uk.ref"; DestDir: "{userdocs}\NumismatTracker"; DestName: "reference.ref"; Languages: uk; Flags: confirmoverwrite
Source: "..\build\exe.win32-3.2\db\reference_es.ref"; DestDir: "{userdocs}\NumismatTracker"; DestName: "reference.ref"; Languages: es; Flags: confirmoverwrite
Source: "..\build\exe.win32-3.2\db\reference_hu.ref"; DestDir: "{userdocs}\NumismatTracker"; DestName: "reference.ref"; Languages: hu; Flags: confirmoverwrite

[Dirs]
Name: "{userdocs}\NumismatTracker\backup"

[Registry]
Root: HKCU; Subkey: "Software\Janis"; Flags: uninsdeletekeyifempty
Root: HKCU; Subkey: "Software\Janis\NumismatTracker"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Janis\NumismatTracker\mainwindow"; ValueType: string; ValueName: "error"; ValueData: "true"; Tasks: sendreport

[Icons]
Name: "{group}\NumismatTracker"; Filename: "{app}\NumismatTracker.exe"
Name: "{group}\Uninstall NumismatTracker"; Filename: "{uninstallexe}"
Name: "{userdesktop}\NumismatTracker"; Filename: "{app}\NumismatTracker.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\NumismatTracker"; Filename: "{app}\NumismatTracker.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\NumismatTracker.exe"; Flags: postinstall nowait skipifsilent

[Tasks]
Name: sendreport; Description: "{cm:sendReport}"
Name: desktopicon; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: quicklaunchicon; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
