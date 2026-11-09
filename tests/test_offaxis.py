"""Separate tests for LCOS arm separation, carrier orders and Fourier filtering."""
import copy
import math
import os
import unittest
from unittest.mock import patch
import numpy as np

from test_four_f import Measurements
from optics import slm_four_f_scene,simulate,validate_scene,Vec,normal,mirror_direction
from slm import slm_component,slm_mask
from slm_geometry import V3,reflected,order_direction,configure_incidence
from wave_optics import Grid,gaussian,power,fourier_plane,trace_wave


class OffAxisGeometryTests(Measurements,unittest.TestCase):
    def test_tilt_separates_arms_but_zero_order_remains_specular(self):
        for degrees in (0,3,5,10):
            a=math.radians(degrees)
            n=V3(math.cos(a),math.sin(a));d=V3(math.cos(2*a),math.sin(2*a))
            zero=order_direction(d,n,V3(-n.y,n.x),720,.128,0)
            specular=reflected(d,n)
            self.measure('zero order equals specular',math.sqrt((zero-specular).dot(zero-specular)),0.)
            separation=math.degrees(math.acos(max(-1,min(1,zero.dot(d*(-1))))))
            self.measure('input/output arm separation [deg]',separation,2*degrees,atol=1e-10)

    def test_3d_tangential_wavevector_and_evanescent_orders(self):
        d=V3(1,.02,.03).unit();n=V3(1,0,0);g=V3(0,0,1)
        out=order_direction(d,n,g,720,.064,1)
        self.measure('3D outgoing norm',out.dot(out),1.)
        self.measure('3D grating tangent k/k0',out.z,d.z+.00072/.064)
        self.measure('orthogonal tangent conserved',out.y,d.y)
        self.measure('reflected hemisphere',int(out.x<0),1)
        self.measure('evanescent order has no geometric ray',int(order_direction(V3(1,0,0),n,g,720,.0005,1) is None),1)

    def test_correct_nonzero_532nm_example(self):
        angle=math.asin(.000532/.064)
        self.measure('532nm /64um angle [deg]',math.degrees(angle),.4762809,atol=2e-5,rtol=0)
        self.measure('532nm /64um focal separation [mm]',200*math.tan(angle),1.6625574,atol=1e-6,rtol=0)

    def test_oblique_order_equation_and_small_angle_approximation(self):
        a=math.radians(5);n=V3(math.cos(a),math.sin(a));g=V3(-n.y,n.x)
        d=V3(math.cos(2*a),math.sin(2*a))
        out=order_direction(d,n,g,720,.128,1)
        theta=math.asin(out.dot(g))
        self.measure('oblique grating equation',math.sin(theta),math.sin(a)+.00072/.128)
        self.measure('small-angle order spacing [rad]',theta-a,.00072/(.128*math.cos(a)),atol=2e-6,rtol=0)

    def test_preset_arm_clearance_incidence_and_image_conjugacy(self):
        scene=slm_four_f_scene();result=simulate(validate_scene(scene))
        self.measure('only sample pickoff splitter remains',sum(c['type']=='splitter' for c in scene['components']),1)
        source,slm=scene['components'][:2]
        d=normal(source['angle']);n=normal(slm['angle'])
        incidence=math.degrees(math.acos(abs(d.dot(n))))
        self.measure('actual LCOS incidence [deg]',incidence,5.)
        incoming_y=source['y']+(800-source['x'])*d.y/d.x
        self.measure('incoming arm clears 25.4mm relay lens',int(abs(incoming_y-600)>12.7+1),1)
        self.measure('sample return path [mm]',next(r for r in result.screens if r.screen_id=='return-screen').path_mm,1100.)
        image=next(r for r in result.screens if r.screen_id=='return-screen').abcd @ result.samples[0].abcd.inverse()
        self.measure('independent collection relay B [mm]',image.b,0.)
        self.measure('collection image magnification',image.a,-1.)

    def test_incidence_control_keeps_relay_axis_and_moves_filter(self):
        scene=slm_four_f_scene();slm=scene['components'][1]
        for a in (-10,-5,2,3,5,10):
            configure_incidence(scene,slm,a)
            source=scene['components'][0]
            out=mirror_direction(normal(source['angle']),normal(slm['angle']))
            self.measure('fixed outgoing axis x',out.x,-1.)
            self.measure('fixed outgoing axis y',out.y,0.)
            hole=next(c for c in scene['components'] if c['type']=='spatial_filter')
            self.measure('linked +1 filter center [mm]',hole['filterOffsetMm'],.00072*200/(.128*math.cos(math.radians(a))))
        with self.assertRaises(ValueError):configure_incidence(scene,slm,0.)

    def test_zero_and_first_order_guides_filter_separately(self):
        result=simulate(slm_four_f_scene())
        zero=[s for s in result.order_paths if s['order']==0]
        first=[s for s in result.order_paths if s['order']==1]
        self.measure('zero order physically blocked',int(zero[-1]['blocked']),1)
        self.measure('zero ends at Fourier plane x [mm]',zero[-1]['end'].x,600.)
        self.measure('+1 reaches return detector',int(abs(first[-1]['end'].y-450)<1e-6),1)
        self.measure('order guide propagation respects cap',int(max(s['path_mm'] for s in zero+first)<=2500),1)


