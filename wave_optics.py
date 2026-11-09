"""Scalar local-plane wave optics, separate from the fast ray/q engine.

Units: mm, nm and mW; |E|² is mW/mm². Time convention exp(-i omega t),
ASM exp(+ikz), thin lens exp(-ikr²/2f). Overall propagation phase is omitted;
interferometer users must explicitly supply relative piston phase.
Finite FFT windows are periodic. Guard checks reject lost power/edge wrap and
under-sampled phase masks rather than silently claiming an accurate solution.
"""
from dataclasses import dataclass
from concurrent.futures import CancelledError
import math
import numpy as np


@dataclass(frozen=True)
class Grid:
    n: int = 512
    width_mm: float = 4.

    def __post_init__(self):
        if not 32 <= self.n <= 2048 or self.n % 2:
            raise ValueError('Grid needs an even size, 32..2048')
        if not math.isfinite(self.width_mm) or self.width_mm <= 0:
            raise ValueError('Grid width must be finite and positive')

    @property
    def dx(self): return self.width_mm/self.n
    @property
    def axis(self): return (np.arange(self.n)-self.n//2)*self.dx
    @property
    def xy(self): return np.meshgrid(self.axis,self.axis)


def power(field,grid):
    return float(np.sum(np.abs(field)**2)*grid.dx**2)


def gaussian(grid,wavelength_nm,q,power_mw=1.):
    if q.imag<=0 or wavelength_nm<=0 or power_mw<0:
        raise ValueError('Invalid Gaussian field parameters')
    x,y=grid.xy
    lam=wavelength_nm*1e-6
    w2=lam/math.pi*abs(q)**2/q.imag
    return math.sqrt(2*power_mw/(math.pi*w2))*np.exp(1j*math.pi*(x*x+y*y)/(lam*q.conjugate()))


def second_moment_radius(field,grid):
    """2 sigma_x, 2 sigma_y, equal to w for an untruncated Gaussian."""
    intensity=np.abs(field)**2
    total=float(intensity.sum())
    if total<=0:raise ValueError('No field power')
    x,y=grid.xy
    mx=float((intensity*x).sum()/total);my=float((intensity*y).sum()/total)
    return (2*math.sqrt(float((intensity*(x-mx)**2).sum()/total)),
            2*math.sqrt(float((intensity*(y-my)**2).sum()/total)))


def field_moments(field,grid,wavelength_nm,spectrum=None):
    """Power-weighted position and transverse k, distinct from the q/ray axis.

    Angles describe the mean propagating direction, not the entire angular
    spread. For a multi-order field the mean is not the +1 chief ray.
    """
    intensity=np.abs(field)**2;total=float(intensity.sum())
    if total<=0:raise ValueError('No field power for moments')
    axis=grid.axis;mx=intensity.sum(axis=0);my=intensity.sum(axis=1)
    cu=float((mx*axis).sum()/total);cv=float((my*axis).sum()/total)
    ru=2*math.sqrt(max(0.,float((mx*(axis-cu)**2).sum()/total)))
    rv=2*math.sqrt(max(0.,float((my*(axis-cv)**2).sum()/total)))
    spectral=np.abs(np.fft.fft2(field) if spectrum is None else spectrum)**2
    norm=float(spectral.sum());freq=np.fft.fftfreq(grid.n,grid.dx)
    fu=float((spectral.sum(axis=0)*freq).sum()/norm)
    fv=float((spectral.sum(axis=1)*freq).sum()/norm)
    su=wavelength_nm*1e-6*fu;sv=wavelength_nm*1e-6*fv
    longitudinal=math.sqrt(max(0.,1-su*su-sv*sv))
    return dict(centroid_mm=[cu,cv],radius_2sigma_mm=[ru,rv],
                mean_transverse_sine=[su,sv],mean_k_rad_mm=[2*math.pi*fu,2*math.pi*fv],
                angle_deg=[math.degrees(math.atan2(su,longitudinal)),math.degrees(math.atan2(sv,longitudinal))])


def propagate(field,grid,wavelength_nm,length_mm,*,strict=True,diagnostics=None):
    """Band-limited exact scalar ASM; no artificial power renormalization.

    Local derivative of transfer phase must be sampled in both frequency axes.
    Evanescent components are excluded; negative propagation is not permitted.
    """
    if not math.isfinite(length_mm) or length_mm<0 or wavelength_nm<=0:
        raise ValueError('Propagation distance must be nonnegative; wavelength positive')
    if np.shape(field)!=(grid.n,grid.n):raise ValueError('Field/grid shape mismatch')
    if length_mm==0:
        if diagnostics is not None:diagnostics.update(field_moments(field,grid,wavelength_nm))
        return np.array(field,copy=True)
    lam=wavelength_nm*1e-6
    fx,fy=np.meshgrid(np.fft.fftfreq(grid.n,grid.dx),np.fft.fftfreq(grid.n,grid.dx))
    s2=lam**2*(fx*fx+fy*fy)
    root=np.sqrt(np.maximum(1-s2,0))
    mask=(s2<1)&(length_mm*lam*np.abs(fx)<=grid.width_mm*root/2)&(length_mm*lam*np.abs(fy)<=grid.width_mm*root/2)
    # sqrt(1-s²)-1 = -s²/(1+sqrt(1-s²)), avoiding cancellation at low NA.
    phase=-2*math.pi/lam*length_mm*s2/(1+root)
    spectrum=np.fft.fft2(field)
    output_spectrum=spectrum*mask*np.exp(1j*phase)
    out=np.fft.ifft2(output_spectrum)
    if strict:
        before=power(field,grid);after=power(out,grid)
        if before>0 and after < before*(1-1e-5):
            raise ValueError('ASM band limit removed significant power: enlarge window/refine sampling')
        intensity=np.abs(out)**2
        rim=np.ones(intensity.shape,dtype=bool);rim[4:-4,4:-4]=False
        if intensity.sum()>0 and intensity[rim].sum()/intensity.sum()>1e-4:
            raise ValueError('FFT window boundary contains power: increase field of view')
    if diagnostics is not None:diagnostics.update(field_moments(out,grid,wavelength_nm,output_spectrum))
    return out


def pupil(grid,radius_mm,offset_mm=0.):
    if not math.isfinite(radius_mm) or radius_mm<=0:raise ValueError('Aperture radius must be positive')
    x,y=grid.xy
    return ((x+offset_mm)**2+y*y <= radius_mm**2)


def fourier_plane(field,grid,wavelength_nm,focal_mm):
    """Ideal front-focal -> back-focal field (scaled FFT, no pupil implied).

    A real lens pupil must be applied separately at its own plane. Output pixel
    pitch is lambda*f/(N*dx); absolute power normalization is preserved.
    """
    if wavelength_nm<=0 or focal_mm<=0:raise ValueError('Positive wavelength/focal length required')
    scale=wavelength_nm*1e-6*focal_mm
    output_grid=Grid(grid.n,scale/grid.dx)
    field_out=-1j*grid.dx**2/scale*np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(field)))
    return field_out,output_grid


