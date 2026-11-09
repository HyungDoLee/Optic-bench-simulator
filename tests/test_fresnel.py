"""Independent forward-diffraction checks; no GS or measured hardware."""
import copy
import math
import os
from pathlib import Path
import threading
from concurrent.futures import CancelledError
import unittest
from unittest.mock import patch
import numpy as np

from optics import ABCD,propagation_matrix,lens_matrix,slm_four_f_scene,simulate,validate_scene
from slm import slm_mask
from wave_optics import Grid,gaussian,power,fourier_plane,trace_wave,lens
from fresnel_optics import fresnel_transform
from test_four_f import Measurements


def relative_complex_error(actual,expected):
    # Overall piston/Gouy phase is not an interferometer observable here.
    overlap=np.vdot(expected,actual)
    piston=overlap/abs(overlap) if abs(overlap) else 1.
    return float(np.linalg.norm(actual-piston*expected)/np.linalg.norm(expected))


class FresnelTests(Measurements,unittest.TestCase):
    def test_free_space_against_independent_fresnel_quadrature(self):
        grid=Grid(128,8);lam=.00072;z=500.
        x,y=grid.xy
        field=np.exp(-(x*x+y*y)/.3**2)*np.exp(2j*math.pi*x/.8)
        out,g=fresnel_transform(field,grid,720,propagation_matrix(z))
        kernel=np.exp(1j*math.pi*(g.axis[:,None]-grid.axis[None,:])**2/(lam*z))
        expected=grid.dx**2/(1j*lam*z)*(kernel @ field @ kernel.T)
        self.measure('direct Fresnel quadrature complex relative error',relative_complex_error(out,expected),0.,atol=1e-12,rtol=0)
        self.measure('Fresnel quadrature absolute power',power(out,g),power(field,grid),atol=1e-12)

    def test_two_fresnel_steps_and_lens_form_fourier_transform(self):
        lam=.00072;f=200.;n=512
        # Natural grids coincide in this independent two-step construction.
        grid=Grid(n,math.sqrt(n*lam*f));x,y=grid.xy
        field=np.exp(-(x*x+y*y)/.4**2)*np.exp(2j*math.pi*x/.5)
        first,g=fresnel_transform(field,grid,720,propagation_matrix(f))
        at_lens=lens(first,g,720,f)  # Infinite pupil by default.
        actual,g=fresnel_transform(at_lens,g,720,propagation_matrix(f))
        expected,fg=fourier_plane(field,grid,720,f)
        self.measure('P(f) L(f) P(f) vs Fourier complex error',relative_complex_error(actual,expected),0.,atol=2e-12,rtol=0)
        self.measure('Fourier output dx [mm]',g.dx,fg.dx)
        self.measure('two-step absolute power',power(actual,g),power(field,grid),atol=1e-12)

    def test_same_n_different_sampling_and_gaussian_fourier_width(self):
        grid=Grid(512,4.096);lam=.00072;f=200.;w=.5
        field=gaussian(grid,720,1j*math.pi*w*w/lam)
        system=propagation_matrix(f) @ lens_matrix(f) @ propagation_matrix(f)
        actual,g=fresnel_transform(field,grid,720,system)
        self.measure('Fourier N unchanged',g.n,512)
        self.measure('512/8um Fourier dx [mm]',g.dx,.03515625)
        self.measure('512/8um Fourier FOV [mm]',g.width_mm,18.)
        x,y=g.xy;wf=lam*f/(math.pi*w)
        intensity=2/(math.pi*wf*wf)*np.exp(-2*(x*x+y*y)/(wf*wf))
        self.measure('Gaussian Fourier intensity NRMSE',float(np.linalg.norm(abs(actual)**2-intensity)/np.linalg.norm(intensity)),0.,atol=2e-7,rtol=0)
        self.measure('Gaussian Fourier power [mW]',power(actual,g),1.,atol=1e-10)

    def test_output_phase_and_detuning_are_retained(self):
        grid=Grid(256,4);x,y=grid.xy
        field=np.exp(-(x*x+y*y)/.35**2)*np.exp(.4j*np.sin(2*math.pi*x/.8))
        f=200.;delta=20.
        actual,g=fresnel_transform(field,grid,720,propagation_matrix(f+delta) @ lens_matrix(f) @ propagation_matrix(f))
        far,fg=fourier_plane(field,grid,720,f)
        # A= -delta/f, B=f, D=0 when only the output plane moves.
        # Equivalently transform an input chirp with A/B=-delta/f².
        chirped=field*np.exp(-1j*math.pi*delta*(x*x+y*y)/(.00072*f*f))
        expected,_=fourier_plane(chirped,grid,720,f)
        self.measure('defocused Fresnel complex error',relative_complex_error(actual,expected),0.,atol=1e-12,rtol=0)
        self.measure('defocus changes complex wave',int(relative_complex_error(actual,far)>1e-3),1)
        # Lens-plane -> back-focus has an output quadratic phase; do not drop it.
        after,g=fresnel_transform(field,grid,720,propagation_matrix(f) @ lens_matrix(f))
        u,v=g.xy
        expected=far*np.exp(1j*math.pi*(u*u+v*v)/(.00072*f))
        self.measure('back-focus output quadratic phase retained',relative_complex_error(after,expected),0.,atol=1e-12,rtol=0)

    def test_unequal_4f_image_and_negative_b_transform(self):
        grid=Grid(256,4);x,y=grid.xy
        field=np.exp(-((x-.2)**2+(y+.1)**2)/.35**2)*np.exp(.3j*x)
        matrix=propagation_matrix(100) @ lens_matrix(100) @ propagation_matrix(300) @ lens_matrix(200) @ propagation_matrix(200)
        image,g=fresnel_transform(field,grid,720,matrix)
        reverse=(-np.arange(grid.n))%grid.n
        expected=field[np.ix_(reverse,reverse)]*2
        self.measure('4f complex image inversion',relative_complex_error(image,expected),0.,atol=1e-12,rtol=0)
        self.measure('4f image FOV [mm]',g.width_mm,2.)
        self.measure('4f image power',power(image,g),power(field,grid),atol=1e-12)
        positive,gp=fresnel_transform(field,grid,720,ABCD(0,200,-.005,0))
        negative,gn=fresnel_transform(field,grid,720,ABCD(0,-200,.005,0))
        self.measure('negative B Fourier sign',relative_complex_error(negative,-positive[np.ix_(reverse,reverse)]),0.,atol=1e-12,rtol=0)

    def test_custom_phase_forward_bench_matches_fourier_and_bypasses_filters(self):
        scene=slm_four_f_scene();scene['wavePropagation']='fresnel'
        slm=next(c for c in scene['components'] if c['type']=='slm')
        n=32;u,v=np.meshgrid(np.linspace(-1,1,n),np.linspace(-1,1,n))
        phase=(.9*np.sin(3*u)+.4*np.cos(4*v)).tolist()
        slm.update(slmPattern='custom',slmPhaseMap=phase,slmResidualPower=0.,slmEfficiency=1.)
        original=copy.deepcopy(phase)
        result=simulate(validate_scene(scene));grid=Grid(512,6)
        out=trace_wave(scene,result,result.probes[0],grid)
        field=gaussian(grid,720,1j*math.pi*.5**2/.00072,10.)
        mask,_=slm_mask(slm,grid,720,field,5.)
        after=field*mask;after=after[:,(-np.arange(grid.n))%grid.n]
        expected,fg=fourier_plane(after,grid,720,200.)
        self.measure('custom phase full bench complex Fourier error',relative_complex_error(out['field'],expected),0.,atol=1e-12,rtol=0)
        self.measure('phase input not optimized or overwritten',int(slm['slmPhaseMap']==original),1)
        self.measure('custom phase absolute power [mW]',out['incident_power_mw'],10.,atol=1e-10)
        sample=trace_wave(scene,result,result.samples[0],grid)
        self.measure('pinhole bypassed in ideal mode',sample['incident_power_mw'],5.,atol=1e-10)
        self.measure('sample output dx [mm]',sample['grid'].dx,grid.dx*.5)
        self.measure('pinhole bypass explicitly recorded',int('fourier-plane pinhole' in sample['bypassed_apertures']),1)
        # Carrier sign includes the LCOS reflection parity.
        slm.update(slmPattern='flat',slmCarrierPeriodMm=.128)
        out=trace_wave(scene,simulate(scene),result.probes[0],grid)
        self.measure('blaze Fourier centroid [mm]',out['moments']['centroid_mm'][0],-.00072*200/(.128*math.cos(math.radians(5))),atol=1e-9)

    def test_phase_only_vortex_has_fourier_dark_core_without_asm(self):
        scene=slm_four_f_scene();scene['wavePropagation']='fresnel'
        slm=next(c for c in scene['components'] if c['type']=='slm')
        slm.update(slmPattern='vortex',slmCarrierPeriodMm=0.,slmResidualPower=0.,slmEfficiency=1.)
        result=simulate(scene)
        with patch('wave_optics.propagate',side_effect=AssertionError('ASM must not be used')):
            out=trace_wave(scene,result,result.probes[0],Grid(512,6))
        intensity=abs(out['field'])**2
        self.measure('pure phase vortex center/peak',float(intensity[256,256]/intensity.max()),0.,atol=1e-5,rtol=0)
        self.measure('vortex absolute power retained',out['incident_power_mw'],10.,atol=1e-10)

    def test_sampling_path_limit_and_cancellation_remain_explicit(self):
        grid=Grid(64,4);field=np.ones((64,64),complex)
        with self.assertRaisesRegex(ValueError,'undersampled'):
            fresnel_transform(field,grid,720,propagation_matrix(.01))
        with self.assertRaises(ValueError):fresnel_transform(field,grid,720,ABCD(a=2,d=2))
        scene=slm_four_f_scene();scene['wavePropagation']='fresnel';result=simulate(scene)
        cancel=threading.Event();cancel.set()
        with self.assertRaises(CancelledError):trace_wave(scene,result,result.probes[0],cancel_event=cancel)
        with self.assertRaisesRegex(ValueError,'FOV'):
            trace_wave(scene,result,result.probes[0],Grid(256,.1))
        scene['table']['widthMm']=4000
        scene['components']=[scene['components'][0],dict(id='far',type='screen',x=3500,y=450,angle=0,diameterMm=25.4)]
        self.measure('Fresnel respects 2500mm route limit',len(simulate(scene).screens),0)
        self.measure('Fresnel JSON model preserved',int(validate_scene(scene)['wavePropagation']=='fresnel'),1)


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires real/virtual display')
class FresnelGUITests(Measurements,unittest.TestCase):
    def test_manual_fresnel_intensity_phase_and_model_selection(self):
        from app import BenchApp
        from gui_helpers import calculate_wave
        from PIL import ImageGrab
        app=BenchApp();errors=[]
        try:
            app.report_callback_exception=lambda *e:errors.append(str(e))
            app.geometry('1490x1180+0+0')
            with patch('app.messagebox.askyesno',return_value=True):app._load_slm_four_f()
            self.measure('ideal default uses 512 grid',app.wave_n.get(),512)
            app.wave_n.set(512);app._select('fourier-plane');app.update()
            self.measure('SLM preset selects Fresnel',int(app.wave_method.get()=='Fresnel'),1)
            self.measure('return-to-laser absorption marker visible',len(app.board.find_withtag('laser-absorption')),1)
            self.measure('finite-pinhole guides absent in ideal mode',len(app.board.find_withtag('slm-order-0')),0)
            self.measure('selecting Fresnel starts no job',int(app.wave_cache is None),1)
            calculate_wave(app)
            data=app.wave_display
            self.measure('Fresnel output computed',int(data is not None),1)
            self.measure('Fresnel status visible',int('Fresnel ideal' in app.analysis_status.get()),1)
            self.measure('output physical sampling displayed',int('24 µm / 12.288 mm' in app.readout.get()),1)
            with patch.object(app,'_compute_wave_snapshot',side_effect=AssertionError('Recompute on phase toggle')):
                with patch('numpy.fft.fft2',side_effect=AssertionError('FFT on phase toggle')):
                    for quantity in ('Intensity','Phase','Intensity','Phase'):
                        app.wave_quantity.set(quantity);app._render_screen();app.update()
            self.measure('phase toggle retains original field',int(app.wave_display is data),1)
            self.measure('phase is selected',int('phase' in app.heatmap_caption.get()),1)
            self.measure('phase image rendered',len(app.heatmap.find_all())>0,True)
            if os.environ.get('OPTICS_CAPTURE_DIR'):
                folder=Path(os.environ['OPTICS_CAPTURE_DIR']);folder.mkdir(parents=True,exist_ok=True)
                for quantity,name in [('Intensity','fresnel-fourier-intensity'),('Phase','fresnel-fourier-phase')]:
                    app.wave_quantity.set(quantity);app._render_screen();app.update()
                    x,y=app.winfo_rootx(),app.winfo_rooty()
                    ImageGrab.grab(bbox=(x,y,x+app.winfo_width(),y+app.winfo_height())).save(folder/(name+'.png'))
            app._select('slm-1');app.slm_pattern_var.set('vortex');app._commit_props()
            app._select('fourier-plane');app.update();calculate_wave(app)
            self.measure('phase-only vortex GUI Fresnel result',int(app.wave_display is not None),1)
            if os.environ.get('OPTICS_CAPTURE_DIR'):
                for quantity,name in [('Intensity','fresnel-vortex-intensity'),('Phase','fresnel-vortex-phase')]:
                    app.wave_quantity.set(quantity);app._render_screen();app.update()
                    x,y=app.winfo_rootx(),app.winfo_rooty()
                    ImageGrab.grab(bbox=(x,y,x+app.winfo_width(),y+app.winfo_height())).save(folder/(name+'.png'))
            app.wave_method.set('ASM');app._wave_method_changed()
            self.measure('model change marks result stale',int('재계산 필요' in app.analysis_status.get()),1)
            self.measure('GUI callback errors',len(errors),0)
        finally:app.destroy()
