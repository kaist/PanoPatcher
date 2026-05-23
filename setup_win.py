import subprocess
import shutil
import os
import sys
try:shutil.rmtree('dist')
except:pass
process=subprocess.Popen([sys.executable,'-m','PyInstaller','PanoPatcher.spec'])
process.wait()
shutil.copytree('app','dist/app')
shutil.rmtree('dist/app/lib')
os.remove('dist/app/gui.py')
try:
	os.remove('dist/app/sets.json')
except:pass

input('All done...')
