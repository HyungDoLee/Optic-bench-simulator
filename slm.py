"""Reflective phase-only LCOS; validation keeps the ray engine stdlib-only.

No hardware SDK, polarization response or gray-level/voltage LUT is implied.
Phase is the total calibrated reflected phase in radians, not single-pass LC phase.
Efficiency and dead space represent passive losses, not amplitude programming.
"""
import math

PATTERNS=('flat','blaze','lens','vortex','custom')


def slm_component(**overrides):
    c=dict(id='slm-1',type='slm',x=250.,y=450.,angle=0.,diameterMm=12.,
           slmHeightMm=8.,slmMode='reflective',slmPattern='flat',slmCoreMm=0.,
           slmEfficiency=1.,slmAmplitude=1.,slmPhaseLevels=0,slmStrokeRad=2*math.pi,
           slmPitchMm=0.,slmFillFactor=1.,slmPeriodMm=.5,slmFocalMm=200.,
           slmCharge=1,slmOffsetRad=0.,slmCarrierPeriodMm=0.,slmCarrierSign=1,
           slmResidualPower=0.,slmResidualPhaseRad=0.,slmDeadReflectivity=0.)
    c.update(overrides)
    return c


def validate_slm(raw):
    c=slm_component(**raw)
    if c['slmMode']!='reflective':raise ValueError('Phase-only LCOS must be reflective; reroute a legacy transmissive scene explicitly')
    if c['slmPattern'] not in PATTERNS:raise ValueError('Invalid SLM pattern')
    for key in ('diameterMm','slmHeightMm','slmEfficiency','slmAmplitude','slmPhaseLevels',
                'slmStrokeRad','slmPitchMm','slmFillFactor','slmPeriodMm','slmFocalMm',
                'slmCharge','slmOffsetRad','slmCoreMm','slmCarrierPeriodMm','slmCarrierSign',
                'slmResidualPower','slmResidualPhaseRad','slmDeadReflectivity'):
        c[key]=float(c[key])
        if not math.isfinite(c[key]):raise ValueError('Nonfinite SLM parameter: '+key)
    if c['diameterMm']<=0 or c['slmHeightMm']<=0:raise ValueError('SLM active dimensions must be positive')
    if not 0<=c['slmEfficiency']<=1 or not 0<=c['slmAmplitude']<=1:
        raise ValueError('SLM efficiency/amplitude must be 0..1')
    if c['slmAmplitude']!=1 or c['slmCoreMm']!=0:
        raise ValueError('Phase-only LCOS cannot program amplitude or attenuate a vortex core')
    if not 0<c['slmFillFactor']<=1:raise ValueError('SLM area fill factor must be >0 and <=1')
    if c['slmPitchMm']<0 or not 0<=c['slmStrokeRad']<=2*math.pi:
        raise ValueError('SLM pitch must be nonnegative and phase stroke 0..2π')
    if c['slmCoreMm']<0 or c['slmPeriodMm']<0:raise ValueError('SLM core/period must be nonnegative')
    if c['slmCarrierPeriodMm']<0 or c['slmCarrierSign'] not in (-1,1):raise ValueError('Invalid carrier period/sign')
    if not 0<=c['slmResidualPower']<=1 or not 0<=c['slmDeadReflectivity']<=1:
        raise ValueError('Residual/dead-space power coefficients must be 0..1')
    residual=math.sqrt(c['slmResidualPower'])
    if max(math.sqrt(c['slmEfficiency']),math.sqrt(c['slmDeadReflectivity']))+residual>1+1e-12:
        raise ValueError('Coherent residual model must be passive: sqrt(eta)+sqrt(residual)<=1')
    levels=c['slmPhaseLevels']
    if levels!=int(levels) or (levels!=0 and not 2<=levels<=4096):
        raise ValueError('SLM phase bins must be 0 (continuous) or integer 2..4096')
    c['slmPhaseLevels']=int(levels)
    if c['slmCharge']!=int(c['slmCharge']) or abs(c['slmCharge'])>10:
        raise ValueError('Vortex charge must be an integer -10..10')
    c['slmCharge']=int(c['slmCharge'])
    for key in ('slmDesignIncidenceDeg','slmSourceDistanceMm','slmRelayAxisDeg'):
        if key in c:
            c[key]=float(c[key])
            if not math.isfinite(c[key]):raise ValueError('Invalid SLM geometry metadata')
    if 'slmSourceDistanceMm' in c and c['slmSourceDistanceMm']<=0:raise ValueError('Source distance must be positive')
    if c['slmPattern']=='blaze' and c['slmPeriodMm']<=0:
        raise ValueError('SLM grating period must be positive')
    if c['slmPattern']=='lens' and abs(c['slmFocalMm'])<1e-9:
        raise ValueError('SLM focal length must be nonzero')
    if 'slmPhaseMap' in c:
        rows=c['slmPhaseMap']
        if not isinstance(rows,list) or not 1<=len(rows)<=256 or not isinstance(rows[0],list) or not 1<=len(rows[0])<=256:
            raise ValueError('SLM phase map must be a rectangular 1..256 by 1..256 list')
        width=len(rows[0]);clean=[]
        for row in rows:
            if not isinstance(row,list) or len(row)!=width:raise ValueError('Ragged SLM phase map')
            converted=[float(v) for v in row]
            if not all(math.isfinite(v) for v in converted):raise ValueError('Nonfinite SLM phase map')
            clean.append(converted)
        c['slmPhaseMap']=clean
    if c['slmPattern']=='custom' and 'slmPhaseMap' not in c:raise ValueError('Import a phase map for custom SLM')
    return c


