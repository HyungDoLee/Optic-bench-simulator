"""Opaque source housing: emitted rays start, returning rays stop."""
import unittest
from optics import simulate,validate_scene,slm_four_f_scene
from slm import slm_component
from test_four_f import Measurements


class LaserStopTests(Measurements,unittest.TestCase):
    def scene(self):
        return dict(table=dict(widthMm=1200,heightMm=900,holeSpacingMm=25),components=[
            dict(id='laser',type='laser',x=200,y=400,angle=0,lambdaNm=720,waistMm=.5,powerMw=10),
            dict(id='mirror',type='mirror',x=600,y=400,angle=0,diameterMm=25.4,reflectivity=1.),
            dict(id='behind',type='screen',x=100,y=400,angle=0,diameterMm=25.4)])

    def test_return_stops_at_emitting_laser_before_rear_screen(self):
        result=simulate(validate_scene(self.scene()))
        self.measure('emitted and reflected segments',len(result.segments),2)
        self.measure('return stops at source x [mm]',result.segments[-1].end.x,200.)
        self.measure('return path [mm]',result.segments[-1].path_end_mm,800.)
        self.measure('no rear screen after laser',len(result.screens),0)
        self.measure('one source absorption',len(result.laser_absorptions),1)
        self.measure('absorbed ray reference power [mW]',result.laser_absorptions[0]['ray_reference_power_mw'],10.)
        self.measure('absorption is not a path cap',result.capped,0)

    def test_other_laser_is_also_opaque(self):
        scene=self.scene();scene['components'][1].update(id='other-laser',type='laser',x=400,angle=180,
            lambdaNm=720,waistMm=.5,powerMw=0.)
        result=simulate(validate_scene(scene))
        self.measure('beam stops at other laser x [mm]',result.segments[0].end.x,400.)
        self.measure('other source absorbs ray',int(result.laser_absorptions[0]['component']=='other-laser'),1)
        self.measure('no transmitted beam through other source',len(result.segments),1)

    def test_missed_laser_does_not_become_an_infinite_wall(self):
        scene=self.scene()
        scene['components'][1].update(id='other-laser',type='laser',x=400,y=450,angle=180,
            diameterMm=20,lambdaNm=720,waistMm=.5,powerMw=0.)
        scene['components'][2].update(x=600)
        result=simulate(validate_scene(scene))
        self.measure('beam passing clear of source reaches screen',len(result.screens),1)
        self.measure('missed source has no absorption',len(result.laser_absorptions),0)

    def test_reflected_slm_order_guides_stop_at_laser(self):
        scene=self.scene();scene['components'][1]=slm_component(id='slm',x=600,y=400,
            slmCarrierPeriodMm=.5,slmEfficiency=1.)
        result=simulate(validate_scene(scene))
        for order in (0,1):
            last=next(s for s in reversed(result.order_paths) if s['order']==order)
            self.measure(f'order {order} terminates at source x [mm]',last['end'].x,200.)
            self.measure(f'order {order} marked blocked',int(last['blocked']),1)
        self.measure('SLM return cannot reach rear detector',len(result.screens),0)

    def test_slm_presets_have_no_segment_past_a_hit_laser(self):
        scene=slm_four_f_scene();result=simulate(scene)
        self.measure('default SLM stray branch is absorbed',len(result.laser_absorptions),1)
        for stop in result.laser_absorptions:
            subsequent=[s for s in result.segments if s.branch_id==stop['branch'] and s.path_start_mm>=stop['path_mm']-1e-8]
            self.measure('no post-laser segments',len(subsequent),0)
