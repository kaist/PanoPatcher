import sys,os
sys.dont_write_bytecode=True
from pathlib import Path

VERSION='1.23'
PORTABLE=False
DATA_PATH=Path('app/')

if hasattr(sys,"frozen"):
    os.chdir(os.path.dirname(sys.executable))
    p=DATA_PATH/Path('error.txt')
    if not p.parent.exists():
        p.parent.mkdir()
    sys.stderr=open(p,'a+')

if not DATA_PATH.exists():
    DATA_PATH.mkdir()







class AppSets:
    def __init__(self):
        object.__setattr__(self, 'dd', {
            'patch_type': 0,
            'patch_exe': '',
            'patch_sync': True,
            'patch_size': 0,
            'fov': 90,
            'phi': 0,
            'theta': 0,
            'aspect':'1:1',
            'favorites':[]
        })
        try:
            l=json.loads(open('app/sets.json').read())
            object.__setattr__(self, 'dd',l)
        except:pass


    def __getattr__(self, item):
        if item in self.dd:
            return self.dd[item]
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    def __setattr__(self, ind, value):
        if ind == 'dd':
            object.__setattr__(self, ind, value)
        else:
            self.dd[ind] = value

    def save(self):
        with open('app/sets.json', 'w') as f:
            json.dump(self.dd, f, indent=4)




