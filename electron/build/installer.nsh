; ──────────────────────────────────────────────────────────────────────────────
; Billino NSIS Custom Installer Script
;
; Ensures the Microsoft Visual C++ 2015-2022 Redistributable (x64) is installed.
; This is required because the PyInstaller-bundled backend depends on
; vcruntime140.dll which ships with the VC++ Redistributable.
; ──────────────────────────────────────────────────────────────────────────────

!include "MUI2.nsh"
!include "x64.nsh"

; ─── Check and install VC++ Redistributable ─────────────────────────────────

!macro customInit
  ; Check if VC++ Redistributable 2015-2022 (x64) is already installed
  ; Registry key exists when the redist is installed
  ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64" "Installed"
  ${If} $0 != 1
    ; Not installed – extract and run the bundled installer silently
    SetOutPath "$PLUGINSDIR"
    File "${BUILD_RESOURCES_DIR}\vc_redist.x64.exe"
    DetailPrint "Installing Microsoft Visual C++ Redistributable..."
    nsExec::ExecToLog '"$PLUGINSDIR\vc_redist.x64.exe" /install /quiet /norestart'
    Pop $0
    ${If} $0 != 0
      ; Non-zero exit – warn but don't block installation
      DetailPrint "VC++ Redistributable installation returned: $0"
    ${EndIf}
  ${Else}
    DetailPrint "Microsoft Visual C++ Redistributable already installed."
  ${EndIf}
!macroend