def carrier_period(component):
    return component.get('slmCarrierPeriodMm',0) or (component.get('slmPeriodMm',.5) if component.get('slmPattern')=='blaze' else 0.)


def slm_mask(component,grid,wavelength_nm,field=None,incidence_deg=0.):
    """Return the complex reflection coefficient and applied phase on a local grid.

    Finite rectangular area, optional sampled pixels/dead space and phase bins.
    Reflection direction/parity is handled by the path tracer, not this mask.
    """
    import numpy as np
    c=validate_slm(component)
    if not math.isfinite(wavelength_nm) or wavelength_nm<=0:raise ValueError('Invalid SLM wavelength')
    if not math.isfinite(incidence_deg) or not 0<=incidence_deg<=10:
        raise ValueError('Projected scalar LCOS model supports 0..10° incidence only')
    cosine=math.cos(math.radians(incidence_deg))
    # Incoming beam-normal coordinate -> LCOS surface coordinate. Reflection
    # then reverses local u in trace_wave. No extra cos loss in normal flux.
    x,y=grid.xy;x=x/cosine;u=x;v=y
    pitch=c['slmPitchMm'];pattern=c['slmPattern']
    aperture=(x>=-c['diameterMm']/2)&(x<c['diameterMm']/2)&(y>=-c['slmHeightMm']/2)&(y<c['slmHeightMm']/2)
    surface_aperture=aperture.copy()
    if pitch:
        if pitch*cosine<4*grid.dx:raise ValueError('SLM pixels unresolved: need at least 4 grid samples per pixel')
        u=pitch*np.floor(x/pitch+.5);v=pitch*np.floor(y/pitch+.5)
        localx=x-u;localy=y-v
        half=pitch*math.sqrt(c['slmFillFactor'])/2
        if 2*half<2*grid.dx:raise ValueError('SLM active pixel area unresolved')
        aperture &= (localx>=-half)&(localx<half)&(localy>=-half)&(localy<half)
    elif c['slmFillFactor']!=1:
        raise ValueError('SLM dead space needs a nonzero resolved pixel pitch')
    phase=np.full(x.shape,c['slmOffsetRad'])
    period=carrier_period(c)
    if period:
        if period*cosine<8*grid.dx or (pitch and period<4*pitch):
            raise ValueError('SLM grating unresolved: refine grid or increase period')
        phase+=c['slmCarrierSign']*2*math.pi*u/period
    if pattern=='lens':
        phase-=math.pi*(u*u+v*v)/(wavelength_nm*1e-6*c['slmFocalMm'])
        if field is not None:
            support=(abs(field)**2>np.max(abs(field)**2)*1e-8)&aperture
            spacing=max(grid.dx,pitch)
            slope=2*math.pi*np.maximum(abs(u),abs(v))/(wavelength_nm*1e-6*abs(c['slmFocalMm']))
            if np.any(slope[support]*spacing>math.pi/2):raise ValueError('SLM lens phase is undersampled')
    if pattern=='vortex':
        phase+=c['slmCharge']*np.arctan2(v,u)
    if pattern=='custom':
        data=np.asarray(c['slmPhaseMap'],dtype=float)
        ix=np.clip(np.floor((u/c['diameterMm']+.5)*data.shape[1]).astype(int),0,data.shape[1]-1)
        iy=np.clip(np.floor((v/c['slmHeightMm']+.5)*data.shape[0]).astype(int),0,data.shape[0]-1)
        # Require even the imported source cells to be spatially resolvable.
        if c['diameterMm']/data.shape[1]<2*grid.dx or c['slmHeightMm']/data.shape[0]<2*grid.dx:
            raise ValueError('Imported SLM cells unresolved; enlarge active area or refine grid')
        phase+=data[iy,ix]
    phase=np.minimum(np.mod(phase,2*math.pi),c['slmStrokeRad'])
    if c['slmPhaseLevels']:
        step=2*math.pi/c['slmPhaseLevels']
        phase=np.floor(phase/step+1e-12)*step
    # Fixed coherent surface reflection is not intentional amplitude control.
    # The amplitude-sum bound in validate_slm guarantees passivity per pixel.
    mask=(math.sqrt(c['slmEfficiency'])*aperture*np.exp(1j*phase)
          +math.sqrt(c['slmDeadReflectivity'])*(surface_aperture & ~aperture)
          +math.sqrt(c['slmResidualPower'])*surface_aperture*np.exp(1j*c['slmResidualPhaseRad']))
    return mask,phase
