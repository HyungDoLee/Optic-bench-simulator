"""Progress is stage-based, time is measured, estimates need matching history."""
import os
import threading
import time
from concurrent.futures import CancelledError
import unittest
from unittest.mock import patch
import numpy as np

from test_four_f import Measurements
from wave_progress import WaveProgress
from optics import slm_four_f_scene,simulate
from wave_optics import Grid,trace_wave


class ProgressStateTests(Measurements,unittest.TestCase):
    def test_monotonic_stages_and_terminal_outcomes(self):
        progress=WaveProgress();progress.begin(100.)
        progress.advance(.4,'step');progress.advance(.2,'old event')
        self.measure('stage progress never goes backwards',progress.fraction,.4)
        progress.advance(1.,'worker done')
        self.measure('100 percent reserved for accepted result',progress.fraction,.99)
        progress.finish(105.,'succeeded')
        self.measure('success reaches exactly 100 percent',progress.fraction,1.)
        self.measure('final elapsed time freezes [s]',progress.elapsed(200.),5.)
        for state in ('failed','cancelled'):
            progress.begin(200.);progress.advance(.6,'work');progress.finish(202.,state)
            self.measure(state+' does not claim full completion',progress.fraction,.6)

    def test_elapsed_time_and_historical_eta_are_honest(self):
        progress=WaveProgress();progress.begin(100.)
        self.measure('first run has no fabricated ETA',int('첫 계산' in progress.labels(102.)[1]),1)
        progress.begin(100.,previous_seconds=8.)
        self.measure('elapsed time [s]',progress.elapsed(103.),3.)
        self.measure('estimate uses previous duration',int('약 5.0초' in progress.labels(103.)[1]),1)
        self.measure('overrun shown instead of negative ETA',int('오래 걸리는' in progress.labels(109.)[1]),1)
        progress.advance(.4,'work');progress.request_cancel();progress.advance(.9,'late report')
        self.measure('late progress cannot overwrite cancellation',progress.fraction,.4)
        self.measure('cancel state stays visible',int('취소 대기' in progress.labels(110.)[1]),1)

    def test_engine_callbacks_are_monotonic_and_preserve_fields(self):
        scene=slm_four_f_scene();result=simulate(scene);grid=Grid(1024,6.)
        for method in ('asm','fresnel'):
            scene['wavePropagation']=method;events=[]
            baseline=trace_wave(scene,result,result.probes[0],grid)
            output=trace_wave(scene,result,result.probes[0],grid,
                progress_callback=lambda fraction,stage:events.append((fraction,stage)))
            self.measure(method+' field unchanged by progress callback',float(np.max(abs(baseline['field']-output['field']))),0.)
            self.measure(method+' callback starts at zero',events[0][0],0.)
            self.measure(method+' callback ends at one',events[-1][0],1.)
            self.measure(method+' callback monotonic',int(all(a[0]<=b[0] for a,b in zip(events,events[1:]))),1)


