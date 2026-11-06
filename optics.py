"""2D non-sequential chief-ray tracing + paraxial Gaussian q propagation.

Distances in mm, wavelengths in nm, powers in mW. XY is the optical bench
(top view; +Y points down on screen). Each branch is capped at 2500 mm of
CUMULATIVE free-space propagation, regardless of mirror reflections.

This is a scalar, circular, ideal Gaussian model. It does NOT propagate a
2D complex field or model diffraction/beam clipping/astigmatism/interference.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any

MAX_PROPAGATION_MM = 2500.0
MAX_EVENTS_PER_BRANCH = 36
MAX_BRANCHES = 128
MIN_POWER_MW = 1e-9
EPS = 1e-6


@dataclass(frozen=True)
class ABCD:
    """Paraxial ray matrix in air; B is mm and C is 1/mm.

    ``second @ first`` applies first, then second. Flat reflections use an
    unfolded local optical axis and therefore have the identity q matrix.
    """
    a: float = 1.
    b: float = 0.
    c: float = 0.
    d: float = 1.

    def __matmul__(self, other: 'ABCD') -> 'ABCD':
        return ABCD(self.a*other.a+self.b*other.c,
                    self.a*other.b+self.b*other.d,
                    self.c*other.a+self.d*other.c,
                    self.c*other.b+self.d*other.d)

    def apply_q(self, q: complex) -> complex:
        return (self.a*q+self.b)/(self.c*q+self.d)

    def inverse(self) -> 'ABCD':
        determinant=self.a*self.d-self.b*self.c
        if abs(determinant)<1e-15: raise ValueError('Singular ABCD matrix')
        return ABCD(self.d/determinant,-self.b/determinant,
                    -self.c/determinant,self.a/determinant)


def propagation_matrix(length_mm: float) -> ABCD:
    if not math.isfinite(length_mm) or length_mm < 0:
        raise ValueError('Propagation length must be finite and nonnegative')
    return ABCD(b=length_mm)


def lens_matrix(focal_mm: float) -> ABCD:
    if not math.isfinite(focal_mm) or abs(focal_mm) <= 1e-12:
        raise ValueError('Focal length must be finite and nonzero')
    return ABCD(c=-1/focal_mm)


def four_f_matrix(f1_mm: float, f2_mm: float) -> ABCD:
    """Object -> sample: P(f2) L(f2) P(f1+f2) L(f1) P(f1)."""
    if f1_mm <= 0 or f2_mm <= 0:
        raise ValueError('4f relay requires positive focal lengths')
    return (propagation_matrix(f2_mm) @ lens_matrix(f2_mm)
            @ propagation_matrix(f1_mm+f2_mm) @ lens_matrix(f1_mm)
            @ propagation_matrix(f1_mm))

@dataclass(frozen=True)
class Vec:
    x: float
    y: float
    def __add__(self, other: 'Vec') -> 'Vec': return Vec(self.x + other.x, self.y + other.y)
    def __sub__(self, other: 'Vec') -> 'Vec': return Vec(self.x - other.x, self.y - other.y)
    def __mul__(self, t: float) -> 'Vec': return Vec(self.x * t, self.y * t)
    __rmul__ = __mul__
    def dot(self, other: 'Vec') -> float: return self.x*other.x + self.y*other.y
    def cross(self, other: 'Vec') -> float: return self.x*other.y - self.y*other.x
    def unit(self) -> 'Vec':
        length = math.hypot(self.x, self.y)
        return Vec(self.x/length, self.y/length) if length else Vec(1, 0)


def normal(degrees: float) -> Vec:
    return Vec(math.cos(math.radians(degrees)), math.sin(math.radians(degrees)))


def tangent(n: Vec) -> Vec: return Vec(-n.y, n.x)


def clamp(x: float, low: float, high: float) -> float: return min(high, max(low, x))


def q_from_source(src: dict[str, Any]) -> complex:
    """q=z+i*zR. Positive waistOffsetMm: waist is ahead of the source."""
    lam_mm = float(src['lambdaNm']) * 1e-6
    waist_mm = float(src['waistMm'])
    if lam_mm <= 0 or waist_mm <= 0:
        raise ValueError('Laser wavelength and waist must be positive')
    return complex(-float(src.get('waistOffsetMm', 0)), math.pi*waist_mm**2/lam_mm)


def free_space(q: complex, length_mm: float) -> complex:
    """ABCD = [[1, L], [0, 1]], q' = q + L."""
    return propagation_matrix(length_mm).apply_q(q)


