import copy
import json
import math
import unittest

from optics import (MAX_PROPAGATION_MM, Vec, beam_radius, default_scene,
    free_space, lens_direction, mirror_direction, normal, q_from_source,
    simulate, thin_lens, validate_scene)

class OpticsTests(unittest.TestCase):
    def test_gaussian_free_space(self):
        lam=780e-6  # mm
        w0=1.0
        zr=math.pi*w0*w0/lam
        q=complex(0,zr)
        self.assertAlmostEqual(beam_radius(free_space(q,500),780),
            w0*math.sqrt(1+(500/zr)**2),places=12)

    def test_lens_abcd(self):
        q=300+2300j
        self.assertAlmostEqual(thin_lens(q,200).real,(q/(1-q/200)).real)
        self.assertAlmostEqual(thin_lens(q,200).imag,(q/(1-q/200)).imag)
        self.assertAlmostEqual(thin_lens(thin_lens(q,200),-200).real,q.real,places=8)
        self.assertAlmostEqual(thin_lens(thin_lens(q,200),-200).imag,q.imag,places=8)

    def test_mirror_90_degree_bend(self):
        d=mirror_direction(Vec(1,0),normal(-45))
        self.assertAlmostEqual(d.x,0,places=10)
        self.assertAlmostEqual(d.y,1,places=10)

    def test_lens_chief_ray_on_axis(self):
        d,_,_=lens_direction(Vec(1,0),normal(0),0,200)
        self.assertAlmostEqual(d.x,1)
        self.assertAlmostEqual(d.y,0)

    def test_lens_chief_ray_off_axis(self):
        d,_,angle=lens_direction(Vec(1,0),normal(0),10,200)
        self.assertAlmostEqual(angle,-0.05)
        self.assertLess(d.y,0)

    def test_default_scene_hits_screen(self):
        result=simulate(default_scene())
        self.assertEqual(len(result.screens),1)
        hit=result.screens[0]
        self.assertEqual(hit.screen_id,'screen-1')
        self.assertAlmostEqual(hit.path_mm,875.,places=7)
        self.assertAlmostEqual(hit.offset_mm,0,places=7)
        self.assertLess(hit.incidence_deg,1e-7)

    def test_screen_radius_matches_manual_abcd(self):
        scene=default_scene()
        r=simulate(scene).screens[0]
        q=q_from_source(scene['components'][0])
        q=free_space(q,225)
        q=thin_lens(q,200)
        q=free_space(q,650)
        self.assertAlmostEqual(r.beam_radius_mm,beam_radius(q,780),places=9)

    def test_screen_tilt_projected_beam(self):
        scene={'table':{'widthMm':1200,'heightMm':900},'components':[
            {'id':'laser-1','type':'laser','x':100,'y':400,'angle':0,
             'lambdaNm':780,'waistMm':1,'powerMw':10},
            {'id':'screen-1','type':'screen','x':500,'y':400,'angle':45,'diameterMm':50}]}
        r=simulate(scene).screens[0]
        self.assertAlmostEqual(r.incidence_deg,45,places=7)
        self.assertAlmostEqual(r.projected_radius_mm,r.beam_radius_mm/math.sqrt(.5),places=7)
        self.assertAlmostEqual(r.relative_intensity(r.projected_radius_mm,0),math.exp(-2),places=7)
        self.assertAlmostEqual(r.relative_intensity(0,0),1,places=9)

    def test_no_screen_outside_aperture(self):
        scene=default_scene();scene['components'][-1]['x']=700
        self.assertEqual(len(simulate(scene).screens),0)

    def test_splitter_branch_powers(self):
        scene={'table':{'widthMm':1200,'heightMm':900},'components':[
            {'id':'laser-1','type':'laser','x':100,'y':300,'angle':0,
             'lambdaNm':780,'waistMm':1,'powerMw':10},
            {'id':'splitter-1','type':'splitter','x':350,'y':300,'angle':-45,
             'diameterMm':25.4,'reflectivity':.3},
            {'id':'screen-a','type':'screen','x':550,'y':300,'angle':0,'diameterMm':50},
            {'id':'screen-b','type':'screen','x':350,'y':600,'angle':90,'diameterMm':50}
        ]}
        r=simulate(scene)
        self.assertEqual(len(r.screens),2)
        self.assertEqual(sorted(round(x.power_mw,4) for x in r.screens),[3,7])

    def test_cumulative_2p5m_mirror_cavity(self):
        scene={'table':{'widthMm':1200,'heightMm':900},'components':[
            # Inject from outside the resonator: an opaque laser cannot sit
            # on the intracavity axis and be passed on every round trip.
            {'id':'laser-1','type':'laser','x':300,'y':100,'angle':90,
             'lambdaNm':780,'waistMm':1,'powerMw':10},
            {'id':'injection','type':'splitter','x':300,'y':450,'angle':45,
             'diameterMm':50,'reflectivity':.5},
            {'id':'mirror-a','type':'mirror','x':900,'y':450,'angle':0,
             'diameterMm':50,'reflectivity':1},
            {'id':'mirror-b','type':'mirror','x':100,'y':450,'angle':0,
             'diameterMm':50,'reflectivity':1}
        ]}
        r=simulate(scene)
        self.assertGreaterEqual(r.capped,1)
        self.assertAlmostEqual(max(s.path_end_mm for s in r.segments),MAX_PROPAGATION_MM)
        self.assertEqual(len(r.screens),0)
        self.assertTrue(r.laser_absorptions)

    def test_branch_inherits_cumulative_length(self):
        scene={'table':{'widthMm':1200,'heightMm':900},'components':[
            {'id':'laser-1','type':'laser','x':100,'y':200,'angle':0,
             'lambdaNm':780,'waistMm':1,'powerMw':10},
            {'id':'splitter-1','type':'splitter','x':350,'y':200,'angle':-45,
             'diameterMm':25.4,'reflectivity':.5},
            {'id':'screen-a','type':'screen','x':700,'y':200,'angle':0,'diameterMm':50},
            {'id':'screen-b','type':'screen','x':350,'y':650,'angle':90,'diameterMm':50}
        ]}
        r=simulate(scene)
        self.assertEqual(sorted(round(x.path_mm) for x in r.screens),[600,700])

    def test_legacy_json_accepted(self):
        scene=default_scene()
        loaded=validate_scene(json.loads(json.dumps(scene)))
        self.assertEqual(loaded['components'][2]['angle'],-45)

    def test_reject_bad_scene(self):
        scene=default_scene();scene['components'][0]['waistMm']=0
        with self.assertRaises(ValueError):validate_scene(scene)

if __name__=='__main__':unittest.main()
