# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('workflows', 'workflows'), ('static', 'static'), ('API', 'API')],
    hiddenimports=[
        'PIL',
        'fastapi',
        'uvicorn',
        'httpx',
        'requests',
        'pydantic',
        'backend',
        'backend.app',
        'backend.core',
        'backend.core_imports',
        'backend.services.image_service',
        'backend.services.llm_service',
        'backend.services.video_service',
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
    [],
    exclude_binaries=True,
    name='Infinite-Canvas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Infinite-Canvas',
)
