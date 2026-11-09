"""Prepare a fixed, inexpensive GUI preview in the calculation worker.

No Tk calls belong here. Full-resolution arrays are inspected once per explicit
calculation; selection/resize/drag only redraw this small cached preview.
"""
import math
import numpy as np
from PIL import Image


def prepare_wave_view(data,reading,target):
    grid=data['grid'];intensity=np.abs(data['field'])**2
    total=float(intensity.sum());peak=float(intensity.max())
    half=.4
    if total:
        for marginal in (intensity.sum(axis=0),intensity.sum(axis=1)):
            cdf=np.cumsum(marginal)/total
            lo=min(grid.n-1,int(np.searchsorted(cdf,.005)))
            hi=min(grid.n-1,int(np.searchsorted(cdf,.995)))
            half=max(half,abs(grid.axis[lo]),abs(grid.axis[hi]))
        # Also show the complete phase support (I/Ipeak >= 1e-6), with a small
        # margin, so an off-axis spot is not cut in half by the preview crop.
        visible=intensity>=peak*1e-6
        for along in (visible.any(axis=0),visible.any(axis=1)):
            indices=np.flatnonzero(along)
            if len(indices):half=max(half,abs(grid.axis[indices[0]])+2*grid.dx,abs(grid.axis[indices[-1]])+2*grid.dx)
    if 'filter_center_mm' in data:
        half=max(half,abs(data['filter_center_mm'])+1.1*data['filter_radius_mm'])
    radius=int(np.ceil(half/grid.dx))
    start=max(0,grid.n//2-radius);end=min(grid.n,grid.n//2+radius+1)
    view=intensity[start:end,start:end]
    normalized=view/peak if peak else view
    scale=np.sqrt(np.clip(normalized,0,1))[...,None]
    rgb=np.asarray(250*(1-scale)+np.array([36,91,145])*scale,dtype=np.uint8)
    image=Image.fromarray(rgb).resize((212,212),Image.Resampling.BILINEAR)
    # Phase is cyclic; dark pixels below the stated intensity threshold have no
    # displayed phase. Nearest-neighbor resizing avoids averaging across ±pi.
    phase=np.angle(data['field'][start:end,start:end])
    hue=np.uint8(np.mod((phase+math.pi)/(2*math.pi),1.)*255)
    value=np.where(normalized>=1e-6,235,0).astype(np.uint8)
    hsv=np.stack((hue,np.full(hue.shape,220,dtype=np.uint8),value),axis=-1)
    phase_image=Image.frombytes('HSV',(hue.shape[1],hue.shape[0]),hsv.tobytes()).convert('RGB').resize((212,212),Image.Resampling.NEAREST)
    row=normalized[grid.n//2-start,:]
    curve=np.interp(np.linspace(0,max(0,len(row)-1),241),np.arange(len(row)),row).tolist()
    moments=data['moments']
    radii=moments['radius_2sigma_mm']
    current=f'{data["current_a"]:.6g} A' if target.get('responsivityAW',0)>0 else 'not configured'
    readout=(f'Path           {reading.path_mm:.6g} mm\n'
        f'Output grid    {grid.n}×{grid.n}\n'
        f'dx / FOV       {1000*grid.dx:.6g} µm / {grid.width_mm:.6g} mm\n'
        f'q ideal w      {reading.beam_radius_mm:.6g} mm\n'
        f'q [mm] {reading.q.real:.4g}+{reading.q.imag:.4g}i\n'
        f'ABCD source -> plane\n'
        f'[{reading.abcd.a:.4g}, {reading.abcd.b:.4g} mm]\n'
        f'[{reading.abcd.c:.4g}/mm, {reading.abcd.d:.4g}]\n'
        f'Wave 2σ u,v    {radii[0]:.5g}, {radii[1]:.5g} mm\n'
        f'Centroid u,v   {moments["centroid_mm"][0]:.5g}, {moments["centroid_mm"][1]:.5g} mm\n'
        f'Mean angle u,v {moments["angle_deg"][0]:.5g}, {moments["angle_deg"][1]:.5g} deg\n'
        f'Wave incident  {data["incident_power_mw"]:.6g} mW\n'
        f'Collected      {data["collected_power_mw"]:.6g} mW\n'
        f'PD current     {current}\n'
        f'Wave peak      {peak*1000:.6g} W/m²')
    if 'selected_roi_mw' in data:
        label='+1 / hole ROI' if data.get('has_carrier') else 'Hole ROI'
        readout+=f'\n0 ROI          {data["zero_roi_mw"]:.5g} mW\n{label:14} {data["selected_roi_mw"]:.5g} mW'
    if data.get('propagation_method')=='fresnel':
        readout+='\nIdeal Fresnel: no clipping / pinhole.\nSLM active area / pixels retained.'
    readout+='\nPhase: reference piston omitted;\ndark where I/Ipeak < 1e-6.'
    return dict(image=image,phase_image=phase_image,curve=curve,min_u_mm=float(grid.axis[start]),
                span_mm=(end-start)*grid.dx,visible_fraction=float(view.sum()/total) if total else 0.,
                readout=readout)