def thin_lens(q: complex, focal_mm: float) -> complex:
    """ABCD = [[1, 0], [-1/f, 1]], q' = q / (1-q/f)."""
    return lens_matrix(focal_mm).apply_q(q)


def beam_radius(q: complex, wavelength_nm: float) -> float:
    """1/e^2 intensity beam radius, mm."""
    if q.imag <= 0 or wavelength_nm <= 0:
        raise ValueError('Invalid Gaussian q or wavelength')
    return math.sqrt((wavelength_nm*1e-6)/math.pi * (abs(q)**2)/q.imag)


def waist_radius(q: complex, wavelength_nm: float) -> float:
    return math.sqrt((wavelength_nm*1e-6)*q.imag/math.pi)


def mirror_direction(d: Vec, n: Vec) -> Vec:
    return (d - n*(2*d.dot(n))).unit()


def lens_direction(d: Vec, n: Vec, off_axis_mm: float, focal_mm: float) -> tuple[Vec, float, float]:
    """Thin-lens paraxial angular kick to the CHIEF ray; not a full ray bundle.

    Off-axis distance is measured along the component tangent relative to
    its center. The local forward surface normal is chosen to face the ray.
    """
    forward = n if d.dot(n) >= 0 else n*(-1)
    t = tangent(forward)
    inc = math.atan2(d.dot(t), d.dot(forward))
    out = inc - off_axis_mm/focal_mm
    return (forward*math.cos(out) + t*math.sin(out)).unit(), inc, out


def intersection(point: Vec, direction: Vec, component: dict[str, Any]):
    n = normal(float(component.get('angle', 0)))
    t = tangent(n)
    delta = Vec(float(component['x']), float(component['y'])) - point
    den = direction.cross(t)
    if abs(den) <= 1e-10: return None
    distance = delta.cross(t)/den
    along = delta.cross(direction)/den
    radius = max(0.0, float(component.get('diameterMm', 25.4)) / 2)
    if distance <= EPS or abs(along) > radius + 1e-8: return None
    return distance, point + direction*distance, along, n


def table_exit_distance(p: Vec, d: Vec, width: float, height: float) -> float:
    candidates = []
    if d.x > 1e-12: candidates.append((width-p.x)/d.x)
    if d.x < -1e-12: candidates.append(-p.x/d.x)
    if d.y > 1e-12: candidates.append((height-p.y)/d.y)
    if d.y < -1e-12: candidates.append(-p.y/d.y)
    candidates = [v for v in candidates if v >= -1e-8]
    return max(0., min(candidates)) if candidates else 0.


@dataclass
class Segment:
    source_id: str
    branch_id: int
    start: Vec
    end: Vec
    direction: Vec
    length_mm: float
    path_start_mm: float
    path_end_mm: float
    q_start: complex
    q_end: complex
    wavelength_nm: float
    power_mw: float
    abcd_start: ABCD = field(default_factory=ABCD)
    abcd_end: ABCD = field(default_factory=ABCD)

@dataclass
class Marker:
    kind: str  # waist, limit
    point: Vec
    branch_id: int
    path_mm: float
    radius_mm: float = 0.

@dataclass
class ScreenReading:
    """Local Gaussian reading; screen_id also identifies sample/probe planes."""
    screen_id: str
    source_id: str
    branch_id: int
    point: Vec
    path_mm: float
    q: complex
    beam_radius_mm: float
    wavelength_nm: float
    power_mw: float
    incidence_deg: float
    cos_incidence: float
    offset_mm: float
    abcd: ABCD = field(default_factory=ABCD)
    @property
    def wavefront_radius_mm(self) -> float:
        return abs(self.q)**2/self.q.real if abs(self.q.real)>1e-12 else math.inf
    @property
    def waist_distance_mm(self) -> float:
        """Distance to Gaussian waist on the unfolded axis; negative means behind."""
        return -self.q.real
    @property
    def projected_radius_mm(self) -> float:
        return self.beam_radius_mm/max(1e-6, self.cos_incidence)
    @property
    def peak_irradiance_w_m2(self) -> float:
        # Flux on the tilted screen plane (ideal untruncated Gaussian).
        w_m = self.beam_radius_mm*1e-3
        return 2*(self.power_mw*1e-3)*self.cos_incidence/(math.pi*w_m*w_m)
    def relative_intensity(self, u_mm: float, v_mm: float = 0.) -> float:
        """u/v are screen-local displacements from screen center, not beam center."""
        w = self.beam_radius_mm
        return math.exp(-2*(((u_mm-self.offset_mm)*self.cos_incidence/w)**2 + (v_mm/w)**2))

