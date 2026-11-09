"""Ideal paraxial forward diffraction using the Collins/Fresnel integral.

Free space and centered thin lenses are combined into an ABCD block between
phase screens. This is an evaluation of the Fresnel integral, not exact ASM.
The physical sampling changes with B (or magnification at B=0). Geometrical
lens/sample/camera pupils and spatial filters are deliberately bypassed.
SLM active area, pixel response and specified reflection coefficients remain.
Global axial/Gouy piston is a reference choice; branch interference is absent.
"""
import math
from concurrent.futures import CancelledError
import numpy as np

from optics import ABCD,propagation_matrix,lens_matrix,MAX_PROPAGATION_MM,normal,tangent,Vec,q_from_source
from wave_optics import Grid,gaussian,power,field_moments,complex_sample


def _chirp(field,grid,wavelength_nm,coefficient):
    """Multiply exp(i*pi*coefficient*r²/lambda), checking lit support."""
    if coefficient==0:return field
    x,y=grid.xy;lam=wavelength_nm*1e-6
    support=abs(field)**2>float(np.max(abs(field)**2))*1e-8
    slope=2*math.pi*abs(coefficient)/lam*np.maximum(abs(x),abs(y))
    if np.any(slope[support]*grid.dx>math.pi/2):
        raise ValueError('Fresnel quadratic phase undersampled: refine grid or move away from a near-image plane')
    return field*np.exp(1j*math.pi*coefficient*(x*x+y*y)/lam)


def fresnel_transform(field,grid,wavelength_nm,matrix):
    """Scaled Collins integral for a centered lossless ABCD system.

    B!=0: dx_out=lambda*abs(B)/(N*dx_in), scaled FFT plus input/output chirps.
    B=0: exact paraxial image, dx_out=abs(A)*dx_in; no FFT interpolation.
    The 2-D Jacobian fixes absolute power, without post-hoc normalization.
    """
    if wavelength_nm<=0 or not math.isfinite(wavelength_nm):raise ValueError('Positive wavelength required')
    if np.shape(field)!=(grid.n,grid.n) or not np.isfinite(field).all():raise ValueError('Finite field must match grid')
    a,b,c,d=matrix.a,matrix.b,matrix.c,matrix.d
    if not all(math.isfinite(v) for v in (a,b,c,d)) or not math.isclose(a*d-b*c,1.,abs_tol=1e-9):
        raise ValueError('Fresnel ABCD matrix must be finite with determinant 1')
    if abs(b)<1e-9:
        if abs(a)<1e-12:raise ValueError('Singular Fresnel image transform')
        output_grid=Grid(grid.n,abs(a)*grid.width_mm)
        if a<0:
            reverse=(-np.arange(grid.n))%grid.n
            out=field[np.ix_(reverse,reverse)]/abs(a)
        else:out=np.array(field,copy=True)/abs(a)
        return _chirp(out,output_grid,wavelength_nm,c/a),output_grid
    lam=wavelength_nm*1e-6
    output_grid=Grid(grid.n,lam*abs(b)/grid.dx)
    prepared=np.fft.ifftshift(_chirp(field,grid,wavelength_nm,a/b))
    if b>0:transformed=np.fft.fft2(prepared)
    else:transformed=np.fft.ifft2(prepared)*grid.n**2
    out=-1j*grid.dx**2/(lam*b)*np.fft.fftshift(transformed)
    out=_chirp(out,output_grid,wavelength_nm,d/b)
    return out,output_grid