def lens(field,grid,wavelength_nm,focal_mm,radius_mm=math.inf,offset_mm=0.):
    if not math.isfinite(focal_mm) or abs(focal_mm)<1e-12:raise ValueError('Invalid focal length')
    x,y=grid.xy
    mask=np.ones(field.shape,dtype=bool) if math.isinf(radius_mm) else pupil(grid,radius_mm,offset_mm)
    # Only illuminated support matters, not phase in a zero-power outer pupil.
    support=(np.abs(field)**2>np.max(np.abs(field)**2)*1e-8)&mask
    slope=2*math.pi/(wavelength_nm*1e-6*abs(focal_mm))*np.maximum(np.abs(x+offset_mm),np.abs(y))
    if np.any(slope[support]*grid.dx>math.pi/2):
        raise ValueError('Lens phase is undersampled; refine grid')
    return field*mask*np.exp(-1j*math.pi*((x+offset_mm)**2+y*y)/(wavelength_nm*1e-6*focal_mm))


def complex_sample(field,grid,reflectivity,phase_rad=0.,period_mm=0.,phase_depth_rad=0.):
    """Local phase screen, NOT RCWA/material-dependent diffraction efficiency."""
    if not 0<=reflectivity<=1:raise ValueError('Reflectivity must be 0..1')
    if period_mm<0:raise ValueError('Grating period must be nonnegative')
    if period_mm and period_mm<8*grid.dx:
        raise ValueError('Sample period unresolved: use local fine grid or grating-order model')
    x,_=grid.xy
    phase=phase_rad+(phase_depth_rad*np.cos(2*math.pi*x/period_mm) if period_mm else 0.)
    return field*math.sqrt(reflectivity)*np.exp(1j*phase)


