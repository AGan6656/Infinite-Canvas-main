!define APPNAME "Infinite-Canvas"
!define APPDIR "$PROGRAMFILES\\Infinite-Canvas"

OutFile "dist\\Infinite-Canvas-Installer.exe"
InstallDir "${APPDIR}"

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "..\\dist\\Infinite-Canvas\\*.*"
  CreateDirectory "$SMPROGRAMS\\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\\${APPNAME}\\Infinite-Canvas.lnk" "$INSTDIR\\Infinite-Canvas.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\\${APPNAME}\\Infinite-Canvas.lnk"
  RMDir "$SMPROGRAMS\\${APPNAME}"
  RMDir /r "$INSTDIR"
SectionEnd
