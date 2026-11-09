import os
import threading
import unittest
from concurrent.futures import CancelledError
from unittest.mock import patch

from test_four_f import Measurements
from gui_helpers import calculate_wave,wait_wave


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires real/virtual display')
class ManualWaveTests(Measurements,unittest.TestCase):
    def setUp(self):
        from app import BenchApp
        from optics import four_f_scene
        self.app=BenchApp();self.app.wave_n.set(256)
        self.app.scene=four_f_scene();self.app.selected_id='return-screen';self.app._refresh()
        self.errors=[]
        self.app.report_callback_exception=lambda *e:self.errors.append(str(e))
        self.app.update()

    def tearDown(self):
        if not self.app._closing:self.app.destroy()
        self.assertEqual(self.errors,[])

    def test_only_button_starts_one_job_and_worker_keeps_ui_alive(self):
        a=self.app;started=threading.Event();release=threading.Event()
        original=a._compute_wave_snapshot;captured=[]
        def held(scene,result,reading,grid,cancel):
            started.set()
            if not release.wait(5):raise AssertionError('Test gate timed out')
            captured.append(next(c for c in scene['components'] if c['id']=='lens-1')['focalMm'])
            return original(scene,result,reading,grid,cancel)
        with patch.object(a,'_compute_wave_snapshot',side_effect=held) as compute:
            a.wave_mode.set(True)
            for _ in range(3):a._render_screen();a._refresh()
            self.measure('mode/refresh starts no FFT',compute.call_count,0)
            a.compute_wave_button.invoke()
            self.assertTrue(started.wait(2))
            a.compute_wave_button.invoke()  # Disabled: no duplicate/queued job.
            heartbeat=[];a.after(1,lambda:heartbeat.append(1))
            a.update();a.after(5,a.quit);a.mainloop()
            self.measure('Tk processes events while worker waits',len(heartbeat),1)
            self.measure('double click runs one job',compute.call_count,1)
            next(c for c in a.scene['components'] if c['id']=='lens-1')['focalMm']+=10
            a._refresh();a._render_screen()
            self.measure('editing during calculation queues nothing',compute.call_count,1)
            release.set();wait_wave(a)
            self.measure('worker used original immutable scene',captured[0],200.)
            self.measure('snapshot result explicitly stale','재계산 필요' in a.analysis_status.get(),True)
            self.measure('no automatic follow-up computation',compute.call_count,1)

    def test_resize_selection_and_repaint_use_fixed_preview(self):
        a=self.app
        with patch.object(a,'_compute_wave_snapshot',wraps=a._compute_wave_snapshot) as compute:
            calculate_wave(a)
            cached=a.wave_display;image=a.heatmap_image
            # Any full-resolution FFT on the main/UI thread would fail here.
            with patch('numpy.fft.fft2',side_effect=AssertionError('FFT during repaint')):
                for _ in range(4):a._render_screen();a.profile.event_generate('<Configure>');a.update()
                a.geometry('1350x950');a.update()
                a.wave_mode.set(False);a._render_screen()
                a.wave_mode.set(True);a._render_screen();a.update()
            self.measure('all redraws reuse one calculation',compute.call_count,1)
            self.measure('cached numerical result unchanged',int(a.wave_display is cached),1)
            self.measure('wave raster reused across mode toggle',int(a.heatmap_image is image),1)
            a._select('lens-1');a._select('return-screen');a.update()
            self.measure('selection causes no recalculation',compute.call_count,1)
            self.measure('profile readout can scroll at laptop height',int(a.analysis_canvas.yview()[1]<1.),1)

    def test_scene_grid_and_plane_changes_mark_stale_until_click(self):
        a=self.app
        with patch.object(a,'_compute_wave_snapshot',wraps=a._compute_wave_snapshot) as compute:
            calculate_wave(a)
            a.wave_n.set(512);a._render_screen()
            self.measure('grid change marks stale','재계산 필요' in a.analysis_status.get(),True)
            self.measure('grid change does not calculate',compute.call_count,1)
            calculate_wave(a)
            self.measure('explicit click recomputes once',compute.call_count,2)
            self.measure('new grid stored',a.wave_display['grid'].n,512)
            a._add('probe');a._select('return-screen');a.update()
            self.measure('scene edit marks stale','재계산 필요' in a.analysis_status.get(),True)
            self.measure('scene edit does not calculate',compute.call_count,2)

    def test_sampling_failure_stops_and_does_not_retry_on_redraw(self):
        a=self.app
        with patch.object(a,'_compute_wave_snapshot',side_effect=ValueError('sampling test')) as compute:
            calculate_wave(a)
            self.measure('sampling failure displayed',int('sampling test' in a.analysis_status.get()),1)
            for _ in range(5):a._render_screen();a.update()
            self.measure('failed job is not retried automatically',compute.call_count,1)
            self.measure('error leaves button enabled',int(str(a.compute_wave_button['state'])=='normal'),1)

    def test_cancel_and_close_are_cooperative(self):
        a=self.app;started=threading.Event();finished=threading.Event()
        def cancellable(scene,result,reading,grid,cancel):
            started.set();cancel.wait(3);finished.set();raise CancelledError()
        with patch.object(a,'_compute_wave_snapshot',side_effect=cancellable):
            a.compute_wave_button.invoke();self.assertTrue(started.wait(2))
            a.cancel_wave_button.invoke();wait_wave(a)
            self.measure('cancelled job keeps no fabricated result',int(a.wave_cache is None),1)
            self.measure('cancel finishes worker',int(finished.is_set()),1)
        started.clear();finished.clear()
        with patch.object(a,'_compute_wave_snapshot',side_effect=cancellable):
            a.compute_wave_button.invoke();self.assertTrue(started.wait(2));a.destroy()
            self.measure('window close signals cancellation',int(finished.wait(2)),1)
