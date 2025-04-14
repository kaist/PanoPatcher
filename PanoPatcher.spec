# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, eval_statement

block_cipher = None


a = Analysis(['PanoPatcher.pyw'],
             pathex=[],
             binaries=[],
             datas=collect_data_files('tkinterdnd2'),
             hiddenimports=['jaraco.text'],
             excludes=[
                    'setuptools',
                    'django',
                    'cryptography',
                    'OpenSSL',
                    'boto3',
                    'botocore',
                    'certify',
                    'colorama',
                    'defusedxml',
                    'diffusers',
                    'google',
                    'huggingface_hub',
                    'imageio',
                    'imageio_ffmpeg',
                    'jinja2',
                    'llvmlite',
                    'moviepy',
                    'mpmath',
                    'networkx',
                    'numba',
                    'psutil',
                    'pycparser'
                    'redis',
                    'requests',
                    's3transfer'
                    'safetensors',
                    'sqlite3',
                    'sympy',
                    'tokenizers',
                    'torch',
                    'torchgen',
                    'tqdm',
                    'transformers',
                    'urllib3',
                    'skipy.linalg',
                    'skipy.integrate',
                    'skipy.optimize',
                    'skipy.parse',
                    'skipy.special',
                    ''
                    ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             collect_all=['TkinterDnD2'],
             noarchive=True)

a.binaries - TOC([
  ('opencv_videoio_ffmpeg4110_64.dll', None, None),

])
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
splash = Splash('app\\icons\\splash.png',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=None,
                text_size=12,
                minify_script=True)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas, 
          splash, 
          splash.binaries,
          [],
          name='PanoPatcher',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon='app/icons/icon.ico')
