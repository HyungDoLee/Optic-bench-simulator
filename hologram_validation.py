"""Local pixel-array/GS validation, separate from full-bench ASM.

One phase value per LCOS pixel is used for synthesis. The analytic square-pixel
sinc envelope describes the primary Fourier zone; higher lattice replicas are
not traced. This does not relax slm_mask's resolved-pixel sampling requirement.
"""
import math
import numpy as np


def illumination_sampling(waist_mm,pitch_mm,diameter_pixels,fov_mm,n,incidence_deg=0.):
    if min(waist_mm,pitch_mm,diameter_pixels,fov_mm,n)<=0:raise ValueError('Positive sampling/beam dimensions required')
    diameter=pitch_mm*diameter_pixels
    minimum_n=math.ceil(4*fov_mm/(pitch_mm*math.cos(math.radians(incidence_deg))))
    return dict(hologram_diameter_mm=diameter,gaussian_1e2_diameter_mm=2*waist_mm,
        edge_relative_intensity=math.exp(-2*(diameter/2/waist_mm)**2),
        power_inside_hologram=1-math.exp(-2*(diameter/2/waist_mm)**2),
        beam_1e2_diameter_pixels=2*waist_mm/pitch_mm,
        required_n_four_samples=minimum_n,next_power_of_two=1<<(minimum_n-1).bit_length(),
        resolved_pixels=n>=minimum_n,dx_um=1000*fov_mm/n)


def gs_phase(amplitude,target,iterations=60,seed=720):
    if amplitude.shape!=target.shape or np.any(amplitude<0) or np.any(target<0) or not target.sum()>0:
        raise ValueError('GS input amplitude/target must match and be nonnegative')
    target_amplitude=np.sqrt(target/target.sum()*np.sum(amplitude**2))
    phase=np.random.default_rng(seed).uniform(-math.pi,math.pi,amplitude.shape)
    history=[]
    for _ in range(iterations):
        far=np.fft.fftshift(np.fft.fft2(amplitude*np.exp(1j*phase),norm='ortho'))
        history.append(nrmse(abs(far)**2,target))
        constrained=target_amplitude*np.exp(1j*np.angle(far))
        phase=np.angle(np.fft.ifft2(np.fft.ifftshift(constrained),norm='ortho'))
    return phase,history


def nrmse(intensity,target):
    if intensity.sum()<=0:return math.inf
    a=intensity/intensity.sum();b=target/target.sum()
    return float(np.linalg.norm(a-b)/np.linalg.norm(b))


def pixel_fourier(field,pitch_mm,wavelength_nm,focal_mm,fill_factor=1.):
    if not 0<fill_factor<=1 or min(pitch_mm,wavelength_nm,focal_mm)<=0:
        raise ValueError('Invalid pixel Fourier parameters')
    n=field.shape[0]
    if field.shape!=(n,n):raise ValueError('Square pixel array required')
    lamf=wavelength_nm*1e-6*focal_mm
    freq=(np.arange(n)-n//2)/(n*pitch_mm)
    fx,fy=np.meshgrid(freq,freq)
    side=pitch_mm*math.sqrt(fill_factor)
    far=-1j*side**2/lamf*np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(field)))
    far*=np.sinc(side*fx)*np.sinc(side*fy)
    return far,(np.arange(n)-n//2)*lamf/(n*pitch_mm)


def gs_filter_benchmark(n=512,iterations=60):
    """Example 8 um LCOS, two Fourier spots; input peak 1 mW/mm².

    This local synthesis benchmark is not a device calibration or bench ASM.
    """
    pitch=.008;lam=720.;f=200.;w=2.048
    index=np.arange(n)-n//2;x,y=np.meshgrid(index*pitch,index*pitch)
    # External illumination pupil, not programmable SLM amplitude modulation.
    amplitude=np.exp(-(x*x+y*y)/w**2)*(x*x+y*y<=(n*pitch/2)**2)
    u,v=np.meshgrid(index,index)
    separation=8*n/512
    target=np.exp(-((u-separation)**2+v*v)/(2*(1.5*n/512)**2))
    target+=np.exp(-((u+separation)**2+v*v)/(2*(1.5*n/512)**2))
    phase,history=gs_phase(amplitude,target,iterations)
    final_intensity=abs(np.fft.fftshift(np.fft.fft2(amplitude*np.exp(1j*phase),norm='ortho')))**2
    carrier=n//16  # 16-pixel blaze, pitch*16 = 128 um.
    carrier_phase=2*math.pi*carrier*u/n
    desired,axis=pixel_fourier(amplitude*np.exp(1j*(phase+carrier_phase)),pitch,lam,f)
    residual,_=pixel_fourier(amplitude,pitch,lam,f)
    field=math.sqrt(.8)*desired+.1*residual
    shifted_target=np.roll(target,carrier,axis=1)
    uu,vv=np.meshgrid(axis,axis);center=axis[n//2+carrier];cell=axis[1]-axis[0]
    desired_power=float(np.sum(abs(desired)**2)*cell**2)
    residual_power=float(np.sum(abs(residual)**2)*cell**2)
    rows=[]
    for radius in (.2,.5):
        mask=(uu-center)**2+vv*vv<=radius*radius
        passed=field*mask
        rows.append(dict(radius_mm=radius,spatial_bandwidth_cycles_mm=radius/(lam*1e-6*f),
            target_pass_fraction=float(np.sum(abs(desired*mask)**2)*cell**2/desired_power),
            residual_pass_fraction=float(np.sum(abs(residual*mask)**2)*cell**2/residual_power),
            coherent_reconstruction_nrmse=nrmse(abs(passed)**2,shifted_target)))
    return dict(model='local pixel-array scalar Fourier synthesis; not full-bench ASM or measured hardware',
        wavelength_nm=lam,pitch_um=pitch*1000,hologram_pixels=n,beam_waist_mm=w,
        reported_power_unit='mW',input_peak_intensity_mw_mm2=1.,
        carrier_period_um=pitch*16*1000,carrier_center_mm=float(center),
        gs_iterations=iterations,gs_initial_nrmse=history[0],gs_final_nrmse=nrmse(final_intensity,target),
        modulated_primary_zone_power=float(np.sum(abs(desired)**2)*cell**2),
        input_pupil_power=float(np.sum(amplitude**2)*pitch**2),
        higher_lattice_orders_traced=False,filters=rows)