@dataclass
class TraceResult:
    segments: list[Segment] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)
    screens: list[ScreenReading] = field(default_factory=list)
    hits: list[tuple[str, Vec, int]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    capped: int = 0
    exits: int = 0
    branches: int = 0
    samples: list[ScreenReading] = field(default_factory=list)
    probes: list[ScreenReading] = field(default_factory=list)
    branch_parents: dict[int, tuple[int, float]] = field(default_factory=dict)
    order_paths: list[dict[str,Any]] = field(default_factory=list)

    def branch_segments(self, branch_id: int) -> list[Segment]:
        """Include the shared source path before each splitter ancestor."""
        selected = []
        end_path = math.inf
        while True:
            selected.extend(s for s in self.segments if s.branch_id == branch_id
                            and s.path_end_mm <= end_path + EPS)
            if branch_id not in self.branch_parents:
                break
            branch_id, end_path = self.branch_parents[branch_id]
        return sorted(selected, key=lambda s: s.path_start_mm)


def simulate(scene: dict[str, Any]) -> TraceResult:
    """Trace until screen, table edge, power threshold, or 2500mm cap.

    Every split branch inherits its cumulative path length. In particular,
    mirror-to-mirror travel counts against the cap; it does not reset.
    """
    table = scene['table']
    width, height = float(table['widthMm']), float(table['heightMm'])
    components = [c for c in scene['components'] if c['type'] != 'laser']
    sources = [c for c in scene['components'] if c['type'] == 'laser']
    result = TraceResult()
    stack: list[dict[str, Any]] = []
    next_id = 0
    for src in sources:
        try:
            q = q_from_source(src)
            power = float(src.get('powerMw', 10))
            if power < 0: raise ValueError('Negative power')
        except (ValueError, TypeError, KeyError) as error:
            result.warnings.append(f"{src.get('id', 'laser')}: {error}")
            continue
        next_id += 1
        stack.append(dict(source_id=src['id'], wavelength_nm=float(src['lambdaNm']),
            point=Vec(float(src['x']),float(src['y'])),
            direction=normal(float(src.get('angle',0))), q=q, power_mw=power,
            path_mm=0., events=0, branch_id=next_id, abcd=ABCD()))
    visited = 0
    while stack:
        visited += 1
        if visited > MAX_BRANCHES:
            result.warnings.append('Branch limit (128) reached')
            break
        state = stack.pop()
        result.branches += 1
        while state['events'] < MAX_EVENTS_PER_BRANCH and state['power_mw'] >= MIN_POWER_MW:
            remaining = MAX_PROPAGATION_MM-state['path_mm']
            if remaining <= EPS:
                result.capped += 1
                result.markers.append(Marker('limit', state['point'], state['branch_id'], state['path_mm']))
                break
            exit_mm = table_exit_distance(state['point'],state['direction'],width,height)
            if exit_mm <= EPS:
                result.exits += 1
                break
            limit = min(remaining, exit_mm)
            nearest = None
            for c in components:
                found = intersection(state['point'], state['direction'], c)
                if found and found[0] <= limit and (nearest is None or found[0] < nearest[0][0]):
                    nearest = (found,c)
            distance = nearest[0][0] if nearest else limit
            end = state['point'] + state['direction']*distance
            q_end = free_space(state['q'], distance)
            abcd_end = propagation_matrix(distance) @ state['abcd']
            result.segments.append(Segment(state['source_id'],state['branch_id'],
                state['point'],end,state['direction'],distance,state['path_mm'],
                state['path_mm']+distance,state['q'],q_end,state['wavelength_nm'],state['power_mw'],
                state['abcd'],abcd_end))
            waist_at = -state['q'].real
            if 0 <= waist_at <= distance:
                result.markers.append(Marker('waist',state['point']+state['direction']*waist_at,
                    state['branch_id'],state['path_mm']+waist_at,
                    waist_radius(state['q'],state['wavelength_nm'])))
            state['point'],state['q'] = end,q_end
            state['abcd'] = abcd_end
            state['path_mm'] += distance
            if nearest is None:
                if remaining <= exit_mm + EPS:
                    result.capped += 1
                    result.markers.append(Marker('limit',end,state['branch_id'],state['path_mm']))
                else:
                    result.exits += 1
                break
            (_, _, along, n), c = nearest
            result.hits.append((c['id'],end,state['branch_id']))
            kind = c['type']
            if kind != 'probe': state['events'] += 1
            if kind=='slm':
                from slm import validate_slm
                settings=validate_slm(c)
                # Nominal (incoherent) reference only; the wave engine includes
                # interference with residual reflection and actual filtering.
                state['power_mw'] *= (settings['slmEfficiency']*settings['slmFillFactor']
                    +settings['slmDeadReflectivity']*(1-settings['slmFillFactor'])+settings['slmResidualPower'])
                state['direction']=mirror_direction(state['direction'],n)
                warning=f"{c['id']}: SLM phase/pixel modulation requires scalar wave mode; q is an unmodulated reference"
                if warning not in result.warnings:result.warnings.append(warning)
                continue
            if kind in ('screen', 'sample', 'probe','spatial_filter'):
                cosine = abs(state['direction'].dot(n))
                offset = (end - Vec(float(c['x']),float(c['y']))).dot(tangent(n))
                reading = ScreenReading(c['id'],state['source_id'],state['branch_id'],
                    end,state['path_mm'],state['q'],beam_radius(state['q'],state['wavelength_nm']),
                    state['wavelength_nm'],state['power_mw'],
                    math.degrees(math.acos(clamp(cosine,0.,1.))),cosine,offset,state['abcd'])
                if kind == 'screen':
                    result.screens.append(reading)
                    break
                if kind in ('probe','spatial_filter'):
                    result.probes.append(reading)
                    if kind=='spatial_filter':
                        warning='Spatial filter affects wave/order paths; Gaussian q trace is a reference axis'
                        if warning not in result.warnings:result.warnings.append(warning)
                    continue  # Virtual, non-intercepting diagnostic plane.
                result.samples.append(reading)  # Incident power, before reflection.
            if kind in ('mirror', 'sample'):
                state['direction'] = mirror_direction(state['direction'],n)
                state['power_mw'] *= clamp(float(c.get('reflectivity',1.)),0,1)
            elif kind == 'lens':
                f = float(c.get('focalMm',0))
                if abs(f) <= EPS:
                    result.warnings.append(f"{c['id']}: focal length must be nonzero")
                    break
                forward = n if state['direction'].dot(n) >= 0 else n*(-1)
                surface_offset = (end-Vec(float(c['x']),float(c['y']))).dot(tangent(forward))
                direction,theta_in,theta_out = lens_direction(state['direction'],n,surface_offset,f)
                if abs(theta_in) > math.radians(15) or abs(theta_out) > math.radians(30):
                    result.warnings.append(f"{c['id']}: large angle, paraxial approximation unreliable")
                state['direction'] = direction
                state['q'] = thin_lens(state['q'],f)
                state['abcd'] = lens_matrix(f) @ state['abcd']
            elif kind == 'splitter':
                reflectivity = clamp(float(c.get('reflectivity',0.5)),0,1)
                if state['power_mw']*reflectivity >= MIN_POWER_MW:
                    next_id += 1
                    branch = state.copy()
                    branch['branch_id'] = next_id
                    branch['direction'] = mirror_direction(state['direction'],n)
                    branch['power_mw'] = state['power_mw']*reflectivity
                    stack.append(branch)
                    result.branch_parents[next_id] = (state['branch_id'], state['path_mm'])
                state['power_mw'] *= (1-reflectivity)
            else:
                result.warnings.append(f"{c['id']}: unsupported type {kind}")
                break
        if state['events'] >= MAX_EVENTS_PER_BRANCH:
            result.warnings.append(f"branch {state['branch_id']}: interaction limit reached")
    if any(c['type']=='slm' for c in scene['components']):
        from slm_geometry import order_segments
        result.order_paths=order_segments(scene,result)
    return result


def default_scene() -> dict[str,Any]:
    return dict(schemaVersion=1,
        table=dict(widthMm=1200,heightMm=900,holeSpacingMm=25),
        components=[
            dict(id='laser-1',type='laser',x=125.,y=375.,angle=0.,lambdaNm=780.,waistMm=1.,waistOffsetMm=0.,powerMw=10.),
            dict(id='lens-1',type='lens',x=350.,y=375.,angle=0.,diameterMm=25.4,focalMm=200.),
            dict(id='mirror-1',type='mirror',x=650.,y=375.,angle=-45.,diameterMm=25.4,reflectivity=1.),
            dict(id='screen-1',type='screen',x=650.,y=725.,angle=90.,diameterMm=25.4),
        ])


def four_f_scene() -> dict[str, Any]:
    """720 nm, 200/100 mm reflection relay; object waist is x=250 mm.

    Probes are virtual measurements, not inserted screens. The sample is an
    ideal flat specular reflector (R=0.8), not a scattering/phase object.
    Input power is 10 mW; the ideal 50:50 splitter sends 5 mW to the sample
    and 2 mW of its return to the detector. All distances are in air.
    """
    return dict(schemaVersion=1,
        table=dict(widthMm=1200, heightMm=900, holeSpacingMm=25),
        components=[
            dict(id='laser-720', type='laser', x=100., y=450., angle=0.,
                 lambdaNm=720., waistMm=.5, waistOffsetMm=150., powerMw=10.),
            dict(id='splitter-1', type='splitter', x=350., y=450., angle=-45.,
                 diameterMm=25.4, reflectivity=.5),
            dict(id='object-plane', type='probe', x=250., y=450., angle=0., diameterMm=25.4),
            dict(id='lens-1', type='lens', x=450., y=450., angle=0.,
                 diameterMm=25.4, focalMm=200.),
            dict(id='fourier-plane', type='probe', x=650., y=450., angle=0., diameterMm=25.4),
            dict(id='lens-2', type='lens', x=750., y=450., angle=0.,
                 diameterMm=25.4, focalMm=100.),
            dict(id='sample-1', type='sample', x=850., y=450., angle=0.,
                 diameterMm=25.4, reflectivity=.8),
            dict(id='return-screen', type='screen', x=350., y=350., angle=90., diameterMm=25.4),
            dict(id='dump-screen', type='screen', x=350., y=700., angle=90., diameterMm=25.4),
        ])


def validate_scene(raw: Any) -> dict[str,Any]:
    """Minimal safe JSON validation; accepts the existing v0.2 file format."""
    if not isinstance(raw,dict) or not isinstance(raw.get('table'),dict) or not isinstance(raw.get('components'),list):
        raise ValueError('JSON must contain table and components')
    table = raw['table']
    width = float(table['widthMm']); height = float(table['heightMm'])
    if not (100 <= width <= 10000 and 100 <= height <= 10000):
        raise ValueError('Table dimensions must be 100..10000 mm')
    if len(raw['components']) > 200: raise ValueError('At most 200 components')
    ids = set()
    spacing = float(table.get('holeSpacingMm',25))
    if not math.isfinite(spacing) or spacing <= 0:
        raise ValueError('Hole spacing must be finite and positive')
    allowed = {'laser','lens','mirror','splitter','screen','sample','probe','slm','spatial_filter'}
    cleaned = []
    for c in raw['components']:
        if not isinstance(c,dict) or c.get('type') not in allowed: raise ValueError('Unknown component type')
        if not isinstance(c.get('id'),str) or not c['id'] or c['id'] in ids: raise ValueError('Invalid/duplicate component id')
        ids.add(c['id'])
        item = c.copy()
        for field_name in ['x','y','angle']:
            item[field_name] = float(c.get(field_name,0))
            if not math.isfinite(item[field_name]): raise ValueError('Nonfinite component coordinate')
        if not (0 <= item['x'] <= width and 0 <= item['y'] <= height):
            raise ValueError(f"{item['id']} is outside the table")
        for k in ['lambdaNm','waistMm','waistOffsetMm','powerMw','diameterMm','focalMm','reflectivity',
                  'phaseRad','periodMm','phaseDepthRad','responsivityAW']:
            if k in item:
                item[k] = float(item[k])
                if not math.isfinite(item[k]): raise ValueError('Nonfinite component parameter')
        if item['type']=='laser' and (item.get('lambdaNm',0)<=0 or item.get('waistMm',0)<=0 or item.get('powerMw',-1)<0):
            raise ValueError(f"{item['id']} has invalid laser parameters")
        if item['type']=='lens' and abs(item.get('focalMm',0)) < 1e-12:
            raise ValueError(f"{item['id']} has invalid focal length")
        if item.get('diameterMm',25.4) <= 0:
            raise ValueError(f"{item['id']} has invalid aperture")
        if item['type'] in ('mirror','splitter','sample') and not (0 <= item.get('reflectivity',1) <= 1):
            raise ValueError(f"{item['id']} has invalid reflectivity")
        if item.get('periodMm',0)<0 or item.get('responsivityAW',0)<0:
            raise ValueError('Period and responsivity must be nonnegative')
        if item['type']=='slm':
            from slm import validate_slm
            item=validate_slm(item)
        if item['type']=='spatial_filter':
            for key,default in [('filterOffsetMm',0.),('filterRadiusMm',.2),('fourierFocalMm',200.)]:
                item[key]=float(item.get(key,default))
                if not math.isfinite(item[key]):raise ValueError('Invalid spatial filter parameter')
            if item['filterRadiusMm']<=0 or item['fourierFocalMm']<=0:raise ValueError('Filter radius/focal length must be positive')
        cleaned.append(item)
    scene={'schemaVersion':1,'table':{'widthMm':width,'heightMm':height,
        'holeSpacingMm':spacing},'components':cleaned}
    if 'waveGrid' in raw:
        config=raw['waveGrid']
        if not isinstance(config,dict):raise ValueError('Saved wave grid must be an object')
        try:n=int(config['n']);fov=float(config['widthMm'])
        except (ValueError,TypeError,KeyError) as error:raise ValueError('Invalid saved wave grid') from error
        if n!=config['n'] or n%2 or not 32<=n<=2048 or not math.isfinite(fov) or fov<=0:
            raise ValueError('Invalid saved wave grid')
        scene['waveGrid']=dict(n=n,widthMm=fov)
    return scene


def slm_four_f_scene() -> dict[str,Any]:
    """5° LCOS, carrier-selected 4f illumination, independent sample pickoff.

    No beamsplitter is used to separate LCOS input/output. One 50:50 splitter
    near the sample collects its return into a separate 1:1 f=50 mm relay.
    Residual reflection is a declared engineering assumption, not catalog data.
    """
    from slm import slm_component
    scene=dict(schemaVersion=1,waveGrid=dict(n=2048,widthMm=6.),table=dict(widthMm=1200,heightMm=900,holeSpacingMm=25),components=[
        dict(id='laser-720',type='laser',x=700.,y=550.,angle=10.,lambdaNm=720.,waistMm=.5,waistOffsetMm=300.,powerMw=10.),
        slm_component(x=1000.,y=600.,slmPattern='flat',slmEfficiency=.8,
                      slmResidualPower=.01,slmCarrierPeriodMm=.128,
                      slmDesignIncidenceDeg=5.,slmIncidentSource='laser-720',slmSourceDistanceMm=300.,slmRelayAxisDeg=180.),
        dict(id='lens-1',type='lens',x=800.,y=600.,angle=0.,diameterMm=25.4,focalMm=200.),
        dict(id='fourier-plane',type='spatial_filter',x=600.,y=600.,angle=0.,diameterMm=25.4,
             filterRadiusMm=.2,filterOffsetMm=1.13,fourierFocalMm=200.,slmLinkedFilter='slm-1'),
        dict(id='lens-2',type='lens',x=500.,y=600.,angle=0.,diameterMm=25.4,focalMm=100.),
        dict(id='return-separator',type='splitter',x=450.,y=600.,angle=45.,diameterMm=25.4,reflectivity=.5,orderPickoff=True),
        dict(id='sample-1',type='sample',x=400.,y=600.,angle=0.,diameterMm=25.4,reflectivity=.8),
        dict(id='collection-lens',type='lens',x=450.,y=550.,angle=90.,diameterMm=25.4,focalMm=50.),
        dict(id='return-screen',type='screen',x=450.,y=450.,angle=90.,diameterMm=25.4),
        dict(id='illumination-dump',type='screen',x=450.,y=850.,angle=90.,diameterMm=25.4),
    ])
    from slm_geometry import configure_incidence
    configure_incidence(scene,scene['components'][1],5.)
    return scene
