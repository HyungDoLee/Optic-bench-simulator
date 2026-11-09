"""Immutable numerical snapshots for independent figures; no Tk or FFT calls."""
from dataclasses import dataclass
from datetime import datetime,timezone,timedelta
from functools import cached_property
import numpy as np


def timestamp_kst():
    return datetime.now(timezone(timedelta(hours=9),name='KST')).isoformat(timespec='seconds')


@dataclass(frozen=True)
class ProfileData:
    intensity_w_m2: np.ndarray
    axis_u_mm: np.ndarray
    axis_v_mm: np.ndarray
    label: str
    method: str
    captured_at: str
    phase_rad: np.ndarray | None = None
    initial_limits: tuple[float,float,float,float] | None = None

    def __post_init__(self):
        # One owned snapshot is shared by every figure opened for this result.
        for name in ('intensity_w_m2','axis_u_mm','axis_v_mm','phase_rad'):
            value=getattr(self,name)
            if value is not None:
                array=np.array(value,dtype=float,copy=True)
                if not np.isfinite(array).all():raise ValueError('Profile must contain finite data')
                array.setflags(write=False);object.__setattr__(self,name,array)
        shape=(len(self.axis_v_mm),len(self.axis_u_mm))
        if min(shape)<2 or self.intensity_w_m2.shape!=shape or np.any(self.intensity_w_m2<0):
            raise ValueError('Invalid intensity/coordinate shape')
        if self.phase_rad is not None and self.phase_rad.shape!=shape:raise ValueError('Phase shape mismatch')
        for axis in (self.axis_u_mm,self.axis_v_mm):
            step=np.diff(axis)
            if not np.all(step>0) or not np.allclose(step,step[0]):raise ValueError('Uniform increasing coordinates required')

    @cached_property
    def extent(self):
        u,v=self.axis_u_mm,self.axis_v_mm
        du=u[1]-u[0];dv=v[1]-v[0]
        return (float(u[0]-du/2),float(u[-1]+du/2),float(v[0]-dv/2),float(v[-1]+dv/2))

    @cached_property
    def peak_w_m2(self):return float(self.intensity_w_m2.max())

    def sample(self,u_mm,v_mm):
        left,right,bottom,top=self.extent
        if not left<=u_mm<right or not bottom<=v_mm<top:return None
        j=min(len(self.axis_u_mm)-1,int((u_mm-left)/(right-left)*len(self.axis_u_mm)))
        i=min(len(self.axis_v_mm)-1,int((v_mm-bottom)/(top-bottom)*len(self.axis_v_mm)))
        intensity=float(self.intensity_w_m2[i,j])
        phase=None
        if self.phase_rad is not None and intensity>=self.peak_w_m2*1e-6 and intensity>0:
            phase=float(self.phase_rad[i,j])
        return dict(row=i,column=j,u_mm=float(self.axis_u_mm[j]),v_mm=float(self.axis_v_mm[i]),
                    intensity_w_m2=intensity,phase_rad=phase)


def wave_profile(data):
    """Build once on first figure open, retaining the full computed resolution."""
    if '_figure_snapshot' not in data:
        grid=data['grid'];preview=data['preview']
        left=preview['min_u_mm']-grid.dx/2;right=left+preview['span_mm']
        data['_figure_snapshot']=ProfileData(abs(data['field'])**2*1000,grid.axis,grid.axis,
            data['target_label'],data.get('method_label','Scalar ASM'),data.get('calculated_at',timestamp_kst()),
            np.angle(data['field']),(left,right,left,right))
    return data['_figure_snapshot']


def gaussian_profile(reading,halfspan,n=513):
    axis=np.linspace(-halfspan,halfspan,n);u,v=np.meshgrid(axis,axis)
    relative=np.exp(-2*(((u-reading.offset_mm)*reading.cos_incidence/reading.beam_radius_mm)**2
                        +(v/reading.beam_radius_mm)**2))
    label=f'{reading.screen_id} / {reading.source_id} / branch {reading.branch_id}'
    return ProfileData(relative*reading.peak_irradiance_w_m2,axis,axis,label,
        'Gaussian q (ideal)',timestamp_kst())
