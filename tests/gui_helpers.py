"""Pump Tk while a single user-requested wave job runs; no production hooks."""
import time


def wait_wave(app,timeout=60.):
    deadline=time.monotonic()+timeout
    while app.wave_busy:
        app.update()
        if time.monotonic()>deadline:raise AssertionError('Wave job did not complete')
        time.sleep(.01)
    app.update()


def calculate_wave(app,timeout=60.):
    app.compute_wave_button.invoke()
    wait_wave(app,timeout)
