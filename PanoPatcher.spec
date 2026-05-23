# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

import tkinterdnd2

block_cipher = None
tkdnd_root = Path(tkinterdnd2.__file__).parent / 'tkdnd' / 'win-x64'
tkinterdnd2_datas = [(str(tkdnd_root), 'tkinterdnd2/tkdnd/win-x64')]


a = Analysis(['PanoPatcher.pyw'],
             pathex=[],
             binaries=[],
             datas=tkinterdnd2_datas,
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
                    'pycparser',
                    'redis',
                    'requests',
                    's3transfer',
                    'safetensors',
                    'sqlite3',
                    'sympy',
                    'tokenizers',
                    'torch',
                    'torchgen',
                    'tqdm',
                    'transformers',
                    'urllib3',
                    'ssl',
                    '_ssl',
                    'pyi_splash',
                    'PIL.ImageQt',
                    'PIL.ImageCms',
                    'PIL.ImageMath',
                    'PIL.ImageFont',
                    'PIL.WebPImagePlugin',
                    'numpy.random',
                    'numpy.fft',
                    'numpy.linalg',
                    'scipy',
                    'scipy.linalg',
                    'scipy.integrate',
                    'scipy.optimize',
                    'scipy.sparse',
                    'scipy.special',
                    'skimage',
                    'scikit_image',
                    ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

def keep_binary(item):
    name = item[0].lower()
    source = item[1].lower()
    if name.startswith('cv2\\opencv_videoio_ffmpeg'):
        return False
    if 'program files\\java\\jdk' in source:
        return False
    if name in {'_ssl.pyd', 'libssl-3.dll'}:
        return False
    if name.startswith('pil\\_webp') or name.startswith('pil\\_imagingcms') or name.startswith('pil\\_imagingmath') or name.startswith('pil\\_imagingft'):
        return False
    if name.startswith('numpy\\random\\') or name.startswith('numpy\\fft\\') or name.startswith('numpy\\linalg\\'):
        return False
    return True

a.binaries = TOC([item for item in a.binaries if keep_binary(item)])
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas, 
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
          entitlements_file=None,
          icon='app/icons/icon.ico',
          manifest='PanoPatcher.manifest')
