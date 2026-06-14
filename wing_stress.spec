# wing_stress.spec  —  AeroBeam v1.2
from PyInstaller.utils.hooks import collect_all, collect_submodules
import os

block_cipher = None

packages = ['numpy', 'matplotlib', 'openpyxl', 'xlsxwriter']

all_datas    = []
all_binaries = []
all_hiddenimports = []

for pkg in packages:
    datas, binaries, hidden = collect_all(pkg)
    all_datas    += datas
    all_binaries += binaries
    all_hiddenimports += hidden

all_hiddenimports += collect_submodules('openpyxl')
all_hiddenimports += collect_submodules('xlsxwriter')
all_hiddenimports += ['openpyxl', 'xlsxwriter']

# Include icon only if it is present next to the spec
_spec_dir  = os.path.dirname(os.path.abspath(SPEC))
_icon_path = os.path.join(_spec_dir, 'AeroBeam.ico')
_icon      = _icon_path if os.path.isfile(_icon_path) else None

if _icon:
    all_datas += [(_icon_path, '.')]

a = Analysis(
    ['wing_stress_gui.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports + ['tkinter', 'tkinter.ttk'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AeroBeam',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AeroBeam',
)
