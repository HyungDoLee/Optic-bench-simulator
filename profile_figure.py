"""Non-modal MATLAB-style Tk/Matplotlib figure over a frozen profile snapshot."""
import math
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import numpy as np
from matplotlib.figure import Figure
from matplotlib.colors import Normalize,LogNorm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
from matplotlib.backend_bases import key_press_handler


class ProfileFigure(tk.Toplevel):
    def __init__(self,master,snapshot,number=1,quantity='Intensity',context='',on_close=None):
        super().__init__(master)
        self.snapshot=snapshot;self.on_close=on_close;self._closed=False
        self.title(f'2D Beam Profile {number} — {snapshot.label}')
        self.geometry(f'1000x850+{70+30*(number%5)}+{40+25*(number%5)}');self.minsize(760,620)
        self.protocol('WM_DELETE_WINDOW',self.destroy)
        self.quantity=tk.StringVar(value=quantity if snapshot.phase_rad is not None else 'Intensity')
        self.units=tk.StringVar(value='W/m²');self.scale=tk.StringVar(value='Linear')
        self.cmap=tk.StringVar(value='twilight' if self.quantity.get()=='Phase' else 'viridis')
        self.low=tk.StringVar();self.high=tk.StringVar();self.cursor=tk.StringVar(value='Move the cursor over a pixel to inspect its value.')
        self.message=tk.StringVar(value='')
        captured=datetime.fromisoformat(snapshot.captured_at).strftime('%Y-%m-%d %H:%M:%S KST (UTC+09:00)')
        ttk.Label(self,text=f'{snapshot.method} | {snapshot.label}',font=('Segoe UI',11,'bold')).pack(anchor='w',padx=10,pady=(8,1))
        ttk.Label(self,text=f'고정 결과 · {captured} · {snapshot.intensity_w_m2.shape[1]}×{snapshot.intensity_w_m2.shape[0]} samples').pack(anchor='w',padx=10)
        if context:ttk.Label(self,text=context,wraplength=950).pack(anchor='w',padx=10,pady=(0,4))
        controls=ttk.Frame(self);controls.pack(fill='x',padx=10,pady=5)
        for label,variable,values,width in [
            ('View',self.quantity,('Intensity','Phase') if snapshot.phase_rad is not None else ('Intensity',),9),
            ('Units',self.units,('W/m²','I / Ipeak'),10),
            ('Scale',self.scale,('Linear','Log'),7),
            ('Colormap',self.cmap,('viridis','inferno','gray','turbo','twilight'),9)]:
            ttk.Label(controls,text=label).pack(side='left',padx=(0,3))
            combo=ttk.Combobox(controls,textvariable=variable,values=values,width=width,state='readonly')
            combo.pack(side='left',padx=(0,10))
            combo.bind('<<ComboboxSelected>>',self._cmap_changed if variable is self.cmap else self._style_changed)
        ttk.Button(controls,text='Full FOV',command=self.full_view).pack(side='left',padx=3)
        ttk.Button(controls,text='Auto colors',command=self.reset_colors).pack(side='left',padx=3)
        limits=ttk.Frame(self);limits.pack(fill='x',padx=10,pady=(0,3))
        ttk.Label(limits,text='Color limits').pack(side='left')
        for variable in (self.low,self.high):ttk.Entry(limits,textvariable=variable,width=13).pack(side='left',padx=5)
        ttk.Button(limits,text='Apply',command=self.apply_color_limits).pack(side='left')
        ttk.Label(limits,textvariable=self.message).pack(side='left',padx=10)
        ttk.Label(self,text='Toolbar: Pan / Zoom / Back / Home / Save  ·  Mouse wheel: zoom at cursor  ·  Cursor: physical pixel value').pack(anchor='w',padx=10,pady=(2,3))
        toolbar_frame=ttk.Frame(self);toolbar_frame.pack(fill='x')
        figure_frame=ttk.Frame(self);figure_frame.pack(fill='both',expand=True)
        ttk.Label(self,textvariable=self.cursor,anchor='w').pack(fill='x',padx=10,pady=(3,7))
        self.figure=Figure(figsize=(8.4,6.3),dpi=100,layout='constrained')
        self.ax=self.figure.add_subplot(111)
        self.ax.set_xlabel('u [mm]');self.ax.set_ylabel('v [mm]')
        self.ax.set_title(snapshot.method+' — '+snapshot.label,fontsize=10)
        self.image=self.ax.imshow(snapshot.intensity_w_m2,origin='lower',extent=snapshot.extent,
            interpolation='nearest',cmap='viridis',aspect='equal',vmin=0,vmax=max(snapshot.peak_w_m2,1e-30))
        self.colorbar=self.figure.colorbar(self.image,ax=self.ax)
        self.canvas=FigureCanvasTkAgg(self.figure,master=figure_frame)
        self.toolbar=NavigationToolbar2Tk(self.canvas,toolbar_frame,pack_toolbar=False)
        self.toolbar.pack(fill='x');self.canvas.get_tk_widget().pack(fill='both',expand=True)
        self._callbacks=[self.canvas.mpl_connect('motion_notify_event',self._inspect_pixel),
                         self.canvas.mpl_connect('scroll_event',self._scroll_zoom),
                         self.canvas.mpl_connect('key_press_event',lambda e:key_press_handler(e,self.canvas,self.toolbar))]
        self._intensity_cmap='viridis';self._previous_quantity=self.quantity.get()
        self.reset_colors()
        if snapshot.initial_limits:
            self.ax.set_xlim(*snapshot.initial_limits[:2]);self.ax.set_ylim(*snapshot.initial_limits[2:])
        self.canvas.draw();self.toolbar.push_current()

    def _display_values(self):
        if self.quantity.get()=='Phase':
            return np.ma.masked_where(self.snapshot.intensity_w_m2<max(self.snapshot.peak_w_m2*1e-6,1e-300),self.snapshot.phase_rad)
        values=self.snapshot.intensity_w_m2
        return values/max(self.snapshot.peak_w_m2,1e-300) if self.units.get()=='I / Ipeak' else values

    def _style_changed(self,_event=None):
        if self.quantity.get()!=self._previous_quantity:
            if self.quantity.get()=='Phase':
                self._intensity_cmap=self.cmap.get();self.cmap.set('twilight')
            else:self.cmap.set(self._intensity_cmap)
            self._previous_quantity=self.quantity.get()
        self.reset_colors()

    def _cmap_changed(self,_event=None):
        if self.quantity.get()=='Intensity':self._intensity_cmap=self.cmap.get()
        self.image.set_cmap(self.cmap.get());self.canvas.draw_idle()

    def reset_colors(self):
        phase=self.quantity.get()=='Phase'
        top=1. if self.units.get()=='I / Ipeak' else max(self.snapshot.peak_w_m2,1e-30)
        low,high=(-math.pi,math.pi) if phase else ((top*1e-6,top) if self.scale.get()=='Log' else (0.,top))
        self.low.set(f'{low:.9g}');self.high.set(f'{high:.9g}')
        self._set_colors(low,high)

    def _set_colors(self,low,high):
        phase=self.quantity.get()=='Phase'
        norm=LogNorm(low,high) if not phase and self.scale.get()=='Log' else Normalize(low,high)
        self.image.set_data(self._display_values());self.image.set_norm(norm)
        self.image.set_cmap(self.cmap.get())
        self.colorbar.update_normal(self.image)
        self.colorbar.set_label('Phase [rad], masked below I/Ipeak = 1e-6' if phase else
            ('Intensity [W/m²]' if self.units.get()=='W/m²' else 'Intensity / peak'))
        self.message.set('Phase: linear radians; intensity units/scale apply in Intensity view.' if phase else '')
        self.canvas.draw_idle()

    def apply_color_limits(self):
        try:
            low=float(self.low.get());high=float(self.high.get())
            if not math.isfinite(low) or not math.isfinite(high) or low>=high:raise ValueError('Require finite min < max.')
            if self.quantity.get()!='Phase' and self.scale.get()=='Log' and low<=0:raise ValueError('Log min must be positive.')
        except ValueError as error:self.message.set(str(error));return
        self._set_colors(low,high)

    def full_view(self):
        self.ax.set_xlim(*self.snapshot.extent[:2]);self.ax.set_ylim(*self.snapshot.extent[2:])
        self.toolbar.push_current();self.canvas.draw_idle()

    def _scroll_zoom(self,event):
        if event.inaxes is not self.ax or event.xdata is None or event.ydata is None:return
        factor=1.25**(-max(-5,min(5,event.step)))
        xlim=self.ax.get_xlim();ylim=self.ax.get_ylim()
        x=event.xdata;y=event.ydata
        self.ax.set_xlim(x+(xlim[0]-x)*factor,x+(xlim[1]-x)*factor)
        self.ax.set_ylim(y+(ylim[0]-y)*factor,y+(ylim[1]-y)*factor)
        self.toolbar.push_current();self.canvas.draw_idle()

    def _inspect_pixel(self,event):
        if event.inaxes is not self.ax or event.xdata is None or event.ydata is None:return
        value=self.snapshot.sample(event.xdata,event.ydata)
        if value is None:
            self.cursor.set(f'u={event.xdata:.6g} mm, v={event.ydata:.6g} mm | outside sampled field');return
        text=f'pixel [{value["row"]}, {value["column"]}]  u={value["u_mm"]:.6g} mm, v={value["v_mm"]:.6g} mm | I={value["intensity_w_m2"]:.7g} W/m²'
        if self.snapshot.phase_rad is not None:
            phase=value['phase_rad'];text+=' | phase='+('undefined (low intensity)' if phase is None else f'{phase:.7g} rad')
        self.cursor.set(text)

    def destroy(self):
        if self._closed:return
        self._closed=True
        if hasattr(self,'canvas'):
            for callback in self._callbacks:self.canvas.mpl_disconnect(callback)
            # TkAgg's deferred draw must not outlive its Tk canvas.
            for name in ('_idle_draw_id','_event_loop_id'):
                identifier=getattr(self.canvas,name,None)
                if identifier:
                    try:self.canvas.get_tk_widget().after_cancel(identifier)
                    except tk.TclError:pass
                    setattr(self.canvas,name,None)
        if self.on_close:self.on_close(self)
        super().destroy()