def coherent_splitter(first,second,reflectivity=.5):
    """Lossless reciprocal two-port unitary S; r=i√R, t=√(1-R).

    Inputs must already share a transverse coordinate system, wavelength,
    sampling and reference plane. Relative propagation phase is user supplied.
    """
    if not 0<=reflectivity<=1 or np.shape(first)!=np.shape(second):
        raise ValueError('Splitter inputs must match; R must be 0..1')
    r=1j*math.sqrt(reflectivity);t=math.sqrt(1-reflectivity)
    return t*first+r*second,r*first+t*second


def detector(field,grid,radius_mm,responsivity_a_w=0.,offset_mm=0.):
    if not math.isfinite(responsivity_a_w) or responsivity_a_w<0:
        raise ValueError('Responsivity must be finite and nonnegative')
    collected=power(field*pupil(grid,radius_mm,offset_mm),grid)
    return dict(incident_power_mw=power(field,grid),collected_power_mw=collected,
                current_a=responsivity_a_w*collected*1e-3)


def grating_orders(wavelength_nm,period_nm,efficiencies,incidence_deg=0.,collection_na=1.):
    """Scalar grating equation in air; efficiencies are PROVIDED, not predicted.

    efficiencies maps integer order -> absolute incident-power fraction.
    Missing fraction is loss/transmission. RCWA is needed to predict this map.
    """
    if wavelength_nm<=0 or period_nm<=0 or not 0<=collection_na<=1:
        raise ValueError('Invalid grating inputs')
    if any(not isinstance(m,int) or not math.isfinite(e) or e<0 for m,e in efficiencies.items()) or sum(efficiencies.values())>1+1e-12:
        raise ValueError('Order efficiencies must be nonnegative and sum to <=1')
    rows=[]
    for m,e in sorted(efficiencies.items()):
        sine=math.sin(math.radians(incidence_deg))+m*wavelength_nm/period_nm
        propagating=abs(sine)<=1
        if not propagating and e>0:raise ValueError('Nonzero power assigned to evanescent order')
        rows.append(dict(order=m,angle_deg=math.degrees(math.asin(sine)) if propagating else None,
                         efficiency=e,collected=propagating and abs(sine)<=collection_na,
                         minimum_na=abs(sine)))
    return rows