def pump_until(app,condition,timeout=5.):
    deadline=time.monotonic()+timeout
    while not condition():
        app.update()
        if time.monotonic()>deadline:raise AssertionError('GUI condition timed out')
        time.sleep(.01)
    app.update()


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires real/virtual display')
class ProgressGUITests(Measurements,unittest.TestCase):
    def setUp(self):
        from app import BenchApp
        self.app=BenchApp();self.errors=[]
        self.app.report_callback_exception=lambda *e:self.errors.append(str(e))
        with patch('app.messagebox.askyesno',return_value=True):self.app._load_slm_four_f()
        self.app._select('fourier-plane');self.app.update()

    def tearDown(self):
        self.app.destroy();self.assertEqual(self.errors,[])

    def test_real_completion_history_and_no_redraw_computation(self):
        from gui_helpers import calculate_wave
        app=self.app;key=app._wave_request()[0]
        with patch.object(app,'_compute_wave_snapshot',wraps=app._compute_wave_snapshot) as compute:
            calculate_wave(app)
            self.measure('completed bar value',app.progress_value.get(),100.)
            self.measure('successful run recorded for exact key',int(key in app._wave_durations),1)
            with patch('numpy.fft.fft2',side_effect=AssertionError('FFT on progress repaint')):
                for _ in range(3):app._render_screen();app._update_wave_progress();app.update()
            self.measure('progress repaint starts no new computation',compute.call_count,1)
            previous=app._wave_durations[key]
            calculate_wave(app)
            self.measure('same settings reuse duration estimate',app.wave_progress.previous_seconds,previous)
            app.wave_n.set(1024);app._render_screen();calculate_wave(app)
            self.measure('different grid does not reuse ETA',int(app.wave_progress.previous_seconds is None),1)

    def test_running_heartbeat_global_badge_and_cancel(self):
        from gui_helpers import wait_wave
        app=self.app;started=threading.Event()
        def held(scene,result,reading,grid,cancel,*,progress_callback=None):
            progress_callback(.35,'대기 중인 테스트 단계');started.set()
            cancel.wait(4);raise CancelledError()
        with patch.object(app,'_compute_wave_snapshot',side_effect=held) as compute:
            app.compute_wave_button.invoke();self.assertTrue(started.wait(2))
            pump_until(app,lambda:app.progress_value.get()>=35)
            first=app.wave_progress.elapsed(time.monotonic());heartbeat=[]
            app.after(30,lambda:heartbeat.append(1))
            pump_until(app,lambda:len(heartbeat)>0)
            self.measure('elapsed clock advances during active job',int(app.wave_progress.elapsed(time.monotonic())>first),1)
            app._select('lens-1');app.update()
            self.measure('global running badge stays mapped',app.job_badge.winfo_ismapped(),1)
            app.job_badge.event_generate('<Button-1>');app.update()
            self.measure('badge returns to analysis panel',int(app.notebook.select()==str(app.analysis_tab)),1)
            app.cancel_wave_button.invoke();wait_wave(app)
            self.measure('cancel outcome visible',int(app.wave_progress.state=='cancelled'),1)
            self.measure('cancel does not fabricate 100 percent',int(app.progress_value.get()<100),1)
            self.measure('cancel does not record misleading ETA',len(app._wave_durations),0)
            self.measure('one worker only',compute.call_count,1)

    def test_failed_calculation_does_not_retry_or_finish_bar(self):
        from gui_helpers import calculate_wave
        app=self.app
        def failed(*args,progress_callback=None):
            progress_callback(.6,'검증 실패 전 단계');raise ValueError('sampling guard test')
        with patch.object(app,'_compute_wave_snapshot',side_effect=failed) as compute:
            calculate_wave(app)
            self.measure('failed outcome recorded',int(app.wave_progress.state=='failed'),1)
            self.measure('failure not displayed as completion',int(app.progress_value.get()<100),1)
            for _ in range(3):app._render_screen();app.update()
            self.measure('failure not automatically retried',compute.call_count,1)
            self.measure('failure leaves no timing history',len(app._wave_durations),0)
            self.measure('error detail still visible',int('sampling guard test' in app.analysis_status.get()),1)

    def test_compact_layout_and_collapsible_details(self):
        app=self.app;app.geometry('1366x768+0+0');app.analysis_canvas.yview_moveto(0);app.update()
        bottom=app.analysis_canvas.winfo_rooty()+app.analysis_canvas.winfo_height()
        self.measure('progress bar visible at laptop height',int(app.wave_progress_bar.winfo_rooty()+app.wave_progress_bar.winfo_height()<bottom),1)
        self.measure('compute button visible at laptop height',int(app.compute_wave_button.winfo_rooty()+app.compute_wave_button.winfo_height()<bottom),1)
        self.measure('details collapsed initially',int(not app.readout_frame.winfo_ismapped()),1)
        self.measure('1D profile collapsed initially',int(not app.profile_area.winfo_ismapped()),1)
        app.show_readout.set(True);app._toggle_readout()
        app.show_profile.set(True);app._toggle_profile();app.update()
        self.measure('details can be expanded',int(app.readout_frame.winfo_ismapped()),1)
        self.measure('1D profile can be expanded',int(app.profile_area.winfo_ismapped()),1)
