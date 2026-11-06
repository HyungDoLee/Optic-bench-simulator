"""720 nm reflection relay: independent analytical expectations, in mm/mW.

Each quantitative assertion retains its measured error for tools/verify_4f.py.
GUI checks require a real or virtual DISPLAY; they explicitly skip otherwise.
"""
import copy
import json
import math
from pathlib import Path
import os
import unittest

from optics import (ABCD, MAX_PROPAGATION_MM, beam_radius, four_f_matrix,
                    four_f_scene, q_from_source, simulate, validate_scene)


class Measurements:
    def measure(self, name, actual, expected, atol=1e-10, rtol=1e-10):
        error = abs(actual-expected)
        tolerance = atol+rtol*abs(expected)
        if not hasattr(self, 'measurements'): self.measurements = []
        self.measurements.append(dict(name=name, actual=actual, expected=expected,
            absolute_error=error, relative_error=error/abs(expected) if expected else None,
            tolerance=tolerance, passed=error <= tolerance))
        self.assertLessEqual(error, tolerance, name)


class FourFTests(Measurements, unittest.TestCase):
    def setUp(self):
        self.scene = four_f_scene()
        self.result = simulate(validate_scene(self.scene))

    def test_720nm_and_saved_example(self):
        path = Path(__file__).resolve().parents[1]/'examples/reflection_4f_720nm.json'
        self.measure('saved example equals preset', int(json.loads(path.read_text()) == self.scene), 1)
        for seg in self.result.segments:
            self.measure('wavelength [nm]', seg.wavelength_nm, 720)

    def test_abcd_4f_analytic(self):
        m = four_f_matrix(200, 100)
        for key, value in dict(a=-.5,b=0.,c=0.,d=-2.).items():
            self.measure('4f '+key, getattr(m,key), value)
        self.measure('ABCD determinant', m.a*m.d-m.b*m.c, 1.)
        # Measured source->sample matrix converted to object->sample.
        actual = self.result.samples[0].abcd @ ABCD(b=-150)
        for key in ('a','b','c','d'):
            self.measure('traced 4f '+key, getattr(actual,key), getattr(m,key))

    def test_sample_waist_and_q(self):
        sample = self.result.samples[0]
        expected_w = .5 * (100/200)
        expected_zr = math.pi*expected_w**2/(720e-6)
        self.measure('sample waist [mm]', sample.beam_radius_mm, expected_w)
        self.measure('sample waist position Re(q) [mm]', sample.q.real, 0.)
        self.measure('sample Rayleigh length Im(q) [mm]', sample.q.imag, expected_zr)
        markers = [m for m in self.result.markers if m.kind=='waist' and abs(m.point.x-850)<1e-6]
        self.measure('waist marker at sample', int(bool(markers)), 1)

    def test_fourier_plane_position_and_waist(self):
        components = {c['id']:c for c in self.scene['components']}
        reading = self.result.probes[1]  # outbound, before sample reflection
        self.measure('shared focal plane from L1 [mm]', reading.point.x,
                     components['lens-1']['x']+200)
        self.measure('shared focal plane from L2 [mm]', reading.point.x,
                     components['lens-2']['x']-100)
        self.measure('Fourier plane width [mm]', reading.beam_radius_mm,
                     720e-6*200/(math.pi*.5))
        self.measure('Fourier plane Re(q) [mm]', reading.q.real, 0)
        actual = reading.abcd @ ABCD(b=-150)
        for key, value in dict(a=0.,b=200.,c=-1/200,d=0.).items():
            self.measure('Fourier matrix '+key, getattr(actual,key), value)

    def test_round_trip_detector(self):
        hit = next(r for r in self.result.screens if r.screen_id=='return-screen')
        zr = math.pi*.5**2/(720e-6)
        self.measure('return path [mm]', hit.path_mm, 1350.)
        self.measure('detector Re(q) [mm]', hit.q.real, 0.)
        self.measure('detector Im(q) [mm]', hit.q.imag, zr)
        self.measure('detector radius [mm]', hit.beam_radius_mm, .5)
        self.measure('incident sample power [mW]', self.result.samples[0].power_mw, 5.)
        self.measure('detector power [mW]', hit.power_mw, 10*.5*.8*.5)
        self.measure('profile peak I/I0', hit.relative_intensity(hit.offset_mm), 1.)
        self.measure('profile at w: I/I0', hit.relative_intensity(hit.offset_mm+hit.beam_radius_mm), math.exp(-2))

    def test_traced_abcd_matches_q_on_every_segment(self):
        q0 = q_from_source(self.scene['components'][0])
        for i, seg in enumerate(self.result.segments):
            expected = seg.abcd_end.apply_q(q0)
            self.measure(f'segment {i} Re(q)', seg.q_end.real, expected.real)
            self.measure(f'segment {i} Im(q)', seg.q_end.imag, expected.imag)

    def test_virtual_probes_preserve_beam(self):
        no_probes = copy.deepcopy(self.scene)
        no_probes['components'] = [c for c in no_probes['components'] if c['type']!='probe']
        result = simulate(no_probes)
        for original in self.result.screens:
            hit = next(r for r in result.screens if r.screen_id==original.screen_id)
            self.measure(original.screen_id+' radius unchanged', hit.beam_radius_mm, original.beam_radius_mm)
            self.measure(original.screen_id+' power unchanged', hit.power_mw, original.power_mw)
            self.measure(original.screen_id+' path unchanged', hit.path_mm, original.path_mm)

    def test_misplaced_lens_is_detectable(self):
        scene=copy.deepcopy(self.scene)
        next(c for c in scene['components'] if c['id']=='lens-1')['x'] += 10
        sample=simulate(scene).samples[0]
        # Independently multiplied for P(100)L(100)P(290)L(200)P(210).
        # Spot size alone is a poor alignment metric: its change is only ~10 nm.
        q0=complex(0,math.pi*.5**2/(720e-6))
        expected=(-.5*q0-5)/(-.0005*q0-2.005)
        self.measure('detuned Re(q) [mm]',sample.q.real,expected.real)
        self.measure('detuned Im(q) [mm]',sample.q.imag,expected.imag)
        expected_w=math.sqrt(720e-6/math.pi*abs(expected)**2/expected.imag)
        self.measure('detuned beam radius [mm]',sample.beam_radius_mm,expected_w)
        # A 10 mm alignment error must not silently pass as an ideal 4f waist.
        self.measure('detect nonzero wavefront curvature',int(abs(sample.q.real)>1.),1)

    def test_reflected_graph_includes_shared_path(self):
        hit = next(r for r in self.result.screens if r.screen_id=='return-screen')
        segments = self.result.branch_segments(hit.branch_id)
        self.measure('graph starts at source [mm]', segments[0].path_start_mm, 0.)
        for left,right in zip(segments,segments[1:]):
            self.measure('graph continuity [mm]', right.path_start_mm, left.path_end_mm)
        self.measure('full graph length [mm]', sum(s.length_mm for s in segments), 1350.)

    def test_strict_cap_and_screen_boundary(self):
        # Regression: the old EPS hit tolerance allowed a detector 0.5 nm beyond the cap.
        for offset, expected_hits in ((-1e-5,1),(0.,1),(5e-7,0),(1.,0)):
            scene = dict(table=dict(widthMm=4000,heightMm=900),components=[
                dict(id='laser',type='laser',x=100,y=450,angle=0,lambdaNm=720,waistMm=.5,powerMw=10),
                dict(id='screen',type='screen',x=2600+offset,y=450,angle=0,diameterMm=25.4)])
            result = simulate(scene)
            self.measure(f'screen hits at cap{offset:+g}', len(result.screens), expected_hits)
            maximum = max(s.path_end_mm for s in result.segments)
            self.measure(f'cap overshoot [mm] {offset:+g}', max(0.,maximum-MAX_PROPAGATION_MM), 0., atol=0.,rtol=0.)

    def test_round_trip_exceeding_cap_stops_before_detector(self):
        scene=copy.deepcopy(self.scene)
        scene['table']['heightMm']=1800
        detector=next(c for c in scene['components'] if c['id']=='return-screen')
        detector.update(y=1750,angle=90)
        # Fold return light down instead of up, with a mirror in its return arm.
        scene['components'].append(dict(id='fold',type='mirror',x=350,y=100,
                                         angle=90,diameterMm=25.4,reflectivity=1.))
        # Travel reaches y=100 (path 1600), reverses, and terminates at 2500.
        result=simulate(scene)
        self.measure('no return detector beyond cap',len([r for r in result.screens if r.screen_id=='return-screen']),0)
        self.measure('at least one capped branch',int(result.capped>=1),1)
        self.measure('maximum branch length [mm]', max(s.path_end_mm for s in result.segments),2500.)

    def test_sample_reflectivity_and_scene_validation(self):
        scene=copy.deepcopy(self.scene)
        sample=next(c for c in scene['components'] if c['type']=='sample')
        sample['reflectivity']=0
        result=simulate(validate_scene(scene))
        self.measure('absorbing sample has no return hit',len([r for r in result.screens if r.screen_id=='return-screen']),0)
        sample['reflectivity']=1.1
        with self.assertRaises(ValueError): validate_scene(scene)
        self.measure('out-of-range reflectivity rejected',1,1)


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'), 'Requires a real or virtual DISPLAY')
class FourFGUITests(Measurements, unittest.TestCase):
    def test_screen_click_shows_profile_and_shared_path(self):
        from app import BenchApp
        app=BenchApp()
        errors=[]
        try:
            app.report_callback_exception=lambda *e: errors.append(str(e))
            app.geometry('1490x1120+0+0')
            app.scene=four_f_scene()
            app.selected_id='lens-1'
            app._refresh()
            app.notebook.select(app.properties_tab)
            app.update()
            screen=next(c for c in app.scene['components'] if c['id']=='return-screen')
            x,y=app._xy((screen['x'],screen['y']))
            # Use actual Canvas bindings, not a direct call to the selection method.
            app.board.event_generate('<ButtonPress-1>',x=round(x),y=round(y))
            app.board.event_generate('<ButtonRelease-1>',x=round(x),y=round(y))
            app.update()
            self.measure('screen selected by click',int(app.selected_id=='return-screen'),1)
            self.measure('profile tab visible',int(app.notebook.select()==str(app.analysis_tab)),1)
            self.measure('heatmap raster exists',int(any(app.heatmap.type(i)=='image' for i in app.heatmap.find_all())),1)
            self.measure('profile curve exists',int(any(app.profile.type(i)=='line' and len(app.profile.coords(i))>100 for i in app.profile.find_all())),1)
            self.measure('readout shows ABCD',int('ABCD' in app.readout.get()),1)
            self.measure('GUI callback error count',len(errors),0)
            if os.environ.get('OPTICS_CAPTURE_DIR'):
                from PIL import ImageGrab
                directory=Path(os.environ['OPTICS_CAPTURE_DIR'])
                directory.mkdir(parents=True,exist_ok=True)
                for component,name in [('return-screen','4f-return'),('sample-1','4f-sample'),('fourier-plane','4f-fourier')]:
                    app._select(component)
                    app.update()
                    app.after(200,app.quit)
                    app.mainloop()
                    x,y=app.winfo_rootx(),app.winfo_rooty()
                    ImageGrab.grab(bbox=(x,y,x+app.winfo_width(),y+app.winfo_height())).save(directory/(name+'.png'))
        finally:
            app.destroy()