def trace_wave(scene,result,reading,grid=None,*,cancel_event=None):
    """Propagate one existing ray branch; paraxial local planes in air only.

    Gaussian rays provide routing, NOT fields clipped into missing geometric
    branches. Does not discover scattered paths or recombine separate branches.
    Normal-incidence lenses/sample/detector required; ideal splitter folds allowed.
    """
    method=scene.get('wavePropagation','asm')
    if method=='fresnel':
        from fresnel_optics import trace_fresnel
        return trace_fresnel(scene,result,reading,grid,cancel_event=cancel_event)
    if method!='asm':raise ValueError('Unknown wave propagation method')
    from optics import MAX_PROPAGATION_MM,q_from_source,normal,tangent,Vec
    config=scene.get('waveGrid',{})
    grid=grid or Grid(config.get('n',512),config.get('widthMm',4.))
    components={c['id']:c for c in scene['components']}
    source=components[reading.source_id]
    lam=float(source['lambdaNm'])
    field=gaussian(grid,lam,q_from_source(source),float(source['powerMw']))
    segments=[s for s in result.branch_segments(reading.branch_id) if s.path_end_mm<=reading.path_mm+1e-8]
    if not segments or segments[-1].path_end_mm>MAX_PROPAGATION_MM:
        raise ValueError('No supported wave path within 2500 mm')
    filter_losses=[]
    arrivals=[]
    for i,segment in enumerate(segments):
        if cancel_event is not None and cancel_event.is_set():raise CancelledError('Wave calculation cancelled')
        arrival={}
        field=propagate(field,grid,lam,segment.length_mm,diagnostics=arrival)
        if cancel_event is not None and cancel_event.is_set():raise CancelledError('Wave calculation cancelled')
        hit=next((h for h in result.hits if h[2]==segment.branch_id and abs(h[1].x-segment.end.x)<1e-7 and abs(h[1].y-segment.end.y)<1e-7),None)
        if not hit:raise ValueError('Missing optical interaction')
        component=components[hit[0]];kind=component['type']
        reference_normal=normal(float(component.get('angle',0)))
        u=tangent(segment.direction);su,sv=arrival['mean_transverse_sine']
        longitudinal=math.sqrt(max(0.,1-su*su-sv*sv))
        projected=(segment.direction*longitudinal+u*su).dot(reference_normal)
        arrival.update(component=component['id'],path_mm=segment.path_end_mm,
                       mean_incidence_deg=math.degrees(math.acos(min(1.,abs(projected)))))
        if max(abs(a) for a in arrival['angle_deg'])>5:
            raise ValueError('Mean wave direction exceeds the 5° paraxial transport limit')
        arrivals.append(arrival)
        cosine=abs(segment.direction.dot(normal(float(component.get('angle',0)))))
        if kind in ('lens','sample','screen','probe','spatial_filter') and cosine<.99999:
            raise ValueError('Wave path needs near-normal lens/sample/detector incidence')
        if i==len(segments)-1:break  # Return the incident field at the selected plane.
        if kind=='lens':
            n=normal(float(component.get('angle',0)))
            forward=n if segment.direction.dot(n)>=0 else n*(-1)
            off=(segment.end-Vec(component['x'],component['y'])).dot(tangent(forward))
            if abs(off)>1e-7:raise ValueError('Decentered chief-ray wave transport is not supported')
            field=lens(field,grid,lam,float(component['focalMm']),float(component.get('diameterMm',25.4))/2)
        if kind=='sample':
            field=complex_sample(field,grid,float(component.get('reflectivity',1)),
                                 float(component.get('phaseRad',0)),float(component.get('periodMm',0)),
                                 float(component.get('phaseDepthRad',0)))
            field=field*pupil(grid,float(component.get('diameterMm',25.4))/2)
        if kind=='slm':
            from slm import slm_mask
            off=(segment.end-Vec(component['x'],component['y'])).dot(tangent(normal(float(component.get('angle',0)))))
            if abs(off)>1e-7:raise ValueError('SLM wave plane must be centered on the chief ray')
            mask,_=slm_mask(component,grid,lam,field,math.degrees(math.acos(min(1.,cosine))))
            field*=mask
            field=field[:,(-np.arange(grid.n))%grid.n]
        if kind=='spatial_filter':
            orientation=tangent(normal(float(component.get('angle',0)))).dot(tangent(segment.direction))
            center=component.get('filterOffsetMm',0)*orientation
            before=power(field,grid)
            field=field*pupil(grid,component.get('filterRadiusMm',.2),-center)
            filter_losses.append(dict(component=component['id'],incident_mw=before,passed_mw=power(field,grid)))
        if kind in ('mirror','sample','splitter'):
            reflected=segment.direction.dot(segments[i+1].direction)<.99999
            if kind=='splitter':
                r=float(component.get('reflectivity',.5))
                field*=1j*math.sqrt(r) if reflected else math.sqrt(1-r)
            elif kind=='mirror':field*=math.sqrt(float(component.get('reflectivity',1)))
            if reflected:field=field[:,(-np.arange(grid.n))%grid.n]
    target=components[reading.screen_id]
    values=detector(field,grid,float(target.get('diameterMm',25.4))/2,
                    float(target.get('responsivityAW',0)),reading.offset_mm)
    out=dict(field=field,grid=grid,filter_losses=filter_losses,moments=arrivals[-1],arrivals=arrivals,**values)
    if target['type']=='spatial_filter':
        from slm import carrier_period
        linked=components.get(target.get('slmLinkedFilter'),{})
        direction=segments[-1].direction
        orientation=tangent(normal(float(target.get('angle',0)))).dot(tangent(direction))
        center=(target.get('filterOffsetMm',0)-reading.offset_mm)*orientation
        radius=target.get('filterRadiusMm',.2)
        out.update(filter_center_mm=center,filter_radius_mm=radius,
                   has_carrier=bool(linked and carrier_period(linked)),
                   selected_roi_mw=power(field*pupil(grid,radius,-center),grid),
                   zero_roi_mw=power(field*pupil(grid,radius,reading.offset_mm*orientation),grid))
    return out
