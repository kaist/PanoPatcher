import sys,os
sys.dont_write_bytecode=True
from pathlib import Path

VERSION='1.30'
PORTABLE=True
APP_DIR=Path(sys.executable).resolve().parent if hasattr(sys,"frozen") else Path(__file__).resolve().parent
if hasattr(sys,"frozen"):
    os.chdir(APP_DIR)
DATA_PATH=APP_DIR/Path('app') if PORTABLE else Path().home()/Path('.panopatcher')

if hasattr(sys,"frozen"):
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    (DATA_PATH/'data').mkdir(parents=True, exist_ok=True)
    p=DATA_PATH/Path('error.txt')
    sys.stderr=open(p,'a+')
else:
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    (DATA_PATH/'data').mkdir(parents=True, exist_ok=True)









class AppSets:
    def __init__(self):
        defaults = {
            'patch_type': 0,
            'patch_exe': '',
            'patch_sync': True,
            'patch_size': 0,
            'fov': 90,
            'phi': 0,
            'theta': 0,
            'aspect':'1:1',
            'favorites':[],
            'autosave':True,
            'ipano_url':'https://ipano.ru',
            'ipano_key':'',
            'ipano_login':'',
        }
        object.__setattr__(self, 'dd', defaults.copy())
        try:
            l=json.loads(open(DATA_PATH/'sets.json').read())
            defaults.update(l)
            if not isinstance(defaults.get('favorites'),list):
                defaults['favorites']=[]
            object.__setattr__(self, 'dd',defaults)
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
        with open(DATA_PATH/'sets.json', 'w') as f:
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
        self.preview_fast=False
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
                    self.th_pers(d['fov'],d['theta'],d['phi'],d['width'],d.get('interpolation'))
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

                if message['action']=='ipano_upload':
                    d=message['data']
                    self.th_ipano_upload(d['project_pk'],d.get('project_name',''))

                if message['action']=='patch_open':
                    d=message['data']
                    self.patch_open()                                               
                self.messages.task_done()
            except queue.Empty:
                pass
    def th_open(self,path,batch=False):
        self.is_opening=True
        subfolder_path = path.parent /"pathed"/path.name
        if subfolder_path.exists():
            path=subfolder_path
        self.loaded_image=E2P.Equirectangular(path)
        self.is_opening=False
        if not batch:
            self.gui.stop_waiter()




    def th_pers(self,fov,theta,phi,width,interpolation=None):
        if not self.loaded_image:return
        if interpolation is None:
            interpolation=cv2.INTER_LINEAR
        if self.is_current_dng():
            img = self.loaded_image.GetPreviewPerspective(fov, theta, phi, width,width, interpolation=interpolation)
        else:
            img = self.loaded_image.GetPerspective(fov, theta, phi, width,width, interpolation=interpolation)
        self.pimg=self.cv_to_pil_preview(img)
        self.gui.update_image(self.pimg)

    def th_shot(self,fov,theta,phi,filename):
        if not self.loaded_image:return
        sh=self.loaded_image._img.shape
        width=min(sh[0],sh[1])

        img = self.loaded_image.GetPerspective(fov, theta, phi, width,width)
        ratio=(int(self.gui.aspect_var.get().split(':')[0]),int(self.gui.aspect_var.get().split(':')[1]))
        if self.is_current_dng():
            img=self.crop_array_by_ratio(img,aspect_ratio=ratio,max_width=width,max_height=width)
            dng_io.write_linear_dng(filename,img,self.loaded_image.dng_metadata)
        else:
            pimg=self.cv_to_pil_preview(img)
            del img
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
        #ratio=(int(self.gui.aspect_var.get().split(':')[0]),int(self.gui.aspect_var.get().split(':')[1]))
        #img=self.crop_image_by_ratio(pimg,aspect_ratio=ratio,max_width=width,max_height=width)
        pimg.save(DATA_PATH/'data/patch.tiff',compression='raw')
        del pimg
        gc.collect()
        if batch:return
     
        file_path=DATA_PATH/'data/patch.tiff'
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
            with Session(str(DATA_PATH/'data/patch.tiff'), action="open",auto_close=True) as ps1:
                ps1.app.doAction(action=self.gui.lev2_var.get(),action_from=self.gui.lev1_var.get())
                ps1.active_document.save()
            self.gui.loader_text.set(f'{n+1}/{ln } '+_('Applying patch...'))
            self.patch_open(batch=True)
            self.gui.loader_text.set(f'{n+1}/{ln } '+_('Saving result...'))
            self.th_save(batch=True)
            d=self.file_list[self.cur_file]
            d['done']=True
            self.file_list[self.cur_file]=d
            try:(DATA_PATH/'data/patch.tiff').unlink()
            except:pass

            
        self.gui.stop_waiter()
        self.gui.toast(_('Done!'),_('Batch complete!'))

    def worker_waiter(self):
        file_path=DATA_PATH/'data/patch.tiff'
        last_seen=None
        while True:
            try:
                if self.waiter:
                    try:
                        mtime=os.path.getmtime(file_path)
                        size=os.path.getsize(file_path)
                    except (FileNotFoundError,PermissionError,OSError):
                        last_seen=None
                        time.sleep(1)
                        continue
                    current=(mtime,size)
                    if mtime>self.current_time and last_seen==current:
                        self.waiter=False
                        last_seen=None
                        self.patch_open_bg()
                    else:
                        last_seen=current
            except Exception as e:
                self.waiter=False
                last_seen=None
                try:
                    sys.stderr.write(f'worker_waiter error: {e}\n')
                except:
                    pass
            time.sleep(1)         


    def th_save(self,batch=False):
        file_path=self.file_list[self.cur_file]['path']
        pathed_folder = file_path.parent / "pathed"
        pathed_folder.mkdir(parents=True, exist_ok=True)
        new_file_path = pathed_folder / file_path.name
        self.cv_save_unicode(new_file_path,self.loaded_image._img)
        if not batch:
            self.gui.stop_waiter()
            self.gui.toast(_('Panorama saved'),_('Look for it in the "patched" subdirectory'))
        d=self.file_list[self.cur_file]
        d['done']=True
        self.file_list[self.cur_file]=d
        self.gui.rebiuld_file_list()

    def get_upload_path(self,item):
        path=item['path']
        patched=path.parent/'pathed'/path.name
        return patched if patched.exists() else path

    def th_ipano_upload(self,project_pk,project_name=''):
        from app.lib.ipano_client import IPanoClient
        self.estop=False
        client=IPanoClient(self.sets.ipano_url,timeout=120)
        files=[]
        for item in self.file_list:
            path=self.get_upload_path(item)
            if path.suffix.lower() not in ('.jpg','.jpeg','.png','.tif','.tiff'):
                continue
            files.append(path)
        if not files:
            self.gui.root.after(0,lambda:self.gui.ipano_upload_done(False,_('No files to upload. DNG is not supported by the site yet.')))
            return
        total=sum(p.stat().st_size for p in files)
        uploaded_base=0
        self.gui.root.after(0,lambda:self.gui.set_upload_progress(0,total))
        try:
            for n,path in enumerate(files,1):
                if self.estop:
                    raise RuntimeError(_('Upload was stopped.'))
                self.gui.root.after(0,lambda n=n,path=path:self.gui.loader_text.set(f'{n}/{len(files)} '+_('Uploading {name}...').format(name=path.name)))
                def progress(sent, request_total, base=uploaded_base):
                    if self.estop:
                        raise RuntimeError(_('Upload was stopped.'))
                    file_sent=min(path.stat().st_size,sent)
                    self.gui.root.after(0,lambda:self.gui.set_upload_progress(base+file_sent,total))
                resp=client.upload_pano(self.sets.ipano_key,project_pk,path,progress=progress)
                if resp.get('error'):
                    raise RuntimeError(resp.get('message') or resp.get('error') or _('Upload failed {name}').format(name=path.name))
                uploaded_base+=path.stat().st_size
                self.gui.root.after(0,lambda:self.gui.set_upload_progress(uploaded_base,total))
            self.gui.root.after(0,lambda:self.gui.ipano_upload_done(True,_('Upload to ipano.ru is complete. Tour {name}').format(name=project_name or project_pk)))
        except Exception as e:
            self.gui.root.after(0,lambda e=e:self.gui.ipano_upload_done(False,str(e)))

    def start_ipano_upload(self,project_pk,project_name=''):
        if not self.file_list:
            return
        if not self.is_opening:
            with self.messages.mutex:
                self.messages.queue.clear()
        self.messages.put({'action':'ipano_upload','data':{'project_pk':project_pk,'project_name':project_name}})



    def save_patch(self,batch=False):
        if self.is_current_dng():
            return
        if not batch:
            self.gui.start_waiter(text=_("Saving result..."))

        if self.is_opening:
            with self.messages.mutex:
                self.messages.queue.clear()
        self.messages.put({'action':'save_patch','data':{}})          

    def cv_save_unicode(self,path,img):
        ext=Path(path).suffix.lower()
        encode_ext=ext
        if ext=='.jpeg':
            encode_ext='.jpg'
        elif ext=='.tiff':
            encode_ext='.tif'
        params=[]
        if ext in ('.jpg','.jpeg'):
            params=[cv2.IMWRITE_JPEG_QUALITY,100]
            if hasattr(cv2,'IMWRITE_JPEG_OPTIMIZE'):
                params.extend([cv2.IMWRITE_JPEG_OPTIMIZE,1])
        success, buffer=cv2.imencode(encode_ext,img,params)
        if not success:
            raise OSError(f'Could not encode image as {ext}')
        buffer.tofile(str(path))

    def patch_open_bg(self):
        if self.is_current_dng():
            return
        self.messages.put({'action':'patch_open','data':{}})          


    def patch_open(self,batch=False):
        if self.is_current_dng():
            return
        if not batch:
            self.gui.progress.setState('loading')
            self.gui.loader_text.set(_('Applying patch...'))


        
        self.gui.patch_button.config(state='disable',text=_('Make patch'))


        equ = m_P2E.Perspective([DATA_PATH/'data/patch.tiff'],
                            [[self.cur_sets['fov'], self.cur_sets['theta'], self.cur_sets['phi']]])   
        equ.GetEquirec(self.loaded_image._img,self.loaded_image._img.shape[0],self.loaded_image._img.shape[1],inplace=True)
        del equ
        gc.collect()
        try:(DATA_PATH/'data/patch.tiff').unlink()
        except:pass
        gc.collect()

        if self.sets.autosave and not batch:
            self.th_save(batch=True)
        

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
        new_width = min(target_width, max_width)
        new_height = min(target_height, max_height)
        

        if target_width / target_height > max_width / max_height:
            new_height = int(new_width * (target_height / target_width))
        else:
            new_width = int(new_height * (target_width / target_height))
            

        resized_img = cropped_img.resize((new_width, new_height), Image.LANCZOS)
        return resized_img

    def crop_array_by_ratio(self,img, aspect_ratio=(16, 9),max_width=100,max_height=100):
        img_height, img_width = img.shape[:2]
        target_width = min(img_width, int(img_height * (aspect_ratio[0] / aspect_ratio[1])))
        target_height = min(img_height, int(img_width * (aspect_ratio[1] / aspect_ratio[0])))
        left = (img_width - target_width) // 2
        top = (img_height - target_height) // 2
        right = (img_width + target_width) // 2
        bottom = (img_height + target_height) // 2
        cropped_img = img[top:bottom, left:right]

        new_width = min(target_width, max_width)
        new_height = min(target_height, max_height)
        if target_width / target_height > max_width / max_height:
            new_height = int(new_width * (target_height / target_width))
        else:
            new_width = int(new_height * (target_width / target_height))

        if new_width != target_width or new_height != target_height:
            return cv2.resize(cropped_img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        return cropped_img.copy()

    def cv_to_pil_preview(self,img):
        if self.is_current_dng():
            return dng_io.linear_bgr_to_pil(img,self.loaded_image.dng_metadata)
        return Image.fromarray(img[:, :, ::-1])

    def is_current_dng(self):
        return bool(self.loaded_image and getattr(self.loaded_image,'is_dng',False))
        

    def open_pano(self):
        if not self.file_list:return
        try:self.file_list[self.cur_file]
        except:return
        
        self.messages.put({'action':'open','data':self.file_list[self.cur_file]})

    def make_pers(self,width=1200,clear=False):
        fov=self.cur_sets['fov']
        theta=self.cur_sets['theta']
        phi=self.cur_sets['phi']
        if width==1200 and self.gui:
            width=self.get_preview_size()
        interpolation=cv2.INTER_NEAREST if self.preview_fast else cv2.INTER_LINEAR
        if clear and not self.is_opening:
            with self.messages.mutex:
                self.messages.queue.clear()
        self.messages.put({'action':'get_pers','data':{'fov':fov,'theta':theta,'phi':phi,'width':width,'interpolation':interpolation}})

    def set_preview_fast(self,enabled):
        self.preview_fast=enabled

    def get_preview_size(self):
        canvas_w, canvas_h = self.gui.win_size
        try:
            ratio_w, ratio_h = [int(i) for i in self.gui.aspect_var.get().split(':')]
            aspect = ratio_w / ratio_h
        except:
            aspect = 1.0

        canvas_aspect = canvas_w / max(1, canvas_h)
        if aspect >= canvas_aspect:
            size = canvas_w
        else:
            size = canvas_h
        max_size = 1600 if self.preview_fast else 2600
        return max(512, min(max_size, int(size)))

    def start_patch(self):
        if self.is_current_dng():
            return
        self.gui.start_waiter(text=_("Creating a patch..."))
        fov=self.cur_sets['fov']
        theta=self.cur_sets['theta']
        phi=self.cur_sets['phi']
        if not self.is_opening:
            with self.messages.mutex:
                self.messages.queue.clear()          
        self.messages.put({'action':'start_patch','data':{'fov':fov,'theta':theta,'phi':phi}})

    def run_batch(self):
        if self.is_current_dng():
            return
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
        try:(DATA_PATH/'data/patch.tiff').unlink()
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

        if fname in self.icons:
            return self.icons[fname]
        thumb_size=(self.gui.u(80),self.gui.u(40))
        if fname.suffix.lower()=='.dng':
            img=dng_io.thumbnail(fname,thumb_size)
            size=dng_io.image_size(fname)
        else:
            img=Image.open(fname)
            size=img.size
        self.file_list[n]={'path':fname,'size':size,'done':self.file_list[n]['done']}
        img.thumbnail(thumb_size)
        i=ImageTk.PhotoImage(image=img)
        self.icons[fname]=i
        return i

    def drop_files(self,event):
        paths = root.tk.splitlist(event.data)
        file_list=[]
        for path in paths:
            if os.path.isfile(path):
                # Проверяем расширение файла
                if path.lower().endswith(('.jpg', '.jpeg','.png', '.tiff', '.tif', '.dng')):
                    file_list.append(path)
            elif os.path.isdir(path):
                # Для папок проверяем все файлы внутри
                for item in os.listdir(path):
                    full_path = os.path.join(path, item)
                    if os.path.isfile(full_path):
                        if full_path.lower().endswith(('.jpg','.png', '.jpeg', '.tiff', '.tif', '.dng')):
                            file_list.append(full_path)
        for f in file_list:
            t={'path':Path(f),'size':[0,0],'done':False}
            self.file_list.append(t)
        self.th=threading.Thread(target=self.gui.rebiuld_file_list)
        self.th.daemon = True
        self.th.start()
        

    






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
    from app.lib import dng_io
    import PIL
    PIL.Image.MAX_IMAGE_PIXELS = 9331200000
    from PIL import Image

    from photoshop import Session
    import photoshop.api as ps
    from tkinterdnd2 import TkinterDnD, DND_FILES


    class CTk(Window, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)



    root=CTk(themename="darkly")
    root.drop_target_register(DND_FILES)

    root.iconify()
    root.update()

    progress = PyTaskbar.Progress(int(root.wm_frame(), 16))
    progress.init()
    sets=AppSets()
    gui=Gui(root,sets,progress,VERSION)
    app=App(gui,sets)
    root.dnd_bind('<<Drop>>', app.drop_files)
    gui.app=app
    gui.build_f_menu()
    root.protocol("WM_DELETE_WINDOW", app.on_closing)




    #prog.setState('loading')
    root.mainloop()


