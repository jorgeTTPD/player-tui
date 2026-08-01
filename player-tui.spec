# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/player_tui/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'dbus',
        'gi',
        'gi.repository.GLib',
        'gi.repository.GObject',
        'gi.repository.Gio',
        'player_tui.lyrics_backend.lyrics_manager',
        'player_tui.lyrics_backend.mpris_player',
        'player_tui.lyrics_backend.mpris_prober',
        'player_tui.lyrics_backend.server',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='player-tui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
