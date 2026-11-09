import math
import threading
import unittest
from concurrent.futures import CancelledError
import numpy as np
from test_four_f import Measurements
from hologram_validation import illumination_sampling,gs_filter_benchmark,pixel_fourier
from optics import slm_four_f_scene,simulate,normal,tangent
from wave_optics import Grid,gaussian,propagate,field_moments,trace_wave


class ReviewDiagnosticsTests(Measurements,unittest.TestCase):
    def test_real_pixel_sampling_and_hologram_illumination_are_explicit(self):
        report=illumination_sampling(.5,.008,512,6,2048,5)
        self.measure('512 pixel hologram diameter [mm]',report['hologram_diameter_mm'],4.096)
        self.measure('default beam illuminates only 125 pixels at 1/e2 diameter',report['beam_1e2_diameter_pixels'],125.)
        self.measure('8um pixels unresolved in 2048/6mm grid',int(report['resolved_pixels']),0)
        self.measure('pixel-resolved next power of two',report['next_power_of_two'],4096)
        self.measure('hologram edge is practically dark',int(report['edge_relative_intensity']<1e-14),1)
        expanded=illumination_sampling(2.048,.008,512,6,2048,5)
        self.measure('expanded Gaussian edge intensity',expanded['edge_relative_intensity'],math.exp(-2))

    def test_wave_centroid_and_mean_direction_independent_of_reference_ray(self):
        grid=Grid();x,y=grid.xy;lam=.00072
        q=1j*math.pi*.5**2/lam
        shifted=gaussian(grid,720,q)*np.exp(2j*math.pi*x/.5)
        a=field_moments(shifted,grid,720)
        self.measure('mean wave sine from carrier',a['mean_transverse_sine'][0],lam/.5)
        arrival={};out=propagate(shifted,grid,720,200,diagnostics=arrival)
        self.measure('wave centroid walks off reference [mm]',arrival['centroid_mm'][0],200*lam/.5,atol=2e-6,rtol=0)
        self.measure('propagation preserves angular centroid',arrival['mean_transverse_sine'][0],lam/.5)

    def test_sample_actual_mean_angle_matches_selected_order_guide(self):
        scene=slm_four_f_scene();result=simulate(scene)
        data=trace_wave(scene,result,result.samples[0])
        incoming=next(s for s in result.order_paths if s['order']==1 and abs(s['end'].x-400)<1e-5)
        guide=(incoming['end']-incoming['start']).unit()
        reference=next(s for s in result.segments if abs(s.path_end_mm-result.samples[0].path_mm)<1e-7)
        predicted=math.degrees(math.atan2(guide.dot(tangent(reference.direction)),guide.dot(reference.direction)))
        self.measure('sample wave vs +1 guide angle [deg]',data['moments']['angle_deg'][0],predicted,atol=.002,rtol=0)
        self.measure('sample actual incidence is nonzero',int(data['moments']['mean_incidence_deg']>.6),1)
        self.measure('per-plane wave diagnostics recorded',int(len(data['arrivals'])>=5),1)

    def test_n_and_fov_convergence_are_checked_separately(self):
        expected=.5*math.sqrt(1+(500/(math.pi*.5**2/.00072))**2)
        for n,width in ((256,4),(512,4),(512,8)):
            grid=Grid(n,width);arrival={}
            propagate(gaussian(grid,720,1j*math.pi*.5**2/.00072),grid,720,500,diagnostics=arrival)
            self.measure(f'Gaussian N={n}, FOV={width} radius [mm]',arrival['radius_2sigma_mm'][0],expected,atol=2e-6,rtol=0)

    def test_wave_job_cancellation_preserves_sampling_guards(self):
        scene=slm_four_f_scene();result=simulate(scene);cancel=threading.Event();cancel.set()
        with self.assertRaises(CancelledError):trace_wave(scene,result,result.probes[0],cancel_event=cancel)

    def test_pixel_envelope_predicts_16_pixel_blaze_main_order(self):
        n=128;pitch=.008;x=np.arange(n)-n//2
        field=np.tile(np.exp(2j*math.pi*x/16),(n,1))
        out,axis=pixel_fourier(field,pitch,720,200)
        cell=axis[1]-axis[0]
        eta=float(abs(out[n//2,n//2+n//16])**2*cell**2/(n*n*pitch**2))
        self.measure('16 pixel carrier sinc envelope efficiency',eta,(math.sin(math.pi/16)/(math.pi/16))**2)


class GSReviewTests(Measurements,unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=gs_filter_benchmark()

    def test_gs_phase_improves_reconstruction_and_filter_tradeoff(self):
        r=self.report;small,large=r['filters']
        self.measure('GS NRMSE improves over random phase',int(r['gs_final_nrmse']<r['gs_initial_nrmse']*.5),1)
        self.measure('GS final NRMSE bounded',int(r['gs_final_nrmse']<.5),1)
        self.measure('large pinhole passes more desired hologram power',int(large['target_pass_fraction']>small['target_pass_fraction']+.3),1)
        self.measure('larger pinhole improves coherent image error',int(large['coherent_reconstruction_nrmse']<small['coherent_reconstruction_nrmse']),1)
        self.measure('large pinhole still rejects residual',int(large['residual_pass_fraction']<.01),1)
        self.measure('pixel envelope zone power is not falsely normalized',int(r['modulated_primary_zone_power']<=r['input_pupil_power']),1)
