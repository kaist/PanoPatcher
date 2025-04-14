import sys
import os
import ctypes as ct
from pathlib import Path
from tkinter import *
#from tkinter.ttk import *
from ttkbootstrap import *
from ttkbootstrap.constants import *
from tkinter import filedialog
from tkinter.font import Font
from pathlib import Path
from PIL import Image, ImageTk
from itertools import count
import threading
import PyTaskbar
import locale
import configparser
import builtins


try:
    from win11toast import notify
except:
    notify=None


class Icons:
    def __init__(self):
        self.icons={}

    def init_icons(self):
        for i in Path('app/icons').glob('*.png'):
            self.icons[i.stem]=PhotoImage(file=i)  
                
    def __getattr__(self,fname):

        return self.icons[fname]

icons=Icons()

class Translation:
    def read_f(self,path):
        conf=configparser.ConfigParser()
        try:
            conf.read_file(open(Path(path) / f'{self.lang}.txt', encoding='utf-8'))
        except:return
        for x in conf['LANG']:
            self.trans[x]=conf['LANG'][x]

    def __init__(self):
        self.trans={}
        self.lang, enc = locale.getdefaultlocale()
        self.read_f('app/locale')
        for x in Path('plugins').glob('*'):
            self.read_f(x/'locale')
        builtins.__dict__['_'] = self.translate


    def translate(self,word):
        
        return self.trans.get(word.lower(),word).replace('|','\n')
    
trans=Translation()

def dark_title_bar(window):
    if sys.platform!='win32':return
    window.update()
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    set_window_attribute = ct.windll.dwmapi.DwmSetWindowAttribute
    get_parent = ct.windll.user32.GetParent
    hwnd = get_parent(window.winfo_id())
    rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
    value = 2
    value = ct.c_int(value)
    set_window_attribute(hwnd, rendering_policy, ct.byref(value),
                     ct.sizeof(value))



class ImageLabel(Label):
    def load(self, im):
        if isinstance(im, str):
            im = Image.open(im)
        self.loc = 0
        self.frames = []

        try:
            for i in count(1):
                self.frames.append(ImageTk.PhotoImage(im.copy()))
                im.seek(i)
        except EOFError:
            pass

        try:
            self.delay = im.info['duration']
        except:
            self.delay = 100

        if len(self.frames) == 1:
            self.config(image=self.frames[0])
        else:
            self.next_frame()

    def unload(self):
        self.config(image="")
        self.frames = None

    def next_frame(self):
        if self.frames:
            self.loc += 1
            self.loc %= len(self.frames)
            self.config(image=self.frames[self.loc])
            self.after(self.delay, self.next_frame)


