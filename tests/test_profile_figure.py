"""Scientific coordinates/units and real Tk/Matplotlib interaction checks."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from test_four_f import Measurements
from profile_data import ProfileData,wave_profile,gaussian_profile
from optics import simulate,validate_scene
from wave_optics import Grid


class ProfileDataTests(Measurements,unittest.TestCase):
    def test_full_resolution_units_orientation_and_snapshot_ownership(self):
        grid=Grid(64,4);field=np.zeros((64,64),complex)
        field[40,50]=2*np.exp(.7j)
        data=dict(grid=grid,field=field,target_label='known pixel',calculated_at='2026-11-09T18:00:00+09:00',
            preview=dict(min_u_mm=-2.,span_mm=4.))
        with patch('numpy.fft.fft2',side_effect=AssertionError('FFT while opening figure')):
            snapshot=wave_profile(data)
            self.assertIs(wave_profile(data),snapshot)
        self.measure('physical intensity mW/mm² -> W/m²',snapshot.intensity_w_m2[40,50],4000.)
        value=snapshot.sample(grid.axis[50],grid.axis[40])
        self.measure('cursor preserves row/origin lower',value['row'],40)
        self.measure('cursor preserves column',value['column'],50)
        self.measure('positive v stays positive [mm]',value['v_mm'],.5)
        self.measure('pixel phase [rad]',value['phase_rad'],.7)
        field[40,50]=0
        self.measure('snapshot survives original field change',snapshot.intensity_w_m2[40,50],4000.)
        with self.assertRaises(ValueError):snapshot.intensity_w_m2[40,50]=0
        self.assertIsNone(snapshot.sample(100,0))
        self.assertIsNone(snapshot.sample(0,0)['phase_rad'])

    def test_gaussian_screen_flux_and_projection_are_preserved(self):
        scene=dict(table=dict(widthMm=1200,heightMm=900,holeSpacingMm=25),components=[
            dict(id='source',type='laser',x=100,y=400,angle=0,lambdaNm=720,waistMm=.5,powerMw=10),
            dict(id='screen',type='screen',x=500,y=400,angle=45,diameterMm=50)])
        reading=simulate(validate_scene(scene)).screens[0]
        snapshot=gaussian_profile(reading,4.)
        dx=snapshot.axis_u_mm[1]-snapshot.axis_u_mm[0]
        self.measure('Gaussian profile integrated power [mW]',float(snapshot.intensity_w_m2.sum()*dx**2*.001),10.,atol=1e-8)
        self.measure('Gaussian center peak W/m²',snapshot.sample(0,0)['intensity_w_m2'],reading.peak_irradiance_w_m2)
        self.measure('Gaussian phase not fabricated',int(snapshot.phase_rad is None),1)


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires real/virtual display')
class ProfileFigureGUITests(Measurements,unittest.TestCase):
    def setUp(self):
        from app import BenchApp
        from gui_helpers import calculate_wave
        self.app=BenchApp();self.errors=[]
        self.app.report_callback_exception=lambda *e:self.errors.append(str(e))
        with patch('app.messagebox.askyesno',return_value=True):self.app._load_slm_four_f()
        self.app._select('fourier-plane');self.app.update()
        self.measure('figure disabled before explicit wave calculation',int(str(self.app.figure_button['state'])=='disabled'),1)
        calculate_wave(self.app)

    def tearDown(self):
        self.app.destroy()
        self.assertEqual(self.errors,[])

    def test_independent_windows_zoom_pan_history_and_cursor_without_fft(self):
        from matplotlib.backend_bases import MouseEvent,MouseButton
        a=self.app;data=a.wave_display
        with patch.object(a,'_compute_wave_snapshot',side_effect=AssertionError('Propagation on figure interaction')):
            with patch('numpy.fft.fft2',side_effect=AssertionError('FFT on figure interaction')):
                a.figure_button.invoke()
                a.wave_quantity.set('Phase');a._render_screen();a.figure_button.invoke();a.update()
                first,second=a.profile_windows
                self.assertIs(first.snapshot,second.snapshot)
                self.measure('popup honors phase selected in main window',int(second.quantity.get()=='Phase'),1)
                self.measure('two independently resizable figures',len(a.profile_windows),2)
                self.assertFalse(first.grab_current())
                first.geometry('1120x900');a.update()
                initial=first.ax.get_xlim();initial_y=first.ax.get_ylim()
                center=((initial[0]+initial[1])/2,(initial_y[0]+initial_y[1])/2)
                px,py=first.ax.transData.transform(center)
                first.canvas.callbacks.process('scroll_event',MouseEvent('scroll_event',first.canvas,px,py,button='up',step=1))
                zoomed=first.ax.get_xlim()
                self.measure('wheel zoom reduces physical span',(zoomed[1]-zoomed[0])/(initial[1]-initial[0]),.8)
                self.measure('second window view unchanged',int(second.ax.get_xlim()==initial),1)
                first.toolbar.back();a.update()
                self.measure('Back restores previous span',first.ax.get_xlim()[1]-first.ax.get_xlim()[0],initial[1]-initial[0])
                first.toolbar.pan()
                for kind,x,y in [('button_press_event',px,py),('motion_notify_event',px+40,py+20),('button_release_event',px+40,py+20)]:
                    event=MouseEvent(kind,first.canvas,x,y,button=1)
                    if kind=='motion_notify_event':event.buttons={MouseButton.LEFT}
                    first.canvas.callbacks.process(kind,event)
                first.toolbar.pan();a.update()
                self.measure('toolbar pan changes view',int(not np.allclose(first.ax.get_xlim(),initial)),1)
                first.full_view();a.update()
                self.measure('Full FOV width [mm]',first.ax.get_xlim()[1]-first.ax.get_xlim()[0],data['grid'].width_mm)
                first.toolbar.home();a.update()
                self.measure('Home restores initial beam view',first.ax.get_xlim()[1]-first.ax.get_xlim()[0],initial[1]-initial[0])
                i,j=np.unravel_index(np.argmax(first.snapshot.intensity_w_m2),first.snapshot.intensity_w_m2.shape)
                px,py=first.ax.transData.transform((first.snapshot.axis_u_mm[j],first.snapshot.axis_v_mm[i]))
                first.canvas.callbacks.process('motion_notify_event',MouseEvent('motion_notify_event',first.canvas,px,py))
                self.measure('physical cursor value shown',int('W/m²' in first.cursor.get() and 'pixel [' in first.cursor.get()),1)
                self.assertIs(a.wave_display,data)
                first.destroy();a.update()
                self.measure('closing one figure preserves the other',len(a.profile_windows),1)
                second.canvas.draw_idle();second.destroy();a.update()
                self.measure('all figure references released on close',len(a.profile_windows),0)

    def test_log_normalized_colors_phase_and_toolbar_png_save(self):
        from matplotlib.colors import LogNorm
        from PIL import Image,ImageGrab
        a=self.app;figure=a._open_profile_window();a.update()
        original=figure.snapshot.intensity_w_m2.copy();limits=figure.ax.get_xlim()
        with patch.object(a,'_compute_wave_snapshot',side_effect=AssertionError('Recompute on colors/save')):
            with patch('numpy.fft.fft2',side_effect=AssertionError('FFT on colors/save')):
                figure.units.set('I / Ipeak');figure.scale.set('Log');figure._style_changed();a.update()
                self.assertIsInstance(figure.image.norm,LogNorm)
                self.measure('normalized color maximum',figure.image.norm.vmax,1.)
                figure.low.set('0.001');figure.high.set('0.8');figure.apply_color_limits()
                figure.cmap.set('inferno');figure._cmap_changed();a.update()
                self.measure('colormap preserves custom color limits',figure.image.norm.vmin,.001)
                self.measure('colormap preserves maximum',figure.image.norm.vmax,.8)
                self.measure('color edits preserve view',int(figure.ax.get_xlim()==limits),1)
                figure.low.set('-1');figure.apply_color_limits()
                self.measure('invalid log limit rejected',int('positive' in figure.message.get()),1)
                figure.quantity.set('Phase');figure._style_changed();a.update()
                self.measure('phase bounds retained [rad]',figure.image.norm.vmax,np.pi)
                figure.quantity.set('Intensity');figure._style_changed();a.update()
                with tempfile.TemporaryDirectory() as temp:
                    path=Path(temp)/'beam.png'
                    with patch('tkinter.filedialog.asksaveasfilename',return_value=str(path)):
                        figure.toolbar.save_figure()
                    with Image.open(path) as image:
                        self.measure('toolbar exports large actual figure',int(image.width>500 and image.height>400),1)
                        self.measure('saved image contains plotted data',int(np.asarray(image).std()>1),1)
                if os.environ.get('OPTICS_CAPTURE_DIR'):
                    folder=Path(os.environ['OPTICS_CAPTURE_DIR']);folder.mkdir(parents=True,exist_ok=True)
                    figure.geometry('1100x900+0+0');a.update()
                    x,y=figure.winfo_rootx(),figure.winfo_rooty()
                    ImageGrab.grab(bbox=(x,y,x+figure.winfo_width(),y+figure.winfo_height())).save(folder/'independent-profile-log.png')
        self.measure('display controls never modify physical intensity',float(np.max(abs(figure.snapshot.intensity_w_m2-original))),0.)

    def test_open_snapshot_survives_recalculation_and_gaussian_mode(self):
        from gui_helpers import calculate_wave
        a=self.app;first=a._open_profile_window();a.update();snapshot=first.snapshot
        slm=a._component('slm-1');slm['slmCarrierPeriodMm']=.256
        a._refresh();calculate_wave(a)
        second=a._open_profile_window();a.update()
        self.assertIsNot(first.snapshot,second.snapshot)
        self.assertIs(first.snapshot,snapshot)
        self.measure('new calculation differs from old frozen figure',int(np.max(abs(first.snapshot.intensity_w_m2-second.snapshot.intensity_w_m2))>100),1)
        a.wave_mode.set(False);a._render_screen()
        third=a._open_profile_window();a.update()
        self.measure('Gaussian q has its own standalone figure',int(third.snapshot.method=='Gaussian q (ideal)'),1)
        self.measure('Gaussian view has no fabricated phase',int(third.snapshot.phase_rad is None),1)
        self.measure('all comparison figures remain open',len(a.profile_windows),3)
