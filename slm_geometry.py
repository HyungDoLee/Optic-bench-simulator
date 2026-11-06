"""Exact 3D reflection/grating directions; the bench GUI remains a coplanar view.

The grating axis is tangent to the LCOS surface. Phase is the total reflected
phase. Tangential wavevector conservation determines propagating orders.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class V3:
    x: float
    y: float
    z: float=0.
    def __add__(self,o):return V3(self.x+o.x,self.y+o.y,self.z+o.z)
    def __sub__(self,o):return V3(self.x-o.x,self.y-o.y,self.z-o.z)
    def __mul__(self,s):return V3(self.x*s,self.y*s,self.z*s)
    def dot(self,o):return self.x*o.x+self.y*o.y+self.z*o.z
    def unit(self):
        size=math.sqrt(self.dot(self))
        if not math.isfinite(size) or size==0:raise ValueError('Invalid direction')
        return self*(1/size)


def reflected(incident,normal):
    d=incident.unit();n=normal.unit()
    return (d-n*(2*d.dot(n))).unit()


def order_direction(incident,normal,grating_axis,wavelength_nm,period_mm,order):
    if wavelength_nm<=0 or period_mm<=0:raise ValueError('Positive wavelength/period required')
    d=incident.unit();n=normal.unit();g=grating_axis.unit()
    if abs(n.dot(g))>1e-10:raise ValueError('Grating axis must be tangent to the surface')
    tangent=d-n*d.dot(n)+g*(order*wavelength_nm*1e-6/period_mm)
    remainder=1-tangent.dot(tangent)
    if remainder<0:return None  # Evanescent order, no ray in air.
    return (tangent-n*math.copysign(math.sqrt(remainder),d.dot(n))).unit()


def configure_incidence(scene,component,degrees):
    """Preset-only input-arm adjustment; keep outgoing specular relay axis fixed."""
    if not 2<=abs(degrees)<=10:
        raise ValueError('This preset requires |incidence|=2..10° to clear the relay lens; check the device datasheet')
    source=next((c for c in scene['components'] if c['id']==component.get('slmIncidentSource')),None)
    if source is None:raise ValueError('Automatic incidence adjustment needs the preset input arm')
    outgoing=math.radians(component.get('slmRelayAxisDeg',180.))
    normal_angle=math.degrees(outgoing)-180+degrees
    n=V3(math.cos(math.radians(normal_angle)),math.sin(math.radians(normal_angle)))
    d=reflected(V3(math.cos(outgoing),math.sin(outgoing)),n)
    length=component.get('slmSourceDistanceMm',300.)
    source.update(x=component['x']-length*d.x,y=component['y']-length*d.y,
                  angle=math.degrees(math.atan2(d.y,d.x)))
    component.update(angle=normal_angle,slmDesignIncidenceDeg=degrees)
    for c in scene['components']:
        if c.get('slmLinkedFilter')==component['id']:
            from slm import carrier_period
            period=carrier_period(component)
            c['filterOffsetMm']=component.get('slmCarrierSign',1)*wavelength(source)*c.get('fourierFocalMm',200)/(period*math.cos(math.radians(degrees))) if period else 0.


def wavelength(source):return float(source['lambdaNm'])*1e-6


def order_segments(scene,result):
    """0/+1 direction diagnostics, not order-efficiency predictions or a 3D GUI."""
    from optics import Vec,normal,tangent,intersection,table_exit_distance,lens_direction,mirror_direction,MAX_PROPAGATION_MM,EPS
    from slm import carrier_period
    rows=[]
    slms={c['id']:c for c in scene['components'] if c['type']=='slm'}
    for source_id,component in slms.items():
        period=carrier_period(component)
        if not period:continue
        hit=next((s for s in result.segments if abs(s.end.x-component['x'])<EPS and abs(s.end.y-component['y'])<EPS),None)
        if hit is None:continue
        n=normal(component['angle']);g=tangent(n)
        for order in (0,1):
            d3=order_direction(V3(hit.direction.x,hit.direction.y),V3(n.x,n.y),V3(g.x,g.y),hit.wavelength_nm,period,order*component.get('slmCarrierSign',1))
            if d3 is None:continue
            d=Vec(d3.x,d3.y);p=hit.end;path=hit.path_end_mm
            for _ in range(36):
                limit=min(MAX_PROPAGATION_MM-path,table_exit_distance(p,d,scene['table']['widthMm'],scene['table']['heightMm']))
                if limit<=EPS:break
                candidates=[]
                for c in scene['components']:
                    if c['type']=='laser':continue
                    found=intersection(p,d,c)
                    if found and found[0]<=limit:candidates.append((found,c))
                chosen=min(candidates,key=lambda v:v[0][0]) if candidates else None
                length=chosen[0][0] if chosen else limit
                end=p+d*length;path+=length
                rows.append(dict(order=order,start=p,end=end,path_mm=path,blocked=False))
                if chosen is None:break
                (_,_,along,cn),c=chosen;p=end
                if c['type']=='spatial_filter':
                    if abs(along-c.get('filterOffsetMm',0))>c.get('filterRadiusMm',.2):
                        rows[-1]['blocked']=True;break
                elif c['type']=='lens':
                    forward=cn if d.dot(cn)>=0 else cn*(-1)
                    off=(p-Vec(c['x'],c['y'])).dot(tangent(forward))
                    d,_,_=lens_direction(d,cn,off,c['focalMm'])
                elif c['type'] in ('sample','mirror','slm'):d=mirror_direction(d,cn)
                elif c['type']=='screen':break
                elif c['type']=='splitter':
                    # Outbound diagnostic follows transmission, return follows
                    # the detector pick-off. Other ports are traced by the q engine.
                    if c.get('orderPickoff') and d.x>0:d=mirror_direction(d,cn)
    return rows