class Gui:
    def __init__(self,root,sets,progress):
        self.root=root
        self.progress=progress

        self.tsets=sets
        self.is_waiter=False
        self.loader_text=StringVar()
        aspect_ratios = [
            "1:1",
            "16:9",
            "9:16",
            "3:2",
            "2:3",
            "4:3",
            "3:4",
            "5:4",
            "4:5"
            ]
        
        #sv_ttk.set_theme("dark")
        self.root.option_add("*tearOff", False)
        icons.init_icons()

        self.style = Style()
        self.style.configure("black.TFrame", background="#000000")
        self.style.configure("black.TLabel", background="#000000")

        self.style.configure("big.primary.TButton", font=("", 14),anchor=W)
        self.style.configure("big.info.TButton", font=("", 14),anchor=W)
        self.style.configure("big.success.TButton", font=("", 14),anchor=W)


        dark_title_bar(self.root)
        self.root.tk.call('wm', 'iconphoto', self.root._w, icons.icon)
        self.root.iconphoto(True, icons.icon)

        try:self.root.state('zoomed')
        except:self.root.attributes('-zoomed', True)
        self.root.title('PanoPatcher')
        scale=self.root.winfo_fpixels('1i')/72
        self.root.tk.call('tk', 'scaling', scale)

        self.root.configure(background='black')
        self.root.update_idletasks()

        self.tools_frame = Frame(self.root, width=300,height=100)
        self.tools_frame.grid(row=0, column=0, sticky="ns")  # Фиксируем слева и растягиваем по Y
        self.tools_frame.grid_propagate(False)

        self.canv_frame = Frame(self.root)
        self.canv_frame.grid(row=0, column=1, sticky="nsew")

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.add_button=Button(self.tools_frame,style='big.primary.TButton',image=icons.add,text=_('Add panoramas'),compound=LEFT,command=self.add_pano_command)
        self.add_button.grid(row=0,column=0,sticky="ew",padx=5,pady=5)
        self.tools_frame.grid_columnconfigure(0, weight=1)

        self.tools_frame.grid_rowconfigure(1, weight=1)  # Растягиваем среднюю строку


        self.f_frame=Frame(self.tools_frame,style='b.TFrame')
        self.f_frame.grid(row=1,column=0,sticky="nsew",padx=5,pady=5)


        self.scr = Scrollbar(self.f_frame, orient = 'vertical')
        self.scr.pack(side =RIGHT, fill = Y)

        self.f_list=Canvas(self.f_frame,yscrollcommand=self.scr.set,width=300,background='#000000')
        self.f_list.pack(side=LEFT,fill=Y,padx=5,pady=5)
        self.scr.config(command=self.f_list.yview)
        self.bind_tree(self.f_frame,"<MouseWheel>", self.plugs_scroll)

        self.exp_frame=Frame(self.tools_frame)
        self.exp_frame.grid(row=2, column=0, sticky="ew")


        # -------------------

        self.patch_frame=Frame(self.exp_frame)
        self.patch_frame.pack(fill=X,expand=True)

        self.patch_button=Button(self.patch_frame,text=_('Make patch'),command=self.start_patch,bootstyle="info",style='big.info.TButton',image=icons.patch,compound=LEFT)
        self.patch_button.pack(side=LEFT,padx=5,pady=5,fill=X,expand=True)

        self.patch_settings_button=Button(self.patch_frame,command=self.show_patch_settings,bootstyle="info-outline",image=icons.settings)
        self.patch_settings_button.pack(side=LEFT,padx=5,pady=5)

        self.save_frame=Frame(self.exp_frame)
        self.save_frame.pack(fill=X,expand=True)

        self.save_button=Button(self.save_frame,text=_('Save the result'),command=self.save_patch,bootstyle="success",style='big.success.TButton',image=icons.save,compound=LEFT)
        self.save_button.pack(padx=5,pady=5,fill=X,expand=True)       

        self.batch_button=Button(self.save_frame,compound='left',bootstyle='info',style='big.info.TButton',text=_('Batch processing in PS'),command=self.show_batch,image=icons.batch)
        self.batch_button.pack(padx=5,fill=X,expand=True,pady=5)


        # -------------------


        self.root.update_idletasks()
        self.win_size=self.canv_frame.winfo_width(),self.canv_frame.winfo_height()
        self.main_canvas=Canvas(self.canv_frame,width=self.win_size[0],height=self.win_size[1])
        self.main_canvas.pack()


        self.theta_var=IntVar(value=self.tsets.theta)
        self.theta_var_id=self.theta_var.trace_add("write", self.round_value_theta)

        self.phi_var=IntVar(value=self.tsets.phi)
        self.phi_var_id=self.phi_var.trace_add("write", self.round_value_phi)

        self.fov_var=IntVar(value=self.tsets.fov)
        self.fov_var_id=self.fov_var.trace_add("write", self.round_value_fov)

        self.theta_slider = Scale(self.canv_frame,
                    length=(self.win_size[0])/2,  # длина в пикселях
                    from_=-180,
                    to=180,
                    variable=self.theta_var,
                    orient='horizontal',
                    command=self.intable_theta,
                )
        self.theta_entry=Entry(self.canv_frame,width=6,textvariable=self.theta_var)


        self.main_canvas.create_window(80,self.win_size[1]-10,anchor=SW,window=self.theta_slider)
        self.main_canvas.create_window(10,self.win_size[1]-10,anchor=SW,window=self.theta_entry)


        self.phi_slider = Scale(self.canv_frame,
                    length=(self.win_size[1])/2,  # длина в пикселях
                    from_=90,
                    to=-90,
                    variable=self.phi_var,
                    orient='vertical',
                    command=self.intable_phi,
                )
        self.phi_entry=Entry(self.canv_frame,width=6,textvariable=self.phi_var)       
        self.main_canvas.create_window(10,self.win_size[1]-90,anchor=SW,window=self.phi_slider)
        self.main_canvas.create_window(10,self.win_size[1]-50,anchor=SW,window=self.phi_entry)


        self.fov_slider = Scale(self.canv_frame,
                    length=(self.win_size[1])/3,  # длина в пикселях
                    from_=20,
                    to=175,
                    variable=self.fov_var,
                    orient='vertical',
                    command=self.intable_fov,
                )
        self.fov_entry=Entry(self.canv_frame,width=6,textvariable=self.fov_var)       
        self.main_canvas.create_window(self.win_size[0]-10,self.win_size[1]-50,anchor=SE,window=self.fov_slider)
        self.main_canvas.create_window(self.win_size[0]-10,self.win_size[1]-10,anchor=SE,window=self.fov_entry)


        self.aspect_var=StringVar(value=self.tsets.aspect)
        self.aspect_var_id=self.aspect_var.trace_add("write", self.round_value_aspect)

        self.aspect_combo=Combobox(self.canv_frame,textvariable=self.aspect_var,values=aspect_ratios,state="readonly")

        self.main_canvas.create_window(self.win_size[0]-80,self.win_size[1]-10,width=70,anchor=SE,window=self.aspect_combo)

        self.main_canvas.bind("<B1-Motion>", self.motion_handler)
        self.main_canvas.bind("<Button-1>", self.click_handler)
        self.main_canvas.bind("<MouseWheel>", self.wheel_handler)
        self.last_x,self.last_y=0,0

        self.screen_button=Button(self.canv_frame,image=icons.shot,command=self.save_image)
        self.main_canvas.create_window(self.win_size[0]-160,self.win_size[1]-10,anchor=SE,window=self.screen_button)

        self.favor_button=Menubutton(self.canv_frame,image=icons.favorite)
        self.main_canvas.create_window(self.win_size[0]-10,10,anchor=NE,window=self.favor_button)

        self.favor_menu = Menu(self.favor_button, tearoff=0,bg="red",foreground='green',relief=FLAT)
        self.build_f_menu()


        self.favor_button.config(menu=self.favor_menu)



        self.start_waiter(initial=True)
        self.root.update_idletasks()
        self.root.deiconify()
       

        self.app=None
        self.root.after(100,self.splash_remove)

   
    def build_f_menu(self):
        self.favor_menu.delete(0,END)
        self.favor_menu.add_command(label="Копировать", command=lambda: print("Копировать"))
        self.favor_menu.add_separator()
        self.favor_menu.add_command(label='В избранное...',image=icons.add_favorite,compound=LEFT)

    def open_favorites(self):
        pass

    def splash_remove(self,event=None):
        try:
            import pyi_splash
            pyi_splash.close()
        except:pass

    def start_waiter(self,text=None,initial=False,batch=False):
        if text:
            self.loader_text.set(text)
        if not initial:
            self.progress.setState('loading')
            self.start_loader(batch)
            self.is_waiter=True
        
        self.aspect_combo.config(state='disabled')
        self.fov_slider.config(state='disabled')
        self.theta_slider.config(state='disabled')
        self.phi_slider.config(state='disabled')
        self.fov_entry.config(state='disabled')
        self.phi_entry.config(state='disabled')
        self.theta_entry.config(state='disabled')
        self.screen_button.config(state='disabled')
        self.patch_button.config(state='disabled')
        self.save_button.config(state='disabled')
        self.batch_button.config(state='disabled')
        self.favor_button.config(state='disabled')

        if not initial:
            self.add_button.config(state='disabled')
        self.patch_settings_button.config(state='disabled')
        self.root.update_idletasks()
        


    def stop_waiter(self,initial=False,batch=False):
        self.is_waiter=False
        if not initial:
            self.progress.setState('normal')
            self.stop_loader()
        self.aspect_combo.config(state='readonly')
        self.fov_slider.config(state='normal')
        self.theta_slider.config(state='normal')
        self.phi_slider.config(state='normal')
        self.fov_entry.config(state='normal')
        self.phi_entry.config(state='normal')
        self.theta_entry.config(state='normal') 
        self.screen_button.config(state='normal')
        self.patch_button.config(state='normal')
        self.save_button.config(state='normal')
        self.batch_button.config(state='normal')
        self.add_button.config(state='normal')
        self.favor_button.config(state='normal')

        self.patch_settings_button.config(state='normal')
        self.root.update_idletasks()
       
    def start_loader(self,batch):
        self.loader_win=Frame(self.canv_frame,width=400,height=300,style='black.TFrame')
        self.loader_win.pack_propagate(False) 
        self.loader_label=ImageLabel(self.loader_win,style='black.TLabel',anchor=CENTER,justify=CENTER,compound=CENTER)
        self.loader_label.load('app/icons/loading.gif')
        self.loader_label.pack(pady=10,padx=10,fill=X,expand=True)
        self.loader_label2=Label(self.loader_win,font=("", 14),style='black.TLabel',width=400,anchor=CENTER,justify=CENTER ,textvariable=self.loader_text)
        self.loader_label2.pack(pady=10,padx=10,fill=X,expand=True)
        if batch:
            self.loader_progress=Progressbar(self.loader_win,maximum=batch,value=0,bootstyle="striped")
            self.loader_progress.pack(padx=10,pady=10,fill=X,expand=True)
            self.stop_button=Button(self.loader_win,text=_('Stop'),image=icons.stop,compound='left',bootstyle='danger',command=self.stop_batch)
            self.stop_button.pack(padx=10,pady=5)

        self.main_canvas.create_window(self.win_size[0]/2, self.win_size[1]/2,tag="loader", window=self.loader_win,anchor=CENTER)
    def stop_loader(self):
        self.main_canvas.delete('loader')

    def stop_batch(self):
        self.stop_button.config(state='disabled')
        self.app.estop=True

    def show_batch(self):
        self.swin=Toplevel(self.root)
        self.swin.title(_('Batch processing'))
        self.swin.grab_set()
        dark_title_bar(self.swin)

        Button(self.swin,text=_('Start batch processing'),command=self.run_batch,bootstyle='info',image=icons.done16,compound=LEFT).grid(row=5,column=0,columnspan=2,padx=10,pady=20)


        Label(self.swin,text=_('Choose a Photoshop action')).grid(row=0,sticky=W,columnspan=2,column=0,padx=10,pady=5)

        self.lev1_var=StringVar()
        self.lev1_var.set(_('waiting photoshop...'))
        self.lev1_combo=Combobox(self.swin,state='readonly',textvariable=self.lev1_var)
        self.lev1_combo.grid(row=1,column=0,padx=10,pady=5)
        self.lev1_combo.bind("<<ComboboxSelected>>", self.app.select_1_level)

        self.lev2_var=StringVar()
        self.lev2_var.set(_('waiting photoshop...'))
        self.lev2_combo=Combobox(self.swin,state='readonly',textvariable=self.lev2_var)
        self.lev2_combo.grid(row=1,column=1,padx=10,pady=5)


        Label(self.swin,text=_('All panoramas will be processed with the current panorama position.')).grid(row=2,column=0,columnspan=2,sticky=W,padx=10,pady=5)


        self.swin.update_idletasks()
        self.swin.place_window_center()




        self.root.after(10,self.app.load_ps_action)

    def run_batch(self):
        self.swin.destroy()
        self.start_waiter(batch=len(self.app.file_list))
        self.app.run_batch()

    def start_patch(self):
        if not self.is_waiter:
            self.app.start_patch()
        else:
            self.app.patch_open_bg()


    def save_patch(self):
        self.app.save_patch()

    def show_patch_settings(self):
        self.swin=Toplevel(self.root)
        self.swin.title(_('Settings'))
        dark_title_bar(self.swin)
        self.sets_path_exe=self.app.sets.patch_exe
        self.sets_path_app_var = IntVar(value=self.app.sets.patch_type)
        self.sets_sync_var=IntVar(value=self.app.sets.patch_sync)

        Radiobutton(
                self.swin,
                text=_("Open the patch in Photoshop"),
                variable=self.sets_path_app_var,
                value=0).grid(row=0,column=0,columnspan=2,padx=10,pady=10,sticky=NW)

        Radiobutton(
                self.swin,
                text=_("Open the patch in another editor"),
                variable=self.sets_path_app_var,
                value=1).grid(row=1,column=0,columnspan=1,padx=10,pady=10,sticky=NW)

        Button(
                self.swin,
                text=_('Select an editor (*.exe)'),
                image=icons.exe,
                bootstyle='secondary',
                compound='left',
                command=self.select_exe_action

            ).grid(row=1,column=1,sticky=NW)

        Radiobutton(
                self.swin,
                text=_("Just show the patch in the explorer"),
                variable=self.sets_path_app_var,
                value=2).grid(row=2,column=0,columnspan=2,padx=10,pady=10,sticky=NW)

        Checkbutton(
                self.swin,
                text=_("Automatically apply patch changes"),
                variable=self.sets_sync_var,
                ).grid(row=3,column=0,columnspan=2,padx=10,pady=10,sticky=NW)

        Label(
            self.swin,
            text=_('Patch size')
            ).grid(row=4,column=0,padx=10,pady=10,sticky=E)

        options = [
                _("Maximum size"),
                _("Half size"),
                _("Quarter size"),
            ] 
        self.sets_size_var=IntVar(value=self.app.sets.patch_size)

        self.sets_combo=Combobox(self.swin,value=options,width=20,state="readonly")
        self.sets_combo.current(self.app.sets.patch_size)
        self.sets_combo.bind("<<ComboboxSelected>>", self.sets_combo_select)
        self.sets_combo.grid(row=4,column=1,padx=10,pady=10,sticky=W)

        Button(self.swin,text=_('Save settings'),command=self.save_sets,bootstyle='primary',image=icons.done16,compound=LEFT).grid(row=5,column=0,columnspan=2,padx=10,pady=20)

        self.swin.update_idletasks()
        self.swin.place_window_center()


    def select_exe_action(self):
        filetypes = (
            (_("The executable file of the editor (exe)"), "*.exe"),
                    )
        file_path = filedialog.askopenfilename(
                title=_("Select executable"),
                filetypes=filetypes,
                multiple=False 
            )  
        self.swin.deiconify()
        if not file_path:return
        self.sets_path_exe=file_path    

    def sets_combo_select(self,event):
        self.sets_size_var.set(self.sets_combo.current())

    def save_sets(self):
        self.app.sets.patch_type=self.sets_path_app_var.get()
        self.app.sets.patch_sync=self.sets_sync_var.get()
        self.app.sets.patch_size=self.sets_size_var.get()
        self.app.sets.patch_exe=self.sets_path_exe
        self.app.sets.save()
        self.swin.destroy()

    def click_handler(self,event):
        if self.is_waiter:return
        self.last_x,self.last_y=event.x,event.y



    def wheel_handler(self,event):
        if self.is_waiter:return
        d=int(-1*(event.delta/120))
        new_d=self.fov_var.get()+d
        if new_d<20:new_d=20
        if new_d>175:new_d=175
        self.fov_var.set(new_d)


    def motion_handler(self,event):
        if self.is_waiter:return
        delta_x=(event.x-self.last_x)
        delta_y=event.y-self.last_y
        self.last_x=event.x
        self.last_y=event.y

        new_theta=int(self.theta_var.get()-(360.0/1200*delta_x))
        if new_theta>180:new_theta-=360
        if new_theta<-180:new_theta+=360

        new_phi=int(self.phi_var.get()-(180.0/1200*delta_y))
        if new_phi>90:new_phi=90
        if new_phi<-90:new_phi=-90


        self.theta_var.set(new_theta)
        self.phi_var.set(new_phi)


    def intable_theta(self,value):
        self.theta_var.trace_remove("write",self.theta_var_id)
        try:self.theta_var.set(int(float(value)))
        except:pass
        self.theta_var_id=self.theta_var.trace_add("write", self.round_value_theta)

    def intable_fov(self,value):
        self.fov_var.trace_remove("write",self.fov_var_id)
        try:self.fov_var.set(int(float(value)))
        except:pass
        self.fov_var_id=self.fov_var.trace_add("write", self.round_value_fov)

    def intable_phi(self,value):
        self.phi_var.trace_remove("write",self.phi_var_id)
        try:self.phi_var.set(int(float(value)))
        except:pass
        self.phi_var_id=self.phi_var.trace_add("write", self.round_value_phi)

    def round_value_theta(self,value,sec,end):
        try:int_value = int(self.theta_var.get())
        except:return
        self.app.cur_sets['theta']=int_value
        self.app.make_pers(clear=True)
        return int_value

    def round_value_aspect(self,value,sec,end):
        self.app.make_pers(clear=True)
  

    def round_value_phi(self,value,sec,end):
        try:int_value = int(self.phi_var.get())
        except:return
        self.app.cur_sets['phi']=int_value
        self.app.make_pers(clear=True)
        return int_value

    def round_value_fov(self,value,sec,end):
        try:int_value = int(self.fov_var.get())
        except:return
        self.app.cur_sets['fov']=int_value
        self.app.make_pers(clear=True)
        return int_value


    def plugs_scroll(self,event):

        self.f_list.yview("scroll",int(-1*(event.delta/120)),"units")
        return "break" 

    def bind_tree(self,widget, event, callback):
        "Binds an event to a widget and all its descendants."
        widget.bind(event, callback)
        for child in widget.children.values():
            self.bind_tree(child, event, callback)


    def save_image(self):
        fname=self.app.file_list[self.app.cur_file]['path'].stem
        fname=f"{fname}_{self.theta_var.get()}_{self.phi_var.get()}_{self.fov_var.get()}_{self.aspect_var.get().replace(':','-')}.jpg"
        filename = filedialog.asksaveasfilename(

            defaultextension=".jpg",
            initialfile=fname,  # предустановленное имя
            filetypes=[("JPG", "*.jpg")],
            title=_("Save a snapshot as...")
              )
        if not filename:return
        self.app.save_shot(filename)

    def add_pano_command(self):
        filetypes = (
            (_("Images"), "*.jpg;*.jpeg;*.png;*.tif;*.tiff"),
                    )
        file_path = filedialog.askopenfilename(
                title=_("Select files with panoramas"),
                filetypes=filetypes,
                multiple=True # Убрать эту опцию, если нужен выбор только одного файла
            )
        if not file_path:return
        for f in file_path:
            t={'path':Path(f),'size':[0,0],'done':False}
            self.app.file_list.append(t)
        self.th=threading.Thread(target=self.rebiuld_file_list)
        self.th.daemon = True
        self.th.start()



    def rebiuld_file_list(self):
        label = Label(self.root, text="")
        fnt =Font(font=('Arial',12,'bold'))
        fnt2 =Font(font=('Arial',8))        
        self.f_list.delete('all')
        self.f_list.config(width=300,height=len(self.app.file_list)*65,scrollregion=(0,0,300,len(self.app.file_list)*65))
        for n,f in enumerate(self.app.file_list):
            clr='#585858'
            w=1
            if n==self.app.cur_file:
                clr='#2e86c1'
                w=2
            self.round_rectangle(self.f_list,8,n*65+4,260,n*65+60,fill='#454545',width=w,outline=clr,tags=(f'addbind{n}',f'numh{n}','hl'))
            self.f_list.create_text(110,n*65+15,text=self.path_to_name(self.app.file_list[n]),anchor=NW,tags=(f'addbind{n}'),fill='white',font=fnt)
            self.f_list.create_image(230,n*65+15,image=icons.delete,anchor=NW,tags=(f'delete{n}'))
            icn=self.app.get_icon(n)
            self.f_list.create_image(15,n*65+10,image=icn,anchor=NW,tags=(f'addbind{n}'))
            if self.app.file_list[n]['done']:
                self.f_list.create_image(20,n*65+15,image=icons.done,anchor=NW,tags=(f'addbind{n}'))


            self.f_list.create_text(110,n*65+35,text=self.get_info(self.app.file_list[n]),anchor=NW,tags=(f'addbind{n}'),fill='white',font=fnt2)


            self.f_list.tag_bind(f'addbind{n}','<Enter>',lambda event, pid=n : self.curs_enter(pid))  
            self.f_list.tag_bind(f'addbind{n}','<Leave>',lambda event, pid=n : self.curs_leave(pid)) 
            self.f_list.tag_bind(f'addbind{n}','<Button-1>',lambda event, pid=n : self.select_action(pid))
            self.f_list.tag_bind(f'delete{n}','<Button-1>',lambda event, pid=n : self.delete_action(pid))
            self.f_list.update_idletasks()

        if not self.app.loaded_image:
            self.start_waiter(text=_('The panorama is being opened...')) 
            self.app.open_pano()
            self.app.make_pers()


    def delete_action(self,n):
        if self.is_waiter:return

        del self.app.file_list[n]
        self.rebiuld_file_list()
        if len(self.app.file_list)==0:
            self.app.loaded_image=None
            self.start_waiter(initial=True)


    
    def get_info(self,n):
        i=n['size']
        return f'{i[0]}x{i[1]} ({i[0]*i[1]/1000000:.1f} mpx)'    


    def path_to_name(self,n):
        p=n['path'].stem
        if '_' in p:
            p=p.split('_')[-1]

        return p[-10:]







            



    def update_image(self,img):
        ratio=(int(self.aspect_var.get().split(':')[0]),int(self.aspect_var.get().split(':')[1]))
        img=self.app.crop_image_by_ratio(img,aspect_ratio=ratio,max_width=self.win_size[0],max_height=self.win_size[1])
        self.main_tk_image=ImageTk.PhotoImage(img)
        self.main_canvas.delete('image')
        self.main_canvas.create_image(self.win_size[0]/2, self.win_size[1]/2,tag="image",image=self.main_tk_image,anchor=CENTER)
        self.main_canvas.update()

    def select_action(self,pid):
        if self.is_waiter:return
        self.app.cur_file=pid
        for item in self.f_list.find_withtag('hl'):
            tags = self.f_list.itemcget(item, 'tags')
            if f'addbind{pid}' in tags:
                self.f_list.itemconfigure(item,outline='#2e86c1',width=2) 
            else:       
                self.f_list.itemconfigure(item,outline='#585858',width=1)
        self.start_waiter(text=_('The panorama is being opened...'))
        self.root.update_idletasks()
        self.app.open_pano()
        self.root.update_idletasks()
        self.app.make_pers()


    def curs_enter(self,num):
        if self.is_waiter:return
        for item in self.f_list.find_withtag('hl'):
            self.f_list.itemconfigure(item,fill='#454545')
        i=self.f_list.find_withtag(f'numh{num}')
        self.f_list.itemconfigure(i,fill='#606060')
        return



    def curs_leave(self,event):
        if self.is_waiter:return
        for item in self.f_list.find_withtag('hl'):
            self.f_list.itemconfigure(item,fill='#454545')



    def round_rectangle(self,canv,x1, y1, x2, y2, radius=25, **kwargs):
            
        points = [x1+radius, y1,
                  x1+radius, y1,
                  x2-radius, y1,
                  x2-radius, y1,
                  x2, y1,
                  x2, y1+radius,
                  x2, y1+radius,
                  x2, y2-radius,
                  x2, y2-radius,
                  x2, y2,
                  x2-radius, y2,
                  x2-radius, y2,
                  x1+radius, y2,
                  x1+radius, y2,
                  x1, y2,
                  x1, y2-radius,
                  x1, y2-radius,
                  x1, y1+radius,
                  x1, y1+radius,
                  x1, y1]

        canv.create_polygon(points, **kwargs, smooth=True)

    def toast(self,title,message):
        try:notify(title,message,app_id='PanoPatcher')
        except:pass