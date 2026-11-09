"""SLM modulation, analytical diffraction, ray routing and real GUI checks."""
import copy
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from test_four_f import Measurements
from optics import slm_four_f_scene,four_f_scene,simulate,validate_scene
from slm import slm_component,validate_slm,slm_mask
from wave_optics import Grid,gaussian,power,propagate,lens,pupil,fourier_plane,trace_wave,second_moment_radius


class SLMTests(Measurements,unittest.TestCase):
    def setUp(self):
        self.grid=Grid(512,4)
        self.zr=math.pi*.5**2/(720e-6)
        self.field=gaussian(self.grid,720,1j*self.zr,1.)

    def test_uniform_phase_and_uniform_reflection_loss(self):
        c=slm_component(slmPattern='flat',slmOffsetRad=.7,slmEfficiency=.8)
        mask,phase=slm_mask(c,self.grid,720,self.field)
        self.measure('uniform phase complex error',float(np.max(abs(mask-math.sqrt(.8)*np.exp(.7j)))),0.)
        self.measure('uniform LCOS reflection power fraction',power(self.field*mask,self.grid)/power(self.field,self.grid),.8)
        self.measure('LCOS mode is reflective',int(c['slmMode']=='reflective'),1)

    def test_blaze_fourier_spot_position(self):
        mask,_=slm_mask(slm_component(slmPattern='blaze',slmPeriodMm=.5),self.grid,720,self.field)
        far,g=fourier_plane(self.field*mask,self.grid,720,200)
        intensity=abs(far)**2;x,y=g.xy
        centroid=float(np.sum(x*intensity)/np.sum(intensity))
        self.measure('blaze spot x [mm]',centroid,720e-6*200/.5,atol=1e-10)
        self.measure('phase-only power conserved [mW]',power(far,g),power(self.field,self.grid))

    def test_digital_lens_against_abcd_waist(self):
        mask,_=slm_mask(slm_component(slmPattern='lens',slmFocalMm=200),self.grid,720,self.field)
        reference=lens(self.field,self.grid,720,200)
        self.measure('digital lens complex field error',float(np.max(abs(self.field*mask-reference))),0.,atol=1e-12)
        f=200.;zr=self.zr
        q=complex(-f*zr*zr,f*f*zr)/(f*f+zr*zr)
        focused=propagate(self.field*mask,self.grid,720,-q.real)
        expected=math.sqrt(720e-6*q.imag/math.pi)
        self.measure('digital lens waist [mm]',second_moment_radius(focused,self.grid)[0],expected,atol=2e-6,rtol=0)

    def test_vortex_winding_and_dark_fourier_core(self):
        c=slm_component(slmPattern='vortex',slmCharge=1)
        mask,_=slm_mask(c,self.grid,720,self.field)
        # Counterclockwise circle in array x/y coordinates; independent winding integral.
        t=np.linspace(0,2*math.pi,257)
        i=np.rint(256+50*np.sin(t)).astype(int);j=np.rint(256+50*np.cos(t)).astype(int)
        winding=float(np.unwrap(np.angle(mask[i,j]))[-1]-np.unwrap(np.angle(mask[i,j]))[0])
        self.measure('vortex phase winding [rad]',winding,2*math.pi)
        far,g=fourier_plane(self.field*mask,self.grid,720,200)
        ratio=float(abs(far[256,256])**2/np.max(abs(far)**2))
        # The phase at the single singular central pixel is defined as zero;
        # its finite-pixel contribution is retained, not amplitude-suppressed.
        self.measure('phase-only vortex central peak fraction',ratio,0.,atol=1e-6,rtol=0)
        self.measure('vortex modulus error',float(np.max(abs(abs(mask)-1))),0.)
        self.measure('vortex phase-only power conserved',power(self.field*mask,self.grid),power(self.field,self.grid))

    def test_quantized_blaze_first_order_efficiency(self):
        c=slm_component(slmPattern='blaze',slmPeriodMm=.5,slmPhaseLevels=4)
        mask,_=slm_mask(c,self.grid,720)
        far,g=fourier_plane(mask,self.grid,720,200)
        index=256+8  # eight whole periods across the 4 mm input window
        efficiency=float(abs(far[256,index])**2*g.dx**2/power(mask,self.grid))
        expected=(math.sin(math.pi/4)/(math.pi/4))**2
        self.measure('4-level blaze first order efficiency',efficiency,expected,atol=.002,rtol=0)

    def test_rectangular_area_pixel_fill_and_phase_stroke(self):
        mask,_=slm_mask(slm_component(diameterMm=2,slmHeightMm=1),self.grid,720)
        self.measure('rectangular active area [mm²]',power(mask,self.grid),2.)
        c=slm_component(slmPitchMm=.0625,slmFillFactor=.5625)
        mask,_=slm_mask(c,self.grid,720)
        self.measure('pixel area fill fraction',power(mask,self.grid)/16,.5625)
        mask,phase=slm_mask(slm_component(slmPattern='blaze',slmStrokeRad=math.pi),self.grid,720)
        self.measure('limited phase stroke [rad]',float(np.max(phase)),math.pi)

    def test_phase_only_rejects_amplitude_controls_and_accepts_custom_phase(self):
        for bad in [dict(slmMode='transmissive'),dict(slmPattern='amplitude_grating'),
                    dict(slmAmplitude=.5),dict(slmCoreMm=.05)]:
            with self.assertRaises(ValueError):validate_slm(slm_component(**bad))
        c=slm_component(slmPattern='custom',slmPhaseMap=[[.25,.25],[.25,.25]])
        mask,_=slm_mask(c,self.grid,720)
        self.measure('embedded phase map complex error',float(np.max(abs(mask-np.exp(.25j)))),0.)

    def test_validation_and_unresolved_hardware_pixels(self):
        for bad in [dict(slmPattern='unknown'),dict(slmEfficiency=1.1),dict(slmCharge=.5),
                    dict(slmPhaseLevels=1),dict(slmStrokeRad=10),dict(slmPitchMm=-1),
                    dict(slmPattern='custom'),dict(slmPhaseMap=[[0.],[0.,1.]]),
                    dict(slmPhaseMap=[[float('nan')]])]:
            with self.assertRaises(ValueError):validate_slm(slm_component(**bad))
        with self.assertRaisesRegex(ValueError,'unresolved'):
            slm_mask(slm_component(slmPitchMm=.008),self.grid,720)
        with self.assertRaisesRegex(ValueError,'unresolved'):
            slm_mask(slm_component(slmPattern='blaze',slmPeriodMm=.001),self.grid,720)
        with self.assertRaisesRegex(ValueError,'undersampled'):
            slm_mask(slm_component(slmPattern='lens',slmFocalMm=1),self.grid,720,self.field)

    def test_example_scene_and_actual_fourier_propagation(self):
        scene=slm_four_f_scene()
        saved=json.loads((Path(__file__).resolve().parents[1]/'examples/slm_blaze_720nm.json').read_text())
        self.measure('saved SLM preset matches',int(saved==scene),1)
        result=simulate(validate_scene(json.loads(json.dumps(scene))))
        reading=result.probes[0]
        out=trace_wave(scene,result,reading);intensity=abs(out['field'])**2;x,y=out['grid'].xy
        intensity*=pupil(out['grid'],out['filter_radius_mm'],-out['filter_center_mm'])
        centroid=float(np.sum(x*intensity)/np.sum(intensity))
        self.measure('traced blaze Fourier centroid [mm]',centroid,-720e-6*200/(.128*math.cos(math.radians(5))),atol=2e-5,rtol=0)
        self.measure('incident Fourier power [mW]',out['incident_power_mw'],8.1,atol=1e-7)
        returned=next(r for r in result.screens if r.screen_id=='return-screen')
        self.measure('nominal return power reference [mW]',returned.power_mw,1.62)
        image=returned.abcd @ result.samples[0].abcd.inverse()
        self.measure('sample to detector B [mm]',image.b,0.)
        self.measure('LCOS source to first return path [mm]',returned.path_mm,1100.)
        self.measure('no direct illumination in return detector',len([r for r in result.screens if r.screen_id=='return-screen' and r.path_mm<1100]),0)
        self.measure('q limitation explicitly warned',int(any('unmodulated reference' in w for w in result.warnings)),1)

    def test_calibrated_reflected_phase_applied_once(self):
        scene=slm_four_f_scene()
        modulator=next(c for c in scene['components'] if c['type']=='slm')
        modulator['slmPattern']='flat'
        modulator['slmResidualPower']=0.
        result=simulate(scene);reading=result.probes[0]
        baseline=trace_wave(scene,result,reading)['field']
        modulator['slmOffsetRad']=.3
        shifted=trace_wave(scene,simulate(scene),reading)['field']
        self.measure('total reflection phase applied once',float(np.max(abs(shifted-baseline*np.exp(.3j)))),0.,atol=1e-10)

    def test_reflective_slm_routes_return_and_applies_efficiency(self):
        scene=four_f_scene()
        old=next(c for c in scene['components'] if c['type']=='sample')
        scene['components'].remove(old)
        scene['components'].append(slm_component(id='reflective-slm',x=850,y=450,
            slmMode='reflective',slmEfficiency=.8,slmPattern='flat'))
        result=simulate(validate_scene(scene))
        reading=next(r for r in result.screens if r.screen_id=='return-screen')
        out=trace_wave(scene,result,reading)
        self.measure('reflective SLM return path [mm]',reading.path_mm,1350.)
        self.measure('reflective SLM output power [mW]',out['incident_power_mw'],2.,atol=1e-7)

    def test_slm_keeps_cumulative_2500mm_limit(self):
        scene=dict(table=dict(widthMm=4000,heightMm=900,holeSpacingMm=25),components=[
            dict(id='laser',type='laser',x=100,y=450,angle=0,lambdaNm=720,waistMm=.5,powerMw=1),
            slm_component(x=500,y=450),
            dict(id='mirror',type='mirror',x=50,y=450,angle=0,diameterMm=25.4,reflectivity=1.),
            dict(id='screen',type='screen',x=2700,y=450,angle=0,diameterMm=25.4)])
        result=simulate(validate_scene(scene))
        self.measure('SLM path beyond cap has no detector',len(result.screens),0)
        self.measure('SLM cumulative cap [mm]',max(s.path_end_mm for s in result.segments),2500.)


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires real/virtual display')
class SLMGUITests(Measurements,unittest.TestCase):
    def test_slm_controls_phase_import_json_and_fourier_profile(self):
        from app import BenchApp
        from PIL import Image,ImageGrab
        a=BenchApp();errors=[]
        warning_patch=patch('app.messagebox.showwarning',side_effect=AssertionError('Unexpected GUI warning'))
        warning_patch.start()
        try:
            a.report_callback_exception=lambda *e:errors.append(str(e))
            a.geometry('1490x1250+0+0')
            with patch('app.messagebox.askyesno',return_value=True):a._load_slm_four_f()
            a.update()
            self.measure('SLM added to GUI scene',int(a._component('slm-1') is not None),1)
            self.measure('SLM polygon rendered',len(a.board.find_withtag('slm-surface')),1)
            self.measure('amplitude controls absent',int('slmAmplitude' not in a.property_vars and 'slmCoreMm' not in a.property_vars),1)
            from gui_helpers import calculate_wave
            a._select('fourier-plane');a.update()
            self.measure('SLM selection does not auto calculate',int(a.wave_cache is None),1)
            a.wave_n.set(1024);a._render_screen();calculate_wave(a)
            self.measure('wave grid selection updates cache',a.wave_display['grid'].n,1024)
            a.wave_n.set(2048);a._render_screen()
            a._select('slm-1')
            a.slm_pattern_var.set('vortex');a._commit_props();a.update()
            self.measure('SLM pattern edit applied',int(a._component('slm-1')['slmPattern']=='vortex'),1)
            a._preview_slm();a.update()
            previews=[w for w in a.winfo_children() if str(w.winfo_class())=='Toplevel']
            self.measure('SLM phase preview window',int(bool(previews)),1)
            for w in previews:w.destroy()
            a._select('fourier-plane');a.update()
            calculate_wave(a)
            self.measure('unresolved pure-phase vortex rejected',int(a.wave_display is None and 'Wave unavailable' in a.analysis_status.get()),1)
            # Do not reintroduce amplitude apodization to hide this limitation.
            # The valid phase-only blaze provides the full-path GUI regression.
            a._select('slm-1');a.slm_pattern_var.set('blaze');a._commit_props()
            a._select('fourier-plane');a.update();calculate_wave(a)
            self.measure('SLM Fourier field rendered',int(a.wave_display is not None),1)
            field=a.wave_display['field'];n=field.shape[0]
            intensity=abs(field)**2;x,_=a.wave_display['grid'].xy
            data=a.wave_display
            intensity*=pupil(data['grid'],data['filter_radius_mm'],-data['filter_center_mm'])
            self.measure('LCOS phase-only GUI selected-order centroid [mm]',float((intensity*x).sum()/intensity.sum()),data['filter_center_mm'],atol=2e-5,rtol=0)
            if os.environ.get('OPTICS_CAPTURE_DIR'):
                directory=Path(os.environ['OPTICS_CAPTURE_DIR']);directory.mkdir(parents=True,exist_ok=True)
                a.after(200,a.quit);a.mainloop()
                x,y=a.winfo_rootx(),a.winfo_rooty()
                ImageGrab.grab(bbox=(x,y,x+a.winfo_width(),y+a.winfo_height())).save(directory/'lcos-blaze-fourier.png')
                a._select('slm-1');a.update()
                ImageGrab.grab(bbox=(x,y,x+a.winfo_width(),y+a.winfo_height())).save(directory/'slm-controls.png')
            with tempfile.TemporaryDirectory() as temp:
                png=Path(temp)/'phase.png';Image.new('L',(4,4),128).save(png)
                a._select('slm-1')
                with patch('app.filedialog.askopenfilename',return_value=str(png)):a._import_slm_phase()
                self.measure('phase import stored in scene [rad]',a._component('slm-1')['slmPhaseMap'][0][0],128*2*math.pi/255)
                a.wave_n.set(2048);a.wave_width.set(6.)
                path=Path(temp)/'scene.json'
                with patch('app.filedialog.asksaveasfilename',return_value=str(path)):a._save()
                with patch('app.filedialog.askopenfilename',return_value=str(path)):a._open()
                self.measure('SLM JSON roundtrip pattern',int(a._component('slm-1')['slmPattern']=='custom'),1)
            self.measure('SLM GUI callback errors',len(errors),0)
        finally:
            warning_patch.stop()
            a.destroy()