def trace_fresnel(scene,result,reading,grid=None,*,cancel_event=None,progress_callback=None):
    """One existing coplanar ray route, with ideal unlimited linear optics.

    A still-unmodulated Gaussian is evaluated analytically at the first phase
    screen. Thereafter Fresnel ABCD blocks propagate the actual complex field.
    Combining a complete focal block analytically avoids sampling artificial
    intermediate lens chirps. Detuned B!=0 systems retain their chirps.
    """
    config=scene.get('waveGrid',{})
    report=progress_callback or (lambda fraction,stage:None)
    report(0.,'Fresnel 입력 광장 준비')
    grid=grid or Grid(config.get('n',512),config.get('widthMm',4.))
    components={c['id']:c for c in scene['components']}
    source=components[reading.source_id];lam=float(source['lambdaNm'])
    segments=[s for s in result.branch_segments(reading.branch_id) if s.path_end_mm<=reading.path_mm+1e-8]
    if not segments or segments[-1].path_end_mm>MAX_PROPAGATION_MM:
        raise ValueError('No supported wave path within 2500 mm')
    field=None;pending=ABCD();factor=1.+0j
    source_q=q_from_source(source)
    arrivals=[];blocks=[];bypassed=[]
    units=len(segments)+1

    def cancelled():
        if cancel_event is not None and cancel_event.is_set():raise CancelledError('Wave calculation cancelled')

    def materialize(component,segment):
        nonlocal field,grid,pending,factor
        cancelled()
        report(i/units,'Fresnel 광장 계산 · '+component['id'])
        before_grid=grid
        if field is None:
            field=gaussian(grid,lam,pending.apply_q(source_q),float(source['powerMw']))*factor
            expected=float(source['powerMw'])*abs(factor)**2
            if expected>0 and abs(power(field,grid)/expected-1)>1e-5:
                raise ValueError('Incident Gaussian truncated by numerical FOV: enlarge the input window')
            mode='analytic incident Gaussian'
        else:
            field,grid=fresnel_transform(field,grid,lam,pending)
            field*=factor;mode='Fresnel integral' if abs(pending.b)>=1e-9 else 'Fresnel image'
        blocks.append(dict(end=component['id'],mode=mode,
            abcd=[pending.a,pending.b,pending.c,pending.d],input_dx_mm=before_grid.dx,output_dx_mm=grid.dx,
            n=grid.n,output_fov_mm=grid.width_mm))
        pending=ABCD();factor=1.+0j
        arrival=field_moments(field,grid,lam)
        if max(abs(a) for a in arrival['angle_deg'])>5:
            raise ValueError('Mean wave direction exceeds the 5° paraxial transport limit')
        su,sv=arrival['mean_transverse_sine'];longitudinal=math.sqrt(max(0.,1-su*su-sv*sv))
        projected=(segment.direction*longitudinal+tangent(segment.direction)*su).dot(normal(float(component.get('angle',0))))
        arrival.update(component=component['id'],path_mm=segment.path_end_mm,
            mean_incidence_deg=math.degrees(math.acos(min(1.,abs(projected)))))
        arrivals.append(arrival)
        cancelled()

    for i,segment in enumerate(segments):
        cancelled()
        report(i/units,f'Fresnel 전파 단계 {i+1}/{len(segments)}')
        pending=propagation_matrix(segment.length_mm) @ pending
        hit=next((h for h in result.hits if h[2]==segment.branch_id and abs(h[1].x-segment.end.x)<1e-7 and abs(h[1].y-segment.end.y)<1e-7),None)
        if not hit:raise ValueError('Missing optical interaction')
        component=components[hit[0]];kind=component['type']
        cosine=abs(segment.direction.dot(normal(float(component.get('angle',0)))))
        if kind in ('lens','sample','screen','probe','spatial_filter') and cosine<.99999:
            raise ValueError('Fresnel path needs near-normal lens/sample/detector incidence')
        if i==len(segments)-1:
            materialize(component,segment)
            report((i+1)/units,component['id']+' 도착');break
        if kind=='lens':
            n=normal(float(component.get('angle',0)))
            forward=n if segment.direction.dot(n)>=0 else n*(-1)
            off=(segment.end-Vec(component['x'],component['y'])).dot(tangent(forward))
            if abs(off)>1e-7:raise ValueError('Decentered Fresnel lens transport is not supported')
            pending=lens_matrix(float(component['focalMm'])) @ pending
            bypassed.append(component['id']+' pupil')
        elif kind=='slm':
            from slm import slm_mask
            off=(segment.end-Vec(component['x'],component['y'])).dot(tangent(normal(float(component.get('angle',0)))))
            if abs(off)>1e-7:raise ValueError('SLM wave plane must be centered on the chief ray')
            materialize(component,segment)
            mask,_=slm_mask(component,grid,lam,field,math.degrees(math.acos(min(1.,cosine))))
            field*=mask
            field=field[:,(-np.arange(grid.n))%grid.n]
        elif kind=='sample':
            if component.get('phaseRad',0) or component.get('phaseDepthRad',0):
                materialize(component,segment)
                field=complex_sample(field,grid,1.,float(component.get('phaseRad',0)),
                    float(component.get('periodMm',0)),float(component.get('phaseDepthRad',0)))
            factor*=math.sqrt(float(component.get('reflectivity',1)))
            bypassed.append(component['id']+' pupil')
        elif kind=='spatial_filter':bypassed.append(component['id']+' pinhole')
        if kind in ('mirror','sample','splitter'):
            reflected=segment.direction.dot(segments[i+1].direction)<.99999
            if kind=='splitter':
                r=float(component.get('reflectivity',.5))
                factor*=1j*math.sqrt(r) if reflected else math.sqrt(1-r)
            elif kind=='mirror':factor*=math.sqrt(float(component.get('reflectivity',1)))
            if reflected and field is not None:field=field[:,(-np.arange(grid.n))%grid.n]
        report((i+1)/units,component['id']+' 처리 완료')

    target=components[reading.screen_id];p=power(field,grid)
    responsivity=float(target.get('responsivityAW',0))
    out=dict(field=field,grid=grid,moments=arrivals[-1],arrivals=arrivals,
        incident_power_mw=p,collected_power_mw=p,current_a=responsivity*p*1e-3,
        filter_losses=[],propagation_method='fresnel',method_label='Fresnel ideal',
        blocks=blocks,bypassed_apertures=bypassed+[target['id']+' detector aperture'],
        model_note='Ideal Fresnel; lens/sample/detector apertures and pinholes bypassed. SLM active area/pixels retained.')
    report(1.,'Fresnel 광파워와 진단 계산 완료')
    return out
