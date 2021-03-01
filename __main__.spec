# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

datas = []

a = Analysis(['zencad/__main__.py'],
             pathex=['/home/mirmik/project/zencad', '/home/mirmik/project/zenframe'],
             binaries=[],
             datas=datas,
             hiddenimports=["zenframe"],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=True)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='ZenFrame',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='ZenFrame')
