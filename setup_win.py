import subprocess
import shutil
import os
try:shutil.rmtree('dist')
except:pass
process=subprocess.Popen(['pyinstaller','PanoPatcher.spec'])
process.wait()
shutil.copytree('app','dist/app')
shutil.rmtree('dist/app/lib')
os.remove('dist/app/gui.py')
try:
	os.remove('dist/app/sets.json')
except:pass

input('All done...')