class OffAxisWaveTests(Measurements,unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene=slm_four_f_scene();cls.result=simulate(cls.scene)
        cls.fourier=trace_wave(cls.scene,cls.result,cls.result.probes[0])

    def test_real_zero_and_selected_order_regions(self):
        data=self.fourier
        self.measure('modulated plus unmodulated Fourier power [mW]',data['incident_power_mw'],8.1,atol=1e-7)
        self.measure('real residual zero ROI [mW]',data['zero_roi_mw'],.1,atol=2e-5,rtol=0)
        self.measure('selected +1 hole power [mW]',data['selected_roi_mw'],8.,atol=.002,rtol=0)
        self.measure('Fourier order separation [mm]',abs(data['filter_center_mm']),.00072*200/(.128*math.cos(math.radians(5))))

    def test_sample_and_detector_follow_filtered_field(self):
        sample=trace_wave(self.scene,self.result,self.result.samples[0])
        hit=next(r for r in self.result.screens if r.screen_id=='return-screen')
        detected=trace_wave(self.scene,self.result,hit)
        selected=self.fourier['selected_roi_mw']
        self.measure('sample receives filtered field [mW]',sample['incident_power_mw'],selected*.5,atol=1e-4,rtol=0)
        self.measure('collection detects sample return [mW]',detected['incident_power_mw'],selected*.5*.8*.5,atol=1e-4,rtol=0)
        self.measure('field filtering actually applied',len(detected['filter_losses']),1)

    def test_wrong_hole_selects_zero_instead_of_first(self):
        scene=copy.deepcopy(self.scene)
        next(c for c in scene['components'] if c['type']=='spatial_filter')['filterOffsetMm']=0.
        result=simulate(scene);hit=next(r for r in result.screens if r.screen_id=='return-screen')
        detected=trace_wave(scene,result,hit)
        self.measure('zero-order-only detector power [mW]',detected['incident_power_mw'],.02,atol=1e-4,rtol=0)

    def test_tilt_alone_does_not_remove_unmodulated_light(self):
        grid=Grid();zr=math.pi*.5**2/.00072
        field=gaussian(grid,720,1j*zr,10.)
        for a in (0,5,10):
            c=slm_component(slmEfficiency=0.,slmResidualPower=.01)
            mask,_=slm_mask(c,grid,720,field,incidence_deg=a)
            out,g=fourier_plane((field*mask)[:,(-np.arange(grid.n))%grid.n],grid,720,200)
            self.measure('tilt retains unmodulated power [mW]',power(out,g),.1)
            intensity=abs(out)**2;x,y=g.xy
            self.measure('zero remains at specular focal origin [mm]',float((intensity*x).sum()/intensity.sum()),0.)

    def test_coherent_residual_passivity_and_dead_space_reflection(self):
        with self.assertRaisesRegex(ValueError,'passive'):
            slm_mask(slm_component(slmEfficiency=1.,slmResidualPower=.01),Grid(),720)
        grid=Grid();field=np.ones((512,512),complex)
        c=slm_component(slmEfficiency=0,slmPitchMm=.0625,slmFillFactor=.5625,slmDeadReflectivity=.5)
        mask,_=slm_mask(c,grid,720,field)
        self.measure('dead-space unmodulated reflection fraction',power(mask,grid)/16,.5*(1-.5625))
        c=slm_component(slmPattern='blaze',slmEfficiency=.8,slmResidualPower=.01)
        mask,_=slm_mask(c,grid,720,field)
        self.measure('local coherent surface reflection is passive',int(float(np.max(abs(mask)))<=1),1)


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires real/virtual display')
class OffAxisGUITests(Measurements,unittest.TestCase):
    def test_incidence_control_order_guides_and_filter_readout(self):
        from app import BenchApp
        a=BenchApp();errors=[]
        try:
            a.report_callback_exception=lambda *e:errors.append(str(e))
            a.geometry('1490x1250+0+0')
            with patch('app.messagebox.askyesno',return_value=True):a._load_slm_four_f()
            a.wave_method.set('ASM');a._wave_method_changed()
            a.wave_n.set(2048)
            a.update()
            self.measure('0 order drawn separately',int(bool(a.board.find_withtag('slm-order-0'))),1)
            self.measure('+1 order drawn separately',int(bool(a.board.find_withtag('slm-order-1'))),1)
            a.property_vars['slmDesignIncidenceDeg'].set('3');a._commit_props()
            self.measure('incidence edit changes physical normal [deg]',a._component('slm-1')['angle'],3.)
            a._select('fourier-plane');a.update()
            from gui_helpers import calculate_wave
            calculate_wave(a)
            self.measure('spatial-filter selected-order power displayed',int('+1 / hole ROI' in a.readout.get()),1)
            self.measure('zero-order readout displayed',int('0 ROI' in a.readout.get()),1)
            hole=next(i for i in a.heatmap.find_all() if a.heatmap.type(i)=='oval')
            left,_,right,_=a.heatmap.coords(hole);width=max(a.heatmap.winfo_width(),264)
            self.measure('entire filter hole visible in magnified view',int(left>=width/2-106 and right<=width/2+106),1)
            self.measure('off-axis GUI callback errors',len(errors),0)
        finally:a.destroy()
