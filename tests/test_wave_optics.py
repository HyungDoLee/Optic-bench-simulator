"""Independent analytical wave, detector, grating and GUI regressions.

No experimental/material data are implied by these numerical model tests.
"""
import math
import os
from pathlib import Path
import unittest
import numpy as np

from test_four_f import Measurements
from optics import four_f_scene,simulate
from wave_optics import (Grid,power,gaussian,propagate,lens,pupil,fourier_plane,
    second_moment_radius,complex_sample,detector,grating_orders,
    coherent_splitter,trace_wave)


class WaveTests(Measurements,unittest.TestCase):
    def test_asm_gaussian_against_analytic_and_grid_refinement(self):
        zr=math.pi*.5**2/(720e-6)
        expected=.5*math.sqrt(1+(500/zr)**2)
        radii=[]
        for n in (256,512):
            grid=Grid(n,4)
            field=gaussian(grid,720,1j*zr,10)
            out=propagate(field,grid,720,500)
            radius=second_moment_radius(out,grid)[0];radii.append(radius)
            # Exact ASM differs from paraxial theory at higher orders in NA.
            self.measure(f'ASM radius {n} [mm]',radius,expected,atol=2e-6,rtol=0)
            self.measure(f'ASM power {n} [mW]',power(out,grid),10.,atol=1e-9)
        self.measure('grid convergence [mm]',radii[0],radii[1],atol=1e-6,rtol=0)

    def test_traced_4f_wave_against_independent_theory(self):
        scene=four_f_scene();result=simulate(scene)
        targets=[(result.probes[1],720e-6*200/(math.pi*.5),5.),
                 (result.samples[0],.25,5.),
                 (next(r for r in result.screens if r.screen_id=='return-screen'),.5,2.)]
        for reading,radius,p in targets:
            output=trace_wave(scene,result,reading)
            self.measure(reading.screen_id+' ASM radius [mm]',second_moment_radius(output['field'],output['grid'])[0],radius,atol=2e-5,rtol=0)
            self.measure(reading.screen_id+' ASM power [mW]',output['incident_power_mw'],p,atol=1e-8)

    def test_image_conjugacy_not_just_waist(self):
        result=simulate(four_f_scene())
        sample=result.samples[0]
        hit=next(r for r in result.screens if r.screen_id=='return-screen')
        image=hit.abcd @ sample.abcd.inverse()
        self.measure('sample to detector B [mm]',image.b,0.)
        self.measure('sample to detector magnification A',image.a,-2.)
        self.measure('sample to detector C [1/mm]',image.c,0.)

    def test_defocus_curvature_and_waist_displacement(self):
        scene=four_f_scene()
        next(c for c in scene['components'] if c['id']=='lens-1')['x']+=10
        r=simulate(scene).samples[0]
        q0=complex(0,math.pi*.5**2/(720e-6))
        expected=(-.5*q0-5)/(-.0005*q0-2.005)
        self.measure('detuned R [mm]',r.wavefront_radius_mm,abs(expected)**2/expected.real)
        self.measure('detuned waist displacement [mm]',r.waist_distance_mm,-expected.real)

    def test_aperture_power_and_actual_diffraction(self):
        grid=Grid(512,4);w=.5;lam=720e-6;f=200
        field=gaussian(grid,720,1j*math.pi*w*w/lam,1)
        clipped=field*pupil(grid,w)
        fraction=power(clipped,grid)/power(field,grid)
        # Circular pixels discretize the edge; 0.2% absolute tolerance covers raster area.
        self.measure('Gaussian aperture a=w power fraction',fraction,1-math.exp(-2),atol=.002,rtol=0)
        far,fg=fourier_plane(clipped,grid,720,f)
        uncut,_=fourier_plane(field,grid,720,f)
        center=grid.n//2
        expected_amp=math.sqrt(2/(math.pi*w*w))*math.pi*w*w*(1-math.exp(-1))/(lam*f)
        self.measure('clipped Fourier DC intensity',float(abs(far[center,center])**2),expected_amp**2,atol=.03,rtol=.003)
        x,y=fg.xy;outer=x*x+y*y>(3*lam*f/(math.pi*w))**2
        tails=float(np.sum(abs(far[outer])**2)*fg.dx**2)
        tails_uncut=float(np.sum(abs(uncut[outer])**2)*fg.dx**2)
        self.measure('aperture creates diffraction wings',int(tails>tails_uncut+1e-3),1)
        self.measure('Fourier power conservation [mW]',power(far,fg),power(clipped,grid),atol=1e-10)

    def test_fourier_peak_scale_mask_and_image_inversion(self):
        grid=Grid(512,4);period=.5;f=200
        x,y=grid.xy
        field=(1+.5*np.cos(2*math.pi*x/period)).astype(complex)
        far,fg=fourier_plane(field,grid,720,f)
        row=abs(far[grid.n//2])**2
        peaks=np.argsort(row)[-3:];coordinates=sorted(fg.axis[peaks])
        expected=720e-6*f/period
        for a,b in zip(coordinates,[-expected,0.,expected]):self.measure('Fourier peak x [mm]',float(a),b)
        restored,rg=fourier_plane(far,fg,720,f)
        self.measure('two Fourier transforms pixel pitch [mm]',rg.dx,grid.dx)
        self.measure('4f intensity inversion error',float(np.max(abs(abs(restored)**2-abs(field[np.ix_((-np.arange(grid.n))%grid.n,(-np.arange(grid.n))%grid.n)])**2))),0.,atol=1e-12)
        lowpass=far*pupil(fg,expected/2)
        filtered,_=fourier_plane(lowpass,fg,720,f)
        self.measure('low-pass removes grating contrast',float(np.max(abs(filtered)**2)-np.min(abs(filtered)**2)),0.,atol=1e-12)

    def test_complex_sample_phase_and_resolved_grating(self):
        grid=Grid(256,4);field=np.ones((grid.n,grid.n),complex)
        out=complex_sample(field,grid,.8,phase_rad=.3,period_mm=.5,phase_depth_rad=.7)
        self.measure('phase sample power fraction',power(out,grid)/power(field,grid),.8)
        x,_=grid.xy
        self.measure('spatial sample phase error',float(np.max(abs(out-math.sqrt(.8)*np.exp(1j*(.3+.7*np.cos(2*math.pi*x/.5)))))),0.)
        with self.assertRaisesRegex(ValueError,'unresolved'):
            complex_sample(field,grid,.8,period_mm=.00089,phase_depth_rad=1.)

    def test_phase_sample_changes_fourier_but_not_ideal_image_intensity(self):
        import json
        scene=json.loads((Path(__file__).resolve().parents[1]/'examples/phase_sample_720nm.json').read_text())
        result=simulate(scene)
        screen=next(r for r in result.screens if r.screen_id=='return-screen')
        image=trace_wave(scene,result,screen)
        self.measure('phase-only image waist [mm]',second_moment_radius(image['field'],image['grid'])[0],.5,atol=1e-5,rtol=0)
        self.measure('phase-only image power [mW]',image['incident_power_mw'],2.,atol=1e-8)
        fp=next(r for r in result.probes if r.screen_id=='fourier-plane' and r.path_mm>750)
        phase=trace_wave(scene,result,fp)
        next(c for c in scene['components'] if c['type']=='sample')['phaseDepthRad']=0.
        baseline=trace_wave(scene,simulate(scene),fp)
        difference=float(np.sum(abs(abs(phase['field'])**2-abs(baseline['field'])**2))*phase['grid'].dx**2)
        self.measure('phase-only object changes Fourier intensity',int(difference>.1),1)

    def test_890nm_orders_na_and_energy_budget(self):
        rows=grating_orders(720,890,{-1:.2,0:.4,1:.2},collection_na=.8)
        first=rows[-1]
        self.measure('720/890 first order angle [deg]',first['angle_deg'],math.degrees(math.asin(720/890)))
        self.measure('720/890 minimum NA',first['minimum_na'],720/890)
        self.measure('NA .8 misses first order',int(first['collected']),0)
        accepted=grating_orders(720,890,{-1:.2,0:.4,1:.2},collection_na=.81)
        self.measure('NA .81 collects declared reflected power',sum(r['efficiency'] for r in accepted if r['collected']),.8)
        with self.assertRaises(ValueError):grating_orders(720,890,{0:1.,1:.1})
        with self.assertRaises(ValueError):grating_orders(720,890,{2:.1})

    def test_finite_detector_and_responsivity(self):
        grid=Grid(512,4);w=.5
        field=gaussian(grid,720,1j*math.pi*w*w/(720e-6),10)
        reading=detector(field,grid,w,responsivity_a_w=.5)
        expected=10*(1-math.exp(-2))
        self.measure('finite detector power [mW]',reading['collected_power_mw'],expected,atol=.02,rtol=0)
        self.measure('photodiode current [A]',reading['current_a'],expected*1e-3*.5,atol=1e-5,rtol=0)
        shifted=detector(field,grid,w,offset_mm=.75)
        self.measure('offset lowers collected power',int(shifted['collected_power_mw']<reading['collected_power_mw']),1)

    def test_coherent_splitter_unitarity_and_recombination(self):
        rng=np.random.default_rng(720)
        a=rng.normal(size=(32,32))+1j*rng.normal(size=(32,32))
        b=rng.normal(size=(32,32))+1j*rng.normal(size=(32,32))
        c,d=coherent_splitter(a,b,.3)
        self.measure('two-port power conservation',float(np.sum(abs(c)**2+abs(d)**2)),float(np.sum(abs(a)**2+abs(b)**2)),atol=1e-10)
        c,d=coherent_splitter(a,1j*a,.5)
        self.measure('coherent dark output power',float(np.sum(abs(c)**2)),0.,atol=1e-20)
        self.measure('coherent bright output power',float(np.sum(abs(d)**2)),float(2*np.sum(abs(a)**2)),atol=1e-10)

    def test_sampling_guards_and_cumulative_cap(self):
        grid=Grid(128,1)
        with self.assertRaises(ValueError):propagate(np.ones((128,128)),grid,720,-1)
        field=gaussian(grid,720,1j*math.pi*.2**2/(720e-6),1)
        with self.assertRaisesRegex(ValueError,'window|band limit'):propagate(field,grid,720,2000)
        with self.assertRaisesRegex(ValueError,'undersampled'):lens(field,grid,720,1.)
        scene=four_f_scene();scene['table']['widthMm']=4000
        scene['components']=[scene['components'][0],dict(id='far',type='screen',x=2700,y=450,angle=0,diameterMm=25.4)]
        self.measure('no wave target past 2500 mm',len(simulate(scene).screens),0)


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires real/virtual display')
class WaveGUITests(Measurements,unittest.TestCase):
    def test_splitter_artwork_and_wave_screen(self):
        from app import BenchApp,artwork_angle
        from PIL import ImageGrab
        a=BenchApp();errors=[]
        try:
            a.report_callback_exception=lambda *e:errors.append(str(e))
            a.geometry('1490x1180+0+0');a.scene=four_f_scene()
            a.selected_id='lens-1';a._refresh();a.update()
            self.measure('splitter artwork rotation at normal -45 [deg]',artwork_angle(dict(type='splitter',angle=-45)),0.)
            line=a.board.find_withtag('splitter-interface')[0]
            x1,y1,x2,y2=a.board.coords(line)
            self.measure('coating is +45 in canvas coordinates',(y2-y1)/(x2-x1),1.)
            a.wave_mode.set(True)
            target=next(c for c in a.scene['components'] if c['id']=='return-screen')
            x,y=a._xy((target['x'],target['y']))
            a.board.event_generate('<ButtonPress-1>',x=round(x),y=round(y))
            a.board.event_generate('<ButtonRelease-1>',x=round(x),y=round(y));a.update()
            self.measure('wave screen selection',int(a.selected_id=='return-screen'),1)
            self.measure('wave selection does not auto calculate',int(a.wave_cache is None),1)
            from gui_helpers import calculate_wave
            calculate_wave(a)
            self.measure('wave field actually computed',int(a.wave_display is not None),1)
            self.measure('ASM mode displayed',int('Scalar ASM' in a.analysis_status.get()),1)
            self.measure('wave screen collected power [mW]',a.wave_display['collected_power_mw'],2.,atol=1e-7)
            self.measure('GUI callback errors',len(errors),0)
            if os.environ.get('OPTICS_CAPTURE_DIR'):
                folder=Path(os.environ['OPTICS_CAPTURE_DIR']);folder.mkdir(parents=True,exist_ok=True)
                for component,name in [('return-screen','wave-return'),('sample-1','wave-sample'),('fourier-plane','wave-fourier')]:
                    a._select(component);a.update();calculate_wave(a);a.after(200,a.quit);a.mainloop()
                    x,y=a.winfo_rootx(),a.winfo_rooty()
                    ImageGrab.grab(bbox=(x,y,x+a.winfo_width(),y+a.winfo_height())).save(folder/(name+'.png'))
        finally:a.destroy()