class App:
    def __init__(self,gui=None,sets=None):
        self.gui=gui
        self.file_list=[]
        self.cur_file=0
        self.loaded_image=None
        self.messages = queue.Queue()
        self.icons={}

        self.is_opening=False

        self.sets=sets
        self.cur_sets={'theta':sets.theta,'phi':sets.phi,'fov':sets.fov}
        self.th=threading.Thread(target=self.worker)
        self.th.daemon = True
        self.th.start()

        self.current_time=0
        self.waiter=False
        self.th2=threading.Thread(target=self.worker_waiter)
        self.th2.daemon = True
        self.th2.start()

    def worker(self):
        while True:
            try:
                message = self.messages.get(timeout=1)
                if message['action']=='open':
                    self.th_open(message['data']['path'])
                if message['action']=='get_pers':
                    d=message['data']
                    self.th_pers(d['fov'],d['theta'],d['phi'],d['width'])
                if message['action']=='save_shot':
                    d=message['data']
                    self.th_shot(d['fov'],d['theta'],d['phi'],d['filename'])     
                if message['action']=='start_patch':
                    d=message['data']
                    self.th_patch(d['fov'],d['theta'],d['phi']) 

                if message['action']=='start_batch':
                    d=message['data']
                    self.th_batch(d['fov'],d['theta'],d['phi']) 


                if message['action']=='save_patch':
                    d=message['data']
                    self.th_save()  

                if message['action']=='patch_open':
                    d=message['data']
                    self.patch_open()                                               
                self.messages.task_done()
            except queue.Empty:
                pass
    def th_open(self,path,batch=False):
        self.is_opening=True
        self.loaded_image=E2P.Equirectangular(path)
        self.is_opening=False
        if not batch:
            self.gui.stop_waiter()




    def th_pers(self,fov,theta,phi,width):
        if not self.loaded_image:return
        img = self.loaded_image.GetPerspective(fov, theta, phi, width,width)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.pimg=Image.fromarray(rgb_img)
        self.gui.update_image(self.pimg)

    def th_shot(self,fov,theta,phi,filename):
        if not self.loaded_image:return
        sh=self.loaded_image._img.shape
        width=min(sh[0],sh[1])

        img = self.loaded_image.GetPerspective(fov, theta, phi, width,width)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        del img
        pimg=Image.fromarray(rgb_img)
        del rgb_img
        ratio=(int(self.gui.aspect_var.get().split(':')[0]),int(self.gui.aspect_var.get().split(':')[1]))
        img=self.crop_image_by_ratio(pimg,aspect_ratio=ratio,max_width=width,max_height=width)
        img.save(filename,quality=90,optimize=True)
        del img
        gc.collect()
        self.gui.toast(_('Done!'),_('The snapshot is saved'))
        self.gui.stop_waiter()

    def th_patch(self,fov,theta,phi,batch=False):
        if not self.loaded_image:return
        sh=self.loaded_image._img.shape
        width=min(sh[0],sh[1])
        if self.sets.patch_size==1:
            width=int(width/2)
        if self.sets.patch_size==2:  
            width=int(width/4)
        img = self.loaded_image.GetPerspective(fov, theta, phi, width,width)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        del img
        pimg=Image.fromarray(rgb_img)
        del rgb_img
        ratio=(int(self.gui.aspect_var.get().split(':')[0]),int(self.gui.aspect_var.get().split(':')[1]))
        img=self.crop_image_by_ratio(pimg,aspect_ratio=ratio,max_width=width,max_height=width)
        img.save('app/data/patch.tiff',compression='raw')
        del img
        gc.collect()
        if batch:return
     
        file_path=Path.cwd()/Path('app/data/patch.tiff')
        if self.sets.patch_type==2:
            self.gui.loader_text.set(_('The patch is done!|Edit and save it there.'))

            subprocess.Popen(f'explorer /select,"{file_path}"')

        if self.sets.patch_type==0:
            self.gui.loader_text.set(_('The patch is done!|Edit it in Photoshop|and save it there.'))
            with Session(str(file_path), action="open") as ps:
                pass
        if self.sets.patch_type==1:
            self.gui.loader_text.set(_('The patch is done!|Edit it in editor|and save it there.'))
            subprocess.Popen([f'{self.sets.patch_exe.replace('/','\\')}',f'"{str(file_path)}"'])
        if self.sets.patch_sync==1:
            self.current_time=os.path.getmtime(file_path)
            self.waiter=True
        else:
            self.gui.patch_button.config(state='normal',text=_('Apply patch'))
            self.gui.root.update_idletasks()
        if not batch:
            self.gui.progress.setState('normal')


    def th_batch(self,fov,theta,phi):
        ln=len(self.file_list)
        self.estop=False
        self.gui.progress.setProgress(5)
        for n,f in enumerate(self.file_list):
            if self.estop:break
            self.cur_file=n
            self.gui.rebiuld_file_list()

            pth=f['path']
            self.gui.loader_text.set(f'{n+1}/{ln } '+_('The panorama is being opened...'))
            self.gui.loader_progress.config(value=n)
            if n>0:
                self.gui.progress.setProgress(int(float(n)/float(ln)*100))
            else:
                self.gui.progress.setProgress(5)

            self.gui.root.update_idletasks()
            self.th_open(pth,batch=True)
            self.make_pers()
            self.gui.loader_text.set(f'{n+1}/{ln } '+_('Creating a patch...'))
            self.th_patch(fov,theta,phi,batch=True)
            self.gui.loader_text.set(f'{n+1}/{ln } '+_('Photoshop is working...'))
            with Session(str(Path.cwd()/Path('app/data/patch.tiff')), action="open",auto_close=True) as ps1:
                ps1.app.doAction(action=self.gui.lev2_var.get(),action_from=self.gui.lev1_var.get())
                ps1.active_document.save()
            self.gui.loader_text.set(f'{n+1}/{ln } '+_('Applying patch...'))
            self.patch_open(batch=True)
            self.gui.loader_text.set(f'{n+1}/{ln } '+_('Saving result...'))
            self.th_save(batch=True)
            d=self.file_list[self.cur_file]
            d['done']=True
            self.file_list[self.cur_file]=d
            try:Path.cwd()/Path('app/data/patch.tiff').unlink()
            except:pass

            
        self.gui.stop_waiter()
        self.gui.toast(_('Done!'),_('Batch complete!'))

    def worker_waiter(self):
        file_path=Path.cwd()/Path('app/data/patch.tiff')
        while True:
            if self.waiter:
                if os.path.getmtime(file_path)>self.current_time:
                    self.waiter=False
                    self.patch_open()
            time.sleep(1)         


    def th_save(self,batch=False):
        file_path=self.file_list[self.cur_file]['path']
        pathed_folder = file_path.parent / "pathed"
        pathed_folder.mkdir(parents=True, exist_ok=True)
        new_file_path = pathed_folder / file_path.name
        rgb_img = cv2.cvtColor(self.loaded_image._img, cv2.COLOR_BGR2RGB)
        pimg=Image.fromarray(rgb_img)
        del rgb_img
        gc.collect()
        if file_path.suffix.lower()=='.jpg':
            pimg.save(new_file_path,optimize=True,quality=100)
        else:
            pimg.save(new_file_path)
        del pimg
        gc.collect()
        if not batch:
            self.gui.stop_waiter()
            self.gui.toast(_('Panorama saved'),_('Look for it in the "patched" subdirectory'))
        d=self.file_list[self.cur_file]
        d['done']=True
        self.file_list[self.cur_file]=d
        self.gui.rebiuld_file_list()



    def save_patch(self,batch=False):
        if not batch:
            self.gui.start_waiter(text=_("Saving result..."))

        if self.is_opening:
            with self.messages.mutex:
                self.messages.queue.clear()
        self.messages.put({'action':'save_patch','data':{}})          

    def patch_open_bg(self):
        self.messages.put({'action':'patch_open','data':{}})          


    def patch_open(self,batch=False):
        if not batch:
            self.gui.progress.setState('loading')
            self.gui.loader_text.set(_('Applying patch...'))


        
        self.gui.patch_button.config(state='disable',text=_('Make patch'))


        equ = m_P2E.Perspective([Path.cwd()/Path('app/data/patch.tiff')],
                            [[self.cur_sets['fov'], self.cur_sets['theta'], self.cur_sets['phi']]])   
        img = equ.GetEquirec(self.loaded_image._img,self.loaded_image._img.shape[0],self.loaded_image._img.shape[1])

        success, buffer = cv2.imencode(".bmp", img)
        del img
        del equ
        gc.collect()
        self.loaded_image._img=cv2.imdecode(buffer,cv2.IMREAD_COLOR)
        del buffer
        try:Path.cwd()/Path('app/data/patch.tiff').unlink()
        except:pass
        gc.collect()
        

        if not batch:
            self.gui.stop_waiter()
            self.make_pers(clear=True)




    def crop_image_by_ratio(self,img, aspect_ratio=(16, 9),max_width=100,max_height=100):
        img_width, img_height = img.size
        target_width = min(img_width, int(img_height * (aspect_ratio[0] / aspect_ratio[1])))
        target_height = min(img_height, int(img_width * (aspect_ratio[1] / aspect_ratio[0])))
        left = (img_width - target_width) // 2
        top = (img_height - target_height) // 2
        right = (img_width + target_width) // 2
        bottom = (img_height + target_height) // 2
        cropped_img = img.crop((left, top, right, bottom))
        del img
        gc.collect()
        new_width = min(target_width, max_width)
        new_height = min(target_height, max_height)
        

        if target_width / target_height > max_width / max_height:
            new_height = int(new_width * (target_height / target_width))
        else:
            new_width = int(new_height * (target_width / target_height))
            

        resized_img = cropped_img.resize((new_width, new_height), Image.LANCZOS)
        del cropped_img
        gc.collect()
        return resized_img
        

    def open_pano(self):
        self.messages.put({'action':'open','data':self.file_list[self.cur_file]})

    def make_pers(self,width=1200,clear=False):
        fov=self.cur_sets['fov']
        theta=self.cur_sets['theta']
        phi=self.cur_sets['phi']
        if clear and not self.is_opening:
            with self.messages.mutex:
                self.messages.queue.clear()
        self.messages.put({'action':'get_pers','data':{'fov':fov,'theta':theta,'phi':phi,'width':width}})

    def start_patch(self):
        self.gui.start_waiter(text=_("Creating a patch..."))
        fov=self.cur_sets['fov']
        theta=self.cur_sets['theta']
        phi=self.cur_sets['phi']
        if not self.is_opening:
            with self.messages.mutex:
                self.messages.queue.clear()          
        self.messages.put({'action':'start_patch','data':{'fov':fov,'theta':theta,'phi':phi}})

    def run_batch(self):
        fov=self.cur_sets['fov']
        theta=self.cur_sets['theta']
        phi=self.cur_sets['phi']
        if not self.is_opening:
            with self.messages.mutex:
                self.messages.queue.clear()          
        self.messages.put({'action':'start_batch','data':{'fov':fov,'theta':theta,'phi':phi}})     



    def save_shot(self,filename,clear=True):
        self.gui.start_waiter(text=_('Snapshot is saving...'))
        fov=self.cur_sets['fov']
        theta=self.cur_sets['theta']
        phi=self.cur_sets['phi']
        if clear and not self.is_opening:
            with self.messages.mutex:
                self.messages.queue.clear()   
        self.messages.put({'action':'save_shot','data':{'fov':fov,'theta':theta,'phi':phi,'filename':filename}})

    def on_closing(self):
        self.sets.fov=self.gui.fov_var.get()
        self.sets.phi=self.gui.phi_var.get()
        self.sets.theta=self.gui.theta_var.get()
        self.sets.aspect=self.gui.aspect_var.get()
        self.sets.save()
        try:Path.cwd()/Path('app/data/patch.tiff').unlink()
        except:pass
        self.gui.root.destroy()

    def load_ps_action(self,event=None):
        app = ps.Application()
        self.all_actions=json.loads(app.doJavaScript(open('app/get_actions.js').read()))
        first_level = [x['name'] for x in self.all_actions]
        self.gui.lev1_combo['values']=first_level
        self.gui.lev1_var.set(first_level[0])
        self.select_1_level(event=None)

    def select_1_level(self,event):
        for x in self.all_actions:
            if self.gui.lev1_combo.get()==x['name']:
                self.gui.lev2_combo['values']=x['actions']
                self.gui.lev2_var.set(x['actions'][0])

    def get_icon(self,n):
        fname=self.file_list[n]['path']

        img=Image.open(fname)
        self.file_list[n]={'path':fname,'size':img.size,'done':self.file_list[n]['done']}
        if fname in self.icons:
            return self.icons[fname]
        img.thumbnail((80,40))
        i=ImageTk.PhotoImage(image=img)
        self.icons[fname]=i
        return i
        

    






if __name__=='__main__':
    import threading
    import json
    import time
    import queue
    import gc
    import subprocess
    #from tkinter import Tk
    from ttkbootstrap import *



    from app.gui import *
    import locale
    import os
    import cv2 
    import app.lib.Equirec2Perspec as E2P
    import app.lib.Perspec2Equirec as P2E
    import app.lib.multi_Perspec2Equirec as m_P2E
    from PIL import Image
    from photoshop import Session
    import photoshop.api as ps

    

    root=Window(themename="darkly",hdpi=False)
    root.iconify()
    root.update()

    progress = PyTaskbar.Progress(int(root.wm_frame(), 16))
    progress.init()
    sets=AppSets()
    gui=Gui(root,sets,progress)
    app=App(gui,sets)
    gui.app=app
    root.protocol("WM_DELETE_WINDOW", app.on_closing)




    #prog.setState('loading')
    root.mainloop()


