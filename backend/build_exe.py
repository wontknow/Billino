"""
Billino Backend – PyInstaller Build Script

Usage:
    cd backend
    python build_exe.py

This script:
1. Builds the FastAPI backend into a standalone executable
2. Ensures vcruntime140.dll is bundled (fixes crashes on PCs without VC++ Redist)
3. Outputs to build/billino-backend/ (picked up by electron-builder)
"""

import os
import shutil
import subprocess
import sys

# ─── Configuration ────────────────────────────────────────────────────────────

APP_NAME = "billino-backend"
ENTRY_POINT = "main.py"
OUTPUT_DIR = os.path.join("build", APP_NAME)

# ─── Locate vcruntime DLLs from the Python installation ──────────────────────

PYTHON_DIR = os.path.dirname(sys.executable)
VCRUNTIME_DLLS = ["vcruntime140.dll", "vcruntime140_1.dll"]


def find_vcruntime_binaries() -> list[tuple[str, str]]:
    """Find vcruntime DLLs to bundle with the executable."""
    binaries = []
    for dll in VCRUNTIME_DLLS:
        dll_path = os.path.join(PYTHON_DIR, dll)
        if os.path.isfile(dll_path):
            # PyInstaller binary tuple: (source_path, destination_folder)
            binaries.append((dll_path, "."))
            print(f"  ✅ Found {dll}: {dll_path}")
        else:
            print(f"  ⚠️  {dll} not found at {dll_path}")
    return binaries


def build():
    """Run PyInstaller to create the backend executable."""
    print("=" * 60)
    print(f"  Billino Backend Build ({APP_NAME})")
    print("=" * 60)
    print()

    # Check vcruntime availability
    print("🔍 Checking vcruntime DLLs...")
    vcruntime_binaries = find_vcruntime_binaries()
    print()

    # Build PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        # One-directory mode (faster startup than one-file)
        "--onedir",
        # Output directory
        "--distpath",
        "build",
        # Work directory for intermediate files
        "--workpath",
        os.path.join("build", "work"),
        # Spec file output
        "--specpath",
        "build",
        # Hidden imports that PyInstaller might miss
        "--hidden-import",
        "uvicorn.logging",
        "--hidden-import",
        "uvicorn.lifespan.on",
        "--hidden-import",
        "uvicorn.lifespan.off",
        "--hidden-import",
        "uvicorn.lifespan",
        "--hidden-import",
        "uvicorn.protocols.http",
        "--hidden-import",
        "uvicorn.protocols.http.auto",
        "--hidden-import",
        "uvicorn.protocols.http.h11_impl",
        "--hidden-import",
        "uvicorn.protocols.http.httptools_impl",
        "--hidden-import",
        "uvicorn.protocols.websockets",
        "--hidden-import",
        "uvicorn.protocols.websockets.auto",
        "--hidden-import",
        "uvicorn.protocols.websockets.wsproto_impl",
        "--hidden-import",
        "uvicorn.protocols.websockets.websockets_impl",
        "--hidden-import",
        "uvicorn.loops",
        "--hidden-import",
        "uvicorn.loops.auto",
        "--hidden-import",
        "uvicorn.loops.asyncio",
    ]

    # Add vcruntime DLLs as binaries
    for src, dest in vcruntime_binaries:
        cmd.extend(["--add-binary", f"{src}{os.pathsep}{dest}"])

    # Entry point
    cmd.append(ENTRY_POINT)

    print(f"🔨 Running PyInstaller...")
    print(f"   Entry: {ENTRY_POINT}")
    print(f"   Output: {OUTPUT_DIR}/")
    print()

    result = subprocess.run(cmd, cwd=os.path.dirname(__file__) or ".")
    if result.returncode != 0:
        print(f"\n❌ Build failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    # Verify output
    exe_name = f"{APP_NAME}.exe" if sys.platform == "win32" else APP_NAME
    exe_path = os.path.join(OUTPUT_DIR, exe_name)
    if os.path.isfile(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n✅ Build successful!")
        print(f"   Executable: {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"\n❌ Expected executable not found: {exe_path}")
        sys.exit(1)

    # Verify vcruntime DLLs in output
    internal_dir = os.path.join(OUTPUT_DIR, "_internal")
    print(f"\n🔍 Checking vcruntime in output...")
    for dll in VCRUNTIME_DLLS:
        # Check both root and _internal
        in_root = os.path.isfile(os.path.join(OUTPUT_DIR, dll))
        in_internal = os.path.isfile(os.path.join(internal_dir, dll))
        if in_root or in_internal:
            location = OUTPUT_DIR if in_root else internal_dir
            print(f"   ✅ {dll} found in {location}")
        else:
            print(f"   ⚠️  {dll} NOT found – may cause crashes on other PCs!")

    print(f"\n🎉 Done! Output ready for electron-builder at: {OUTPUT_DIR}/")


if __name__ == "__main__":
    build()
