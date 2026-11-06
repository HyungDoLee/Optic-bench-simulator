"""Optical Bench Desktop v0.3 — Tkinter desktop UI (not a web application).

Run: python app.py
Dependency: Pillow (only for the supplied optical-component icons and heatmaps).
"""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from optics import (
    MAX_PROPAGATION_MM, Vec, beam_radius, default_scene, free_space,
    simulate, validate_scene, four_f_scene,
)

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ASSETS = ROOT/'assets'
BG = '#f4f5f6'
PANEL = '#ffffff'
INK = '#28323c'
MUTED = '#6b7680'
LINE = '#dce1e5'
ACCENT = '#356f9c'
RAY = '#bc574d'
LABEL = {'laser':'Laser','lens':'Thin lens','mirror':'Mirror',
         'splitter':'Beam splitter','screen':'Screen',
         'sample':'Sample (specular)', 'probe':'Virtual plane probe'}
FIELD_LABEL = {
    'x':'X [mm]', 'y':'Y [mm]', 'angle':'Normal angle [deg]',
    'lambdaNm':'Wavelength [nm]', 'waistMm':'Input waist [mm]',
    'waistOffsetMm':'Waist offset [mm]', 'powerMw':'Power [mW]',
    'diameterMm':'Aperture diameter [mm]', 'focalMm':'Focal length [mm]',
    'reflectivity':'Reflectivity [0...1]',
    'phaseRad':'Sample phase [rad]', 'periodMm':'Phase period [mm; 0=off]',
    'phaseDepthRad':'Phase modulation [rad]', 'responsivityAW':'Responsivity [A/W; assumed]',
}
FIELDS = {
    'laser':['x','y','angle','lambdaNm','waistMm','waistOffsetMm','powerMw'],
    'lens':['x','y','angle','focalMm','diameterMm'],
    'mirror':['x','y','angle','reflectivity','diameterMm'],
    'splitter':['x','y','angle','reflectivity','diameterMm'],
    'screen':['x','y','angle','diameterMm','responsivityAW'],
    'sample':['x','y','angle','reflectivity','diameterMm','phaseRad','periodMm','phaseDepthRad'],
    'probe':['x','y','angle','diameterMm'],
}


def fmt(x: float, places: int = 2) -> str:
    return f'{x:,.{places}f}' if math.isfinite(x) else '—'


def color_for_normalized_intensity(f: float) -> tuple[int,int,int]:
    # White-to-navy ramp, deliberately neutral and low-saturation.
    f = max(0.0, min(1.0,f))**0.5
    return tuple(round(250*(1-f)+end*f) for end in (36, 91, 145))


def artwork_angle(component: dict) -> float:
    """Native splitter artwork has its coating at +45°, normal at -45°."""
    return float(component.get('angle',0))+(45 if component['type']=='splitter' else 0)


class BenchApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Optical Bench — Python Desktop v0.3')
        self.geometry('1490x920')
        self.minsize(1150,690)
        self.configure(bg=BG)
        self.scene = default_scene()
        self.selected_id: str | None = 'screen-1'
        self.result = simulate(self.scene)
        self.project_file: Path | None = None
        self.drag_id: str | None = None
        self.drag_offset = (0.,0.)
        self.snap = tk.BooleanVar(value=False)
        self.envelope = tk.BooleanVar(value=True)
        self.zoom = tk.DoubleVar(value=1.0)
        self.beam_scale = tk.DoubleVar(value=18.)
        self.selected_branch_index = 0
        self.image_sources = self._load_icons()
        self.image_cache: dict[tuple[str,int], ImageTk.PhotoImage] = {}
        self.icon_refs: list[ImageTk.PhotoImage] = []
        self.heatmap_image: ImageTk.PhotoImage | None = None
        self.property_vars: dict[str,tk.StringVar] = {}
        self.tree_lock = False
        self.origin_x = 0.
        self.origin_y = 0.
        self.mm_scale = 1.
        self.current_readings = []
        self.wave_mode=tk.BooleanVar(value=False)
        self.wave_cache=None
        self.wave_display=None
        self._set_styles()
        self._create_ui()
        self._bind_shortcuts()
        self.notebook.select(self.analysis_tab)
        self._refresh()

    def _set_styles(self):
        style = ttk.Style(self)
        if 'clam' in style.theme_names(): style.theme_use('clam')
        style.configure('.', font=('Segoe UI',10), background=PANEL, foreground=INK)
        style.configure('TFrame',background=PANEL)
        style.configure('TLabel',background=PANEL,foreground=INK)
        style.configure('Muted.TLabel',foreground=MUTED)
        style.configure('Title.TLabel',font=('Segoe UI',13,'bold'))
        style.configure('TButton',padding=(8,6),font=('Segoe UI',9))
        style.configure('Primary.TButton',background='#e7f0f7',foreground='#245a82')
        style.map('Primary.TButton',background=[('active','#d8e8f3')])
        style.configure('Treeview',rowheight=27,background='#fff',fieldbackground='#fff',borderwidth=0)
        style.configure('Treeview.Heading',font=('Segoe UI',9,'bold'))
        style.configure('TNotebook',background=PANEL,borderwidth=0)
        style.configure('TNotebook.Tab',padding=(10,7))
        style.configure('TEntry',padding=5)

    def _load_icons(self) -> dict[str,Image.Image]:
        images = {}
        for name in ('laser','lens','lens_negative','mirror','splitter','screen'):
            p=ASSETS/f'{name}.png'
            if p.is_file(): images[name] = Image.open(p).convert('RGBA')
        return images

    def _component_image(self, c: dict) -> ImageTk.PhotoImage | None:
        kind = 'lens_negative' if c['type']=='lens' and float(c.get('focalMm',1))<0 else c['type']
        if kind == 'sample': kind = 'mirror'
        if kind not in self.image_sources: return None
        angle=int(round(artwork_angle(c)/5)*5)%360
        key=(kind,angle)
        if key not in self.image_cache:
            widths={'laser':56,'lens':20,'lens_negative':20,'mirror':21,'splitter':43,'screen':27}
            heights={'laser':41,'lens':51,'lens_negative':51,'mirror':51,'splitter':43,'screen':51}
            # Pillow rotate uses mathematical CCW on its screen raster; the
            # canvas has +Y down, so use the opposite of the physical angle.
            base=self.image_sources[kind].resize((widths[kind],heights[kind]),Image.Resampling.LANCZOS)
            rotated=base.rotate(-angle,Image.Resampling.BICUBIC,expand=True)
            self.image_cache[key]=ImageTk.PhotoImage(rotated,master=self)
        return self.image_cache[key]

    def _create_ui(self):
        head=tk.Frame(self,bg=PANEL,height=58,highlightthickness=1,highlightbackground=LINE)
        head.pack(fill='x'); head.pack_propagate(False)
        tk.Label(head,text='Optical Bench',font=('Segoe UI',16,'bold'),bg=PANEL,fg=INK).pack(side='left',padx=(17,8))
        tk.Label(head,text='Python desktop  •  ABCD Gaussian  •  2.50 m path cap',
                 font=('Segoe UI',9),bg=PANEL,fg=MUTED).pack(side='left')
        for title,command in [('예제 복원',self._reset),('JSON 열기',self._open),('JSON 저장',self._save)]:
            ttk.Button(head,text=title,command=command).pack(side='right',padx=(1,10 if title=='예제 복원' else 2),pady=11)

        body=tk.PanedWindow(self,orient='horizontal',sashwidth=6,bd=0,background=BG,
                            sashrelief='flat',showhandle=False)
        body.pack(fill='both',expand=True)
        left=tk.Frame(body,bg=PANEL,width=205)
        middle=tk.Frame(body,bg=BG,width=800)
        right=tk.Frame(body,bg=PANEL,width=335)
        body.add(left,minsize=190,width=205,stretch='never')
        body.add(middle,minsize=460,stretch='always')
        body.add(right,minsize=295,width=335,stretch='never')
        self._create_left(left)
        self._create_middle(middle)
        self._create_right(right)
        self.status=tk.StringVar(value='Ready')
        tk.Label(self,textvariable=self.status,anchor='w',bg='#fff',fg=MUTED,
                 bd=0,highlightthickness=1,highlightbackground=LINE,
                 font=('Segoe UI',9),padx=12,pady=5).pack(fill='x')

    def _section_label(self,parent,text):
        tk.Label(parent,text=text,anchor='w',font=('Segoe UI',10,'bold'),
                 fg=INK,bg=PANEL).pack(fill='x',padx=13,pady=(14,7))

    def _create_left(self,parent):
        self._section_label(parent,'OPTICAL COMPONENTS')
        self.tool_icons={}
        ttk.Button(parent,text='Load 720 nm reflection 4f',
                   command=self._load_four_f).pack(fill='x',padx=10,pady=(5,8))
        for kind in ('laser','lens','mirror','splitter','screen','sample','probe'):
            frame=tk.Frame(parent,bg=PANEL)
            frame.pack(fill='x',padx=10,pady=2)
            icon=self._component_image({'type':kind,'angle':0,'focalMm':200})
            if icon: self.tool_icons[kind]=icon
            btn=ttk.Button(frame,text='+  '+LABEL[kind],command=lambda k=kind:self._add(k))
            btn.pack(fill='x')
        ttk.Separator(parent).pack(fill='x',pady=(15,0))
        self._section_label(parent,'COMPONENT LIST')
        cols=('position',)
        self.tree=ttk.Treeview(parent,columns=cols,show='tree headings',selectmode='browse',height=6)
        self.tree.heading('#0',text='Name',anchor='w');self.tree.heading('position',text='(X,Y) mm')
        self.tree.column('#0',minwidth=85,width=92,stretch=False)
        self.tree.column('position',minwidth=72,width=79,stretch=True,anchor='e')
        self.tree.pack(fill='both',expand=True,padx=9,pady=3)
        self.tree.bind('<<TreeviewSelect>>',self._on_tree_select)
        ttk.Button(parent,text='선택 부품 삭제',command=self._remove).pack(fill='x',padx=9,pady=(5,14))
        ttk.Separator(parent).pack(fill='x')
        self._section_label(parent,'VIEW OPTIONS')
        ttk.Checkbutton(parent,text='Gaussian envelope',variable=self.envelope,
                        command=self._draw_board).pack(anchor='w',padx=13,pady=3)
        ttk.Checkbutton(parent,text='25 mm 홀에 스냅',variable=self.snap).pack(anchor='w',padx=13,pady=3)
        tk.Label(parent,text='Envelope exaggeration',bg=PANEL,fg=MUTED,
                 font=('Segoe UI',9)).pack(anchor='w',padx=13,pady=(10,0))
        ttk.Scale(parent,from_=1,to=45,variable=self.beam_scale,
                  command=lambda _=None:self._draw_board()).pack(fill='x',padx=12,pady=(1,4))
        tk.Label(parent,text='좌클릭 선택 · 드래그 이동\nR / Shift+R 회전 · Delete 삭제',
                 justify='left',bg=PANEL,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w',padx=13,pady=(13,12))

    def _create_middle(self,parent):
        options=tk.Frame(parent,bg=BG)
        options.pack(fill='x',padx=16,pady=(12,6))
        tk.Label(options,text='Optical breadboard',bg=BG,fg=INK,
                 font=('Segoe UI',13,'bold')).pack(side='left')
        tk.Label(options,text='1200 × 900 mm  |  holes 25 mm',
                 bg=BG,fg=MUTED,font=('Segoe UI',9)).pack(side='left',padx=12)
        tk.Label(options,text='Zoom',bg=BG,fg=MUTED).pack(side='right')
        ttk.Scale(options,from_=0.8,to=1.25,variable=self.zoom,
                  command=lambda _=None:self._draw_board()).pack(side='right',padx=(3,12))
        board_border=tk.Frame(parent,bg='#dadfe4',bd=0,padx=1,pady=1)
        board_border.pack(fill='both',expand=True,padx=16,pady=(2,10))
        self.board=tk.Canvas(board_border,bg='#f9fafb',highlightthickness=0,cursor='crosshair')
        self.board.pack(fill='both',expand=True)
        self.board.bind('<Configure>',lambda _e:self._draw_board())
        self.board.bind('<ButtonPress-1>',self._mouse_down)
        self.board.bind('<B1-Motion>',self._mouse_move)
        self.board.bind('<ButtonRelease-1>',self._mouse_up)
        self.board.bind('<Motion>',self._mouse_hover)
        bottom=tk.Frame(parent,bg=PANEL,height=182,highlightthickness=1,highlightbackground=LINE)
        bottom.pack(fill='x',padx=16,pady=(0,12));bottom.pack_propagate(False)
        caption=tk.Frame(bottom,bg=PANEL)
        caption.pack(fill='x',padx=12,pady=(8,0))
        tk.Label(caption,text='Beam radius along optical path',bg=PANEL,fg=INK,
                 font=('Segoe UI',10,'bold')).pack(side='left')
        tk.Label(caption,text='w(s)  ·  1/e² radius',bg=PANEL,fg=MUTED,
                 font=('Segoe UI',9)).pack(side='right')
        self.radius_graph=tk.Canvas(bottom,bg=PANEL,height=143,highlightthickness=0)
        self.radius_graph.pack(fill='both',expand=True,padx=8,pady=(0,7))
        self.radius_graph.bind('<Configure>',lambda _e:self._draw_radius_graph())

    def _create_right(self,parent):
        notebook=ttk.Notebook(parent)
        notebook.pack(fill='both',expand=True,padx=8,pady=8)
        self.notebook=notebook
        self.properties_tab=tk.Frame(notebook,bg=PANEL)
        self.analysis_tab=tk.Frame(notebook,bg=PANEL)
        notebook.add(self.properties_tab,text='Properties')
        notebook.add(self.analysis_tab,text='Screen profile')
        self.props_holder=tk.Frame(self.properties_tab,bg=PANEL)
        self.props_holder.pack(fill='both',expand=True,padx=9,pady=7)
        self._section_label(self.analysis_tab,'SCREEN BEAM PROFILE')
        self.analysis_status=tk.StringVar(value='Screen을 선택하세요')
        self.analysis_state=tk.Label(self.analysis_tab,textvariable=self.analysis_status,
            bg='#eef3f7',fg='#426077',wraplength=280,justify='left',anchor='w',
            font=('Segoe UI',9),padx=8,pady=8)
        self.analysis_state.pack(fill='x',padx=10,pady=3)
        branch_row=tk.Frame(self.analysis_tab,bg=PANEL)
        branch_row.pack(fill='x',padx=10,pady=(8,3))
        tk.Label(branch_row,text='Detected branch',bg=PANEL,fg=MUTED).pack(side='left')
        self.branch_combo=ttk.Combobox(branch_row,state='readonly',width=18)
        self.branch_combo.pack(side='right')
        self.branch_combo.bind('<<ComboboxSelected>>',self._branch_changed)
        ttk.Checkbutton(self.analysis_tab,text='Scalar wave profile (FFT/ASM)',
                        variable=self.wave_mode,command=self._render_screen).pack(anchor='w',padx=12,pady=4)
        tk.Label(self.analysis_tab,text='2D intensity  ·  I / I₀',bg=PANEL,fg=INK,
                 font=('Segoe UI',9,'bold')).pack(anchor='w',padx=13,pady=(8,3))
        self.heatmap=tk.Canvas(self.analysis_tab,width=264,height=250,bg='#fff',highlightthickness=1,
                               highlightbackground=LINE)
        self.heatmap.pack(padx=10,pady=0,fill='x')
        tk.Label(self.analysis_tab,text='1D profile  ·  screen-local u',bg=PANEL,fg=INK,
                 font=('Segoe UI',9,'bold')).pack(anchor='w',padx=13,pady=(12,3))
        self.profile=tk.Canvas(self.analysis_tab,height=145,bg='#fff',highlightthickness=1,
                               highlightbackground=LINE)
        self.profile.pack(padx=10,fill='x')
        self.profile.bind('<Configure>',lambda _e:self._render_screen())
        self.readout=tk.StringVar(value='—')
        tk.Label(self.analysis_tab,textvariable=self.readout,justify='left',anchor='nw',
                 bg=PANEL,fg=INK,font=('Consolas',9),wraplength=280).pack(fill='x',padx=12,pady=(11,2))
        tk.Label(self.analysis_tab,
          text='q: ideal Gaussian. Wave: scalar local planes;\nno RCWA, polarization or branch interference.',
          bg=PANEL,fg=MUTED,justify='left',font=('Segoe UI',8)).pack(anchor='w',padx=12,pady=(5,10))

    def _bind_shortcuts(self):
        self.bind('<Control-s>',lambda _e:self._save())
        self.bind('<Control-o>',lambda _e:self._open())
        self.bind('<Delete>',lambda _e:self._remove())
        self.bind('<KeyPress-r>',lambda _e:self._rotate(5))
        self.bind('<KeyPress-R>',lambda _e:self._rotate(-5))

    def _component(self, id_: str | None):
        return next((c for c in self.scene['components'] if c['id']==id_),None)

    def _select(self,id_:str | None):
        if id_ == self.selected_id:
            current=self._component(id_)
            if current and current['type'] in ('screen','sample','probe'):
                self.notebook.select(self.analysis_tab)
                self._render_screen()
            return
        self.selected_id=id_
        self.selected_branch_index=0
        self._render_tree()
        self._render_properties()
        c=self._component(id_)
        if c and c['type'] in ('screen','sample','probe'): self.notebook.select(self.analysis_tab)
        else: self.notebook.select(self.properties_tab)
        self._draw_board()
        self._render_screen()
        self._draw_radius_graph()

    def _add(self,kind:str):
        count=1
        ids={c['id'] for c in self.scene['components']}
        while f'{kind}-{count}' in ids: count+=1
        x=min(self.scene['table']['widthMm']-40,250.+count*35)
        y=min(self.scene['table']['heightMm']-40,220.+count*30)
        c=dict(id=f'{kind}-{count}',type=kind,x=x,y=y,angle=0.,diameterMm=25.4)
        if kind=='laser': c.update(lambdaNm=780.,waistMm=1.,waistOffsetMm=0.,powerMw=10.)
        if kind=='lens': c.update(focalMm=200.)
        if kind=='mirror': c.update(angle=-45.,reflectivity=1.)
        if kind=='splitter': c.update(angle=-45.,reflectivity=.5)
        if kind=='sample': c.update(reflectivity=.8)
        self.scene['components'].append(c)
        self._select(c['id'])
        self._refresh()

    def _remove(self):
        if self.focus_get() and isinstance(self.focus_get(),tk.Entry): return
        if not self.selected_id: return
        self.scene['components']=[c for c in self.scene['components'] if c['id']!=self.selected_id]
        self.selected_id=None
        self._refresh()

    def _rotate(self,delta:float):
        if isinstance(self.focus_get(),(tk.Entry,ttk.Entry)): return
        c=self._component(self.selected_id)
        if c:
            c['angle']=(float(c.get('angle',0))+delta+180)%360-180
            self._refresh()

    def _reset(self):
        if not messagebox.askyesno('예제 복원','현재 배치를 기본 예제로 바꿀까요?'): return
        self.scene=default_scene();self.selected_id='screen-1';self.selected_branch_index=0
        self.project_file=None
        self._refresh()

    def _load_four_f(self):
        if not messagebox.askyesno('720 nm reflection 4f',
                                  'Replace current layout with the 720 nm 4f example?'):
            return
        self.scene=four_f_scene()
        self.selected_id='return-screen'
        self.selected_branch_index=0
        self.project_file=None
        self._refresh()
        self.notebook.select(self.analysis_tab)

    def _open(self):
        file=filedialog.askopenfilename(title='Optical bench JSON 열기',filetypes=[('JSON scene','*.json'),('All files','*.*')])
        if not file:return
        try:
            with open(file,encoding='utf-8') as f: scene=validate_scene(json.load(f))
            self.scene=scene
            self.project_file=Path(file)
            self.selected_id=next((c['id'] for c in scene['components'] if c['type']=='screen'),
                scene['components'][0]['id'] if scene['components'] else None)
            self.selected_branch_index=0
            self._refresh()
        except Exception as e:
            messagebox.showerror('열기 실패',f'JSON을 읽을 수 없습니다:\n{e}')

    def _save(self):
        file=filedialog.asksaveasfilename(title='Optical bench JSON 저장',
            initialfile=self.project_file.name if self.project_file else 'optical_bench.json',
            defaultextension='.json',filetypes=[('JSON scene','*.json')])
        if not file:return
        try:
            with open(file,'w',encoding='utf-8') as f:
                json.dump(self.scene,f,ensure_ascii=False,indent=2)
            self.project_file=Path(file)
            self.status.set(f'Saved: {self.project_file}')
        except OSError as e:
            messagebox.showerror('저장 실패',str(e))

    def _refresh(self, update_inspector=True):
        try:self.result=simulate(self.scene)
        except Exception as error:
            messagebox.showerror('계산 실패',str(error));return
        self._render_tree()
        if update_inspector:self._render_properties()
        self._draw_board()
        self._render_screen()
        self._draw_radius_graph()
        self.status.set(f'{len(self.scene["components"])} elements  |  {len(self.result.segments)} segments  |  '
                        f'{len(self.result.screens)} screen hits  |  {self.result.capped} capped at 2.5 m  |  '
                        f'{len(self.result.warnings)} warnings')

    def _render_tree(self):
        self.tree_lock=True
        existing=self.tree.get_children()
        if existing:self.tree.delete(*existing)
        for c in self.scene['components']:
            self.tree.insert('',tk.END,iid=c['id'],text=LABEL[c['type']],
                             values=(f'{c["x"]:.0f}, {c["y"]:.0f}',))
        if self.selected_id and self.tree.exists(self.selected_id):
            self.tree.selection_set(self.selected_id)
            self.tree.see(self.selected_id)
        self.tree_lock=False

    def _on_tree_select(self,_event):
        if self.tree_lock:return
        choice=self.tree.selection()
        if choice:self._select(choice[0])

    def _render_properties(self):
        for child in self.props_holder.winfo_children():child.destroy()
        self.property_vars={}
        c=self._component(self.selected_id)
        if not c:
            tk.Label(self.props_holder,text='부품을 클릭해서 선택하세요.',bg=PANEL,fg=MUTED).pack(anchor='w',pady=10)
            return
        tk.Label(self.props_holder,text=LABEL[c['type']],font=('Segoe UI',13,'bold'),
                 bg=PANEL,fg=INK).pack(anchor='w',pady=(4,3))
        tk.Label(self.props_holder,text=c['id'],bg=PANEL,fg=MUTED).pack(anchor='w',pady=(0,14))
        for key in FIELDS[c['type']]:
            ttk.Label(self.props_holder,text=FIELD_LABEL[key],style='Muted.TLabel').pack(anchor='w',pady=(6,2))
            variable=tk.StringVar(value=f'{c.get(key,0):g}')
            self.property_vars[key]=variable
            entry=ttk.Entry(self.props_holder,textvariable=variable)
            entry.pack(fill='x')
            entry.bind('<Return>',lambda _e:self._commit_props())
        ttk.Button(self.props_holder,text='Apply parameters',style='Primary.TButton',
                   command=self._commit_props).pack(fill='x',pady=(16,6))
        tk.Label(self.props_holder,text='회전각은 광학 소자의 법선 방향 기준입니다.\n'
            '렌즈는 이상적인 thin lens 근사로 계산합니다.',bg=PANEL,fg=MUTED,
            font=('Segoe UI',8),justify='left',wraplength=270).pack(anchor='w',pady=10)
        if self.result.warnings:
            ttk.Separator(self.props_holder).pack(fill='x',pady=12)
            ttk.Label(self.props_holder,text='경고',style='Muted.TLabel').pack(anchor='w',pady=(0,6))
            tk.Label(self.props_holder,text='\n'.join(self.result.warnings[:4]),
                bg=PANEL,fg='#9a5c36',justify='left',wraplength=280).pack(anchor='w')

    def _commit_props(self):
        c=self._component(self.selected_id)
        if not c:return
        updated=c.copy()
        try:
            for key,v in self.property_vars.items():updated[key]=float(v.get().strip())
            if any(not math.isfinite(x) for x in (updated[k] for k in self.property_vars)):
                raise ValueError('NaN / Infinity is not allowed')
            t=self.scene['table']
            if not (0<=updated['x']<=t['widthMm'] and 0<=updated['y']<=t['heightMm']):
                raise ValueError('X/Y must lie within the table')
            if updated.get('diameterMm',1)<=0:raise ValueError('Aperture must be > 0')
            if c['type']=='lens' and abs(updated['focalMm'])<1e-12:raise ValueError('f must be nonzero')
            if c['type']=='laser' and (updated['lambdaNm']<=0 or updated['waistMm']<=0 or updated['powerMw']<0):
                raise ValueError('Invalid laser parameters')
            if c['type'] in ('mirror','splitter','sample') and not (0<=updated['reflectivity']<=1):
                raise ValueError('Reflectivity must be between 0 and 1')
            if updated.get('periodMm',0)<0 or updated.get('responsivityAW',0)<0:
                raise ValueError('Period and responsivity must be nonnegative')
        except ValueError as error:
            messagebox.showwarning('입력 확인',str(error));self._render_properties();return
        c.clear();c.update(updated)
        self._refresh()

    def _coordinates(self):
        width=self.board.winfo_width();height=self.board.winfo_height()
        table=self.scene['table']
        if width<10 or height<10:return False
        self.mm_scale=min((width-56)/table['widthMm'],(height-56)/table['heightMm'])*self.zoom.get()
        self.origin_x=(width-table['widthMm']*self.mm_scale)/2
        self.origin_y=(height-table['heightMm']*self.mm_scale)/2
        return True

    def _xy(self,p:Vec | tuple[float,float]):
        x,y=(p.x,p.y) if isinstance(p,Vec) else p
        return self.origin_x + x*self.mm_scale,self.origin_y + y*self.mm_scale

    def _mm(self,x:float,y:float):
        return (x-self.origin_x)/self.mm_scale,(y-self.origin_y)/self.mm_scale

    def _draw_board(self):
        if not hasattr(self,'board') or not self._coordinates():return
        canvas=self.board
        canvas.delete('all')
        table=self.scene['table'];w=table['widthMm'];h=table['heightMm']
        x0,y0=self._xy((0,0));x1,y1=self._xy((w,h))
        canvas.create_rectangle(x0,y0,x1,y1,fill='#f4f6f8',outline='#bbc3ca',width=1.4)
        spacing=table.get('holeSpacingMm',25)
        if spacing>0 and self.mm_scale*spacing>=7:
            for i in range(0,int(w//spacing)+1):
                for j in range(0,int(h//spacing)+1):
                    x,y=self._xy((i*spacing,j*spacing))
                    canvas.create_oval(x-1.15,y-1.15,x+1.15,y+1.15,fill='#cbd2d8',outline='')
        if self.envelope.get():
            for seg in self.result.segments:
                N=max(2,min(55,int(seg.length_mm/12)+2))
                top=[];bottom=[]
                for j in range(N+1):
                    distance=seg.length_mm*j/N
                    p=seg.start+seg.direction*distance
                    wmm=beam_radius(free_space(seg.q_start,distance),seg.wavelength_nm)
                    # Enlarged ONLY for visibility on board; physics is unscaled.
                    v=wmm*self.beam_scale.get()*self.mm_scale
                    tangent=Vec(-seg.direction.y,seg.direction.x)
                    cx,cy=self._xy(p)
                    top += [cx+tangent.x*v,cy+tangent.y*v]
                    bottom += [cx-tangent.x*v,cy-tangent.y*v]
                points=top[:]
                for k in reversed(range(0,len(bottom),2)):points.extend(bottom[k:k+2])
                if len(points)>=6:canvas.create_polygon(*points,fill='#f5ddda',outline='')
        for seg in self.result.segments:
            x0,y0=self._xy(seg.start);x1,y1=self._xy(seg.end)
            canvas.create_line(x0,y0,x1,y1,fill=RAY,width=2)
        for marker in self.result.markers:
            x,y=self._xy(marker.point)
            if marker.kind=='waist':
                canvas.create_oval(x-4,y-4,x+4,y+4,fill='#c29341',outline='#fff',width=1)
            elif marker.kind=='limit':
                canvas.create_line(x-6,y-6,x+6,y+6,fill='#af3e35',width=2)
                canvas.create_line(x-6,y+6,x+6,y-6,fill='#af3e35',width=2)
        self.icon_refs=[]
        for c in self.scene['components']:
            x,y=self._xy((c['x'],c['y']))
            if c['id']==self.selected_id:
                canvas.create_oval(x-34,y-34,x+34,y+34,outline=ACCENT,width=1.4,dash=(3,3))
            icon=self._component_image(c)
            if icon:
                self.icon_refs.append(icon)
                canvas.create_image(x,y,image=icon)
            elif c['type']=='probe':
                angle=math.radians(c.get('angle',0))
                tx,ty=-math.sin(angle)*24,math.cos(angle)*24
                canvas.create_line(x-tx,y-ty,x+tx,y+ty,fill='#607e63',dash=(4,3),width=2)
            else:
                canvas.create_oval(x-9,y-9,x+9,y+9,fill='#dce5eb',outline=ACCENT)
            if c['type']!='laser':
                angle=math.radians(c.get('angle',0))
                length=13
                nx=math.cos(angle);ny=math.sin(angle)
                canvas.create_line(x,y,x+nx*length,y+ny*length,fill='#477da4',width=1.5,arrow='last',arrowshape=(5,6,3))
                if c['type']=='splitter':
                    # The coating line is explicitly tangent to the PHYSICAL normal.
                    tx,ty=-ny*21,nx*21
                    canvas.create_line(x-tx,y-ty,x+tx,y+ty,fill='#345965',width=2,
                                       tags=('splitter-interface',))
            canvas.create_text(x,y-37 if c['type']=='probe' else y+37,
                               text=c['id'],font=('Segoe UI',9),fill=INK)
        board_x,board_y=self._xy((0,0))
        canvas.create_rectangle(board_x+8,board_y+8,board_x+176,board_y+31,fill='#fff',outline='#dce2e6')
        canvas.create_text(board_x+17,board_y+19,text='Gaussian ray  /  top view',anchor='w',
                           font=('Segoe UI',8),fill=MUTED)

    def _find_nearest_component(self,ex:float,ey:float):
        nearest=None;score=32.**2
        for c in self.scene['components']:
            x,y=self._xy((c['x'],c['y']))
            dist=(x-ex)**2+(y-ey)**2
            if dist<score: nearest=c;score=dist
        return nearest

    def _mouse_down(self,event):
        c=self._find_nearest_component(event.x,event.y)
        if c:
            self._select(c['id'])
            self.drag_id=c['id']
            mx,my=self._mm(event.x,event.y)
            self.drag_offset=(c['x']-mx,c['y']-my)
        else:
            self.drag_id=None
            self._select(None)

    def _mouse_move(self,event):
        if not self.drag_id:return
        c=self._component(self.drag_id)
        if not c:return
        mx,my=self._mm(event.x,event.y)
        x=mx+self.drag_offset[0];y=my+self.drag_offset[1]
        if self.snap.get():
            spacing=self.scene['table']['holeSpacingMm']
            if spacing>0:x=round(x/spacing)*spacing;y=round(y/spacing)*spacing
        c['x']=max(0.,min(self.scene['table']['widthMm'],x))
        c['y']=max(0.,min(self.scene['table']['heightMm'],y))
        self.result=simulate(self.scene)
        self._draw_board();self._render_screen();self._draw_radius_graph()
        if 'x' in self.property_vars:self.property_vars['x'].set(f'{c["x"]:.1f}')
        if 'y' in self.property_vars:self.property_vars['y'].set(f'{c["y"]:.1f}')

    def _mouse_up(self,_event):
        if self.drag_id:self._refresh(update_inspector=False)
        self.drag_id=None

    def _mouse_hover(self,event):
        if self.drag_id:return
        if self.mm_scale>0:
            x,y=self._mm(event.x,event.y)
            if 0<=x<=self.scene['table']['widthMm'] and 0<=y<=self.scene['table']['heightMm']:
                self.status.set(f'Cursor: ({x:.1f}, {y:.1f}) mm  |  '
                    f'{len(self.result.screens)} screen hits  |  Cumulative path limit: 2500 mm')

    def _screen_selection(self):
        c=self._component(self.selected_id)
        if not c or c['type'] not in ('screen','sample','probe'):return []
        pool={'screen':self.result.screens,'sample':self.result.samples,
              'probe':self.result.probes}[c['type']]
        return [r for r in pool if r.screen_id==c['id']]

    def _branch_changed(self,_event):
        self.selected_branch_index=max(0,self.branch_combo.current())
        self._render_screen()
        self._draw_radius_graph()

    def _render_screen(self):
        if not hasattr(self,'analysis_status'):return
        readings=self._screen_selection()
        self.wave_display=None
        self.current_readings=readings
        self.branch_combo['values']=[f'Branch {r.branch_id} / {r.source_id}' for r in readings]
        if not readings:
            self.selected_branch_index=0
            self.branch_combo.set('')
            c=self._component(self.selected_id)
            self.analysis_status.set('화면에 빔이 도달하지 않았음.\n렌즈·미러·Screen 위치와 2.5 m 제한을 확인하세요.'
                if c and c['type']=='screen' else 'Breadboard에서 Screen을 클릭하세요.')
            self.readout.set('No beam detected')
            self.heatmap.delete('all');self.profile.delete('all')
            self.heatmap.create_text(130,110,text='No beam',fill=MUTED,font=('Segoe UI',11))
            self.profile.create_text(125,67,text='No beam',fill=MUTED,font=('Segoe UI',10))
            return
        self.selected_branch_index=min(self.selected_branch_index,len(readings)-1)
        self.branch_combo.current(self.selected_branch_index)
        r=readings[self.selected_branch_index]
        if self.wave_mode.get():
            try:
                from wave_optics import trace_wave
                key=(json.dumps(self.scene,sort_keys=True),r.screen_id,r.branch_id,r.path_mm)
                if self.wave_cache is None or self.wave_cache[0]!=key:
                    self.wave_cache=(key,trace_wave(self.scene,self.result,r))
                self.wave_display=self.wave_cache[1]
            except (ValueError,ImportError) as error:
                self.analysis_status.set('Wave unavailable: '+str(error))
                self.readout.set('q/ray result retained; wave profile not computed.')
                self.heatmap.delete('all');self.profile.delete('all')
                return
        self.analysis_status.set(f'Beam detected  •  {r.source_id}  •  branch {r.branch_id}')
        self.readout.set(
            f'Path length     {fmt(r.path_mm,1):>9} mm\n'
            f'Radius w        {fmt(r.beam_radius_mm,4):>9} mm\n'
            f'Projected w(u)  {fmt(r.projected_radius_mm,4):>9} mm\n'
            f'Power (input)   {fmt(r.power_mw,4):>9} mW\n'
            f'Peak irradiance {fmt(r.peak_irradiance_w_m2,1):>9} W/m²\n'
            f'Incidence       {fmt(r.incidence_deg,1):>9} deg\n'
            f'Spot offset     {fmt(r.offset_mm,3):>9} mm\n'
            f'q [mm]  {r.q.real:.4g} + {r.q.imag:.4g}i\n'
            f'ABCD (source -> plane)\n'
            f'[{r.abcd.a:.4g}, {r.abcd.b:.4g} mm]\n'
            f'[{r.abcd.c:.4g}/mm, {r.abcd.d:.4g}]')
        if self.wave_display is not None:
            v=self.wave_display
            from wave_optics import second_moment_radius
            import numpy as np
            radii=second_moment_radius(v['field'],v['grid'])
            target=self._component(r.screen_id)
            current=f'{v["current_a"]:.6g} A' if target.get('responsivityAW',0)>0 else 'not configured'
            self.analysis_status.set('Scalar ASM: finite pupils + complex sample')
            self.readout.set(
                f'Path           {r.path_mm:.6g} mm\n'
                f'q ideal w      {r.beam_radius_mm:.6g} mm\n'
                f'q [mm] {r.q.real:.4g}+{r.q.imag:.4g}i\n'
                f'q R            {r.wavefront_radius_mm:.6g} mm\n'
                f'ABCD source -> plane\n'
                f'[{r.abcd.a:.4g}, {r.abcd.b:.4g} mm]\n'
                f'[{r.abcd.c:.4g}/mm, {r.abcd.d:.4g}]\n'
                f'Wave 2σ u,v    {radii[0]:.5g}, {radii[1]:.5g} mm\n'
                f'Wave incident  {v["incident_power_mw"]:.6g} mW'
                f'\nCollected      {v["collected_power_mw"]:.6g} mW'
                f'\nPD current     {current}'
                f'\nWave peak      {float(np.max(abs(v["field"])**2))*1000:.6g} W/m²')
        self._draw_heatmap(r)
        self._draw_profile(r)

    def _plot_halfspan(self,r):
        return max(.4,3.35*r.projected_radius_mm,abs(r.offset_mm)+2.5*r.projected_radius_mm)

    def _draw_heatmap(self,r):
        if self.wave_display is not None:
            self._draw_wave_profile()
            return
        c=self.heatmap;c.delete('all')
        # The heatmap shows a chosen field of view centered at SCREEN center;
        # this is not the actual finite screen aperture boundary.
        half=self._plot_halfspan(r)
        n=110;px=212;py=212
        rgb=Image.new('RGB',(n,n))
        pix=rgb.load()
        for j in range(n):
            v=half*(1-2*j/(n-1))
            for i in range(n):
                u=half*(2*i/(n-1)-1)
                pix[i,j]=color_for_normalized_intensity(r.relative_intensity(u,v))
        self.heatmap_image=ImageTk.PhotoImage(rgb.resize((px,py),Image.Resampling.BILINEAR),master=self)
        width=max(c.winfo_width(),258)
        left=(width-px)/2;top=4
        c.create_image(left,top,image=self.heatmap_image,anchor='nw')
        c.create_rectangle(left,top,left+px,top+py,outline='#a9b2bb')
        # White circle is intentionally NOT a physical aperture projection.
        centerx=left+px/2;centery=top+py/2
        c.create_line(centerx,top,centerx,top+py,fill='#a3aeb8',dash=(2,4))
        c.create_line(left,centery,left+px,centery,fill='#a3aeb8',dash=(2,4))
        c.create_text(width/2,top+py+14,text=f'u,v: ±{half:.3g} mm (screen-center FOV)',
                      font=('Segoe UI',8),fill=MUTED)

    def _draw_profile(self,r):
        if self.wave_display is not None:return  # Both canvases drawn together.
        c=self.profile;c.delete('all')
        width=max(c.winfo_width(),270);height=max(c.winfo_height(),145)
        l,t,rr,b=39,14,width-12,height-29
        half=self._plot_halfspan(r)
        def sx(u):return l+(u+half)/(2*half)*(rr-l)
        def sy(v):return b-(v)*(b-t)
        for z in (0,.5,1):
            y=sy(z);c.create_line(l,y,rr,y,fill='#e9edf0',dash=(2,3))
            c.create_text(l-7,y,text=f'{z:g}',anchor='e',fill=MUTED,font=('Segoe UI',8))
        c.create_line(l,b,rr,b,fill='#828c96')
        c.create_line(l,t,l,b,fill='#828c96')
        xy=[]
        for i in range(241):
            u=-half+2*half*i/240
            xy.extend((sx(u),sy(r.relative_intensity(u,0.))))
        c.create_line(*xy,fill=ACCENT,width=2.5,smooth=True)
        center=sx(r.offset_mm)
        c.create_line(center,t,center,b,fill='#bf8d4f',dash=(4,3))
        for v in (-half,0,half):
            c.create_text(sx(v),b+14,text=f'{v:.2g}',fill=MUTED,font=('Segoe UI',8))
        c.create_text(width-5,height-8,text='u [mm]',anchor='e',fill=MUTED,font=('Segoe UI',8))

    def _draw_wave_profile(self):
        import numpy as np
        data=self.wave_display;grid=data['grid']
        intensity=np.abs(data['field'])**2
        peak=float(intensity.max())
        normalized=intensity/peak if peak else intensity
        scale=np.sqrt(np.clip(normalized,0,1))[...,None]
        rgb=np.asarray(250*(1-scale)+np.array([36,91,145])*scale,dtype=np.uint8)
        image=Image.fromarray(rgb).resize((212,212),Image.Resampling.BILINEAR)
        self.heatmap_image=ImageTk.PhotoImage(image,master=self)
        c=self.heatmap;c.delete('all');width=max(c.winfo_width(),264)
        c.create_image(width/2,4,image=self.heatmap_image,anchor='n')
        c.create_text(width/2,232,text=f'ASM beam-local FOV: {grid.width_mm:g} mm',fill=MUTED)
        c=self.profile;c.delete('all');width=max(c.winfo_width(),270)
        line=normalized[grid.n//2,:]
        xy=[]
        for i,value in enumerate(line):xy.extend((30+(width-45)*i/(grid.n-1),112-95*float(value)))
        c.create_line(*xy,fill=ACCENT,width=2)
        c.create_text(width/2,132,text='beam-local u [mm], normalized to peak',fill=MUTED)

    def _draw_radius_graph(self):
        if not hasattr(self,'radius_graph'):return
        c=self.radius_graph;c.delete('all')
        w=c.winfo_width();h=c.winfo_height()
        if w<80 or h<50:return
        # Select a single source/branch for clarity; the bottom graph displays
        # the path distance on that branch rather than X coordinate on table.
        readings=self._screen_selection()
        bid=readings[min(self.selected_branch_index,len(readings)-1)].branch_id if readings else (self.result.segments[0].branch_id if self.result.segments else None)
        segs=self.result.branch_segments(bid) if bid is not None else []
        if readings:
            # A sample/probe reading is at an intermediate plane. Do not draw
            # its future propagation or an unrelated continuation of a branch.
            end_path=readings[min(self.selected_branch_index,len(readings)-1)].path_mm
            segs=[s for s in segs if s.path_end_mm <= end_path + 1e-6]
        if not segs:
            c.create_text(w/2,h/2,text='Add a laser to see w(s)',fill=MUTED)
            return
        pts=[]
        for seg in segs:
            for k in range(32):
                d=seg.length_mm*k/31
                q=free_space(seg.q_start,d)
                pts.append((seg.path_start_mm+d,beam_radius(q,seg.wavelength_nm)))
        maxs=max(50.,max(p[0] for p in pts))
        maxw=max(0.01,max(p[1] for p in pts)*1.15)
        l,t,r,b=48,9,w-17,h-25
        def xx(s):return l+s/maxs*(r-l)
        def yy(rad):return b-rad/maxw*(b-t)
        for k in range(5):
            y=yy(maxw*k/4)
            c.create_line(l,y,r,y,fill='#edf0f2')
            c.create_text(l-6,y,text=f'{maxw*k/4:.2g}',anchor='e',fill=MUTED,font=('Segoe UI',8))
        c.create_line(l,b,r,b,fill='#9ca6ae')
        c.create_line(l,t,l,b,fill='#9ca6ae')
        xy=[]
        for s,rad in pts:xy.extend((xx(s),yy(rad)))
        if len(xy)>3:c.create_line(*xy,fill=ACCENT,width=2)
        c.create_text(l+2,2,text='w [mm]',anchor='nw',fill=MUTED,font=('Segoe UI',8))
        c.create_text(r,b+13,text=f'{maxs:.0f} mm',anchor='e',fill=MUTED,font=('Segoe UI',8))
        c.create_text(l,b+13,text='0',anchor='w',fill=MUTED,font=('Segoe UI',8))
        c.create_text((l+r)/2,b+13,text='Accumulated propagation s',fill=MUTED,font=('Segoe UI',8))


def main():
    app=BenchApp()
    app.mainloop()


if __name__=='__main__':main()
