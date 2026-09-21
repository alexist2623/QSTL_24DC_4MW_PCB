"""RF geometry preparation. Millimeters/degrees/picoseconds; no project writes.

No channel, frequency, velocity, fence pitch or impedance width is selected here.
All values affecting a design must be supplied by the caller.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Hashable, Sequence
import math
import struct

EPS = 1e-10
XY = tuple[float, float]

def add(a: XY, b: XY) -> XY: return a[0]+b[0], a[1]+b[1]
def sub(a: XY, b: XY) -> XY: return a[0]-b[0], a[1]-b[1]
def scale(a: XY, s: float) -> XY: return a[0]*s, a[1]*s
def left(a: XY) -> XY: return -a[1], a[0]
def norm(a: XY) -> float: return math.hypot(*a)
def unit(a: XY) -> XY:
    n=norm(a)
    if n<EPS: raise ValueError('Zero-length direction')
    return scale(a,1/n)

@dataclass(frozen=True)
class Line:
    start: XY
    end: XY
    layer: Hashable
    width: float
    net: str | None = None
    @property
    def length(self): return math.dist(self.start,self.end)
    def at(self, distance: float):
        if not -EPS<=distance<=self.length+EPS: raise ValueError('Distance outside line')
        u=unit(sub(self.end,self.start))
        return add(self.start,scale(u,distance)),u

@dataclass(frozen=True)
class Arc:
    center: XY
    radius: float
    start_deg: float
    sweep_deg: float  # signed: +CCW, -CW, in mathematical PCB XY
    layer: Hashable
    width: float
    net: str | None = None
    def __post_init__(self):
        if self.radius<=0 or self.width<=0 or not EPS<abs(self.sweep_deg)<=360+EPS:
            raise ValueError('Invalid radius, width or arc sweep')
    @property
    def length(self): return self.radius*math.radians(abs(self.sweep_deg))
    @property
    def start(self): return self.at(0)[0]
    @property
    def end(self): return self.at(self.length)[0]
    def at(self, distance: float):
        if not -EPS<=distance<=self.length+EPS: raise ValueError('Distance outside arc')
        direction=math.copysign(1,self.sweep_deg)
        a=math.radians(self.start_deg)+direction*distance/self.radius
        radial=(math.cos(a),math.sin(a))
        return add(self.center,scale(radial,self.radius)),scale(left(radial),direction)
    def native_angles(self):
        if abs(abs(self.sweep_deg)-360)<EPS: return 0.,360.
        if self.sweep_deg>0: return self.start_deg%360,(self.start_deg+self.sweep_deg)%360
        return (self.start_deg+self.sweep_deg)%360,self.start_deg%360

Primitive = Line | Arc

def path_length(path: Sequence[Primitive]) -> float:
    return math.fsum(p.length for p in path)

def primitive_to_altium_dict(p: Primitive):
    """Geometry for the prepared DelphiScript helper; no object is created here."""
    common={'net':p.net,'layer':p.layer,'width':p.width}
    if isinstance(p,Line):
        return dict(common,kind='track',x1=p.start[0],y1=p.start[1],x2=p.end[0],y2=p.end[1])
    a0,a1=p.native_angles()
    return dict(common,kind='arc',cx=p.center[0],cy=p.center[1],radius=p.radius,start_angle=a0,end_angle=a1,length_mm=p.length)

def validate_path(path: Sequence[Primitive], tolerance=1e-7, tangent_tolerance=1e-7):
    """Checks geometric continuity/tangency, not copper clearance or connectivity."""
    issues=[]
    for i,(a,b) in enumerate(zip(path,path[1:])):
        if math.dist(a.end,b.start)>tolerance: issues.append((i,'disconnected'))
        if math.dist(a.at(a.length)[1],b.at(0)[1])>tangent_tolerance: issues.append((i,'nontangent'))
    return issues

def fillet_polyline(points: Sequence[XY], radius: float | Sequence[float], *, layer,
                    width: float, net=None, shrink_to_fit=False) -> list[Primitive]:
    """Analytic tangent fillets. Rejects reversals and overlarge radii by default.

    A radius sequence has one entry per interior vertex. Optional proportional
    shrink only reduces radii when neighboring fillets consume an entire edge.
    It does not select a manufacturing/RF minimum bend radius.
    """
    points=[tuple(map(float,p)) for p in points]
    if len(points)<2 or width<=0: raise ValueError('Need >=2 points and positive width')
    vectors=[sub(b,a) for a,b in zip(points,points[1:])]
    lengths=[norm(v) for v in vectors]
    if min(lengths)<=EPS: raise ValueError('Repeated adjacent vertices')
    units=[scale(v,1/l) for v,l in zip(vectors,lengths)]
    radii=[float(radius)]*(len(points)-2) if isinstance(radius,(int,float)) else list(radius)
    if len(radii)!=len(points)-2 or any(r<=0 for r in radii): raise ValueError('Invalid radii')
    turns=[math.atan2(a[0]*b[1]-a[1]*b[0],a[0]*b[0]+a[1]*b[1]) for a,b in zip(units,units[1:])]
    if any(abs(abs(t)-math.pi)<1e-8 for t in turns): raise ValueError('Cannot fillet a180-degree reversal')
    setbacks=[r*math.tan(abs(t)/2) for r,t in zip(radii,turns)]
    for _ in range(len(points)+1):
        changed=False
        for edge,length in enumerate(lengths):
            ids=[i for i in [edge-1,edge] if 0<=i<len(setbacks)]
            total=sum(setbacks[i] for i in ids)
            if total>length+EPS:
                if not shrink_to_fit: raise ValueError(f'Fillets exceed edge{edge}')
                factor=length/total
                for i in ids: setbacks[i]*=factor;radii[i]*=factor
                changed=True
        if not changed: break
    result=[];cursor=points[0]
    for i,vertex in enumerate(points[1:-1]):
        if abs(turns[i])<EPS: continue
        incoming,outgoing=units[i],units[i+1]
        before=sub(vertex,scale(incoming,setbacks[i]));after=add(vertex,scale(outgoing,setbacks[i]))
        center=add(before,scale(left(incoming),math.copysign(radii[i],turns[i])))
        if math.dist(cursor,before)>EPS: result.append(Line(cursor,before,layer,width,net))
        radial=sub(before,center)
        result.append(Arc(center,radii[i],math.degrees(math.atan2(radial[1],radial[0])),math.degrees(turns[i]),layer,width,net))
        cursor=after
    if math.dist(cursor,points[-1])>EPS: result.append(Line(cursor,points[-1],layer,width,net))
    if validate_path(result): raise ArithmeticError('Fillet failed tangent-continuity validation')
    return result

@dataclass(frozen=True)
class VerticalMedium:
    z0: float
    z1: float
    velocity_mm_per_ps: float

@dataclass(frozen=True)
class ViaTraversal:
    from_layer: Hashable
    to_layer: Hashable
    name: str = ''

def via_delay(traversal: ViaTraversal, layer_z: dict, media: Sequence[VerticalMedium]):
    """Only traversed z interval, never unconditionally full through-hole height.

    Media must partition that interval without gaps/overlaps. This is a nominal
    delay integral; it does not model a via's EM discontinuity or unused stub.
    """
    lo,hi=sorted((layer_z[traversal.from_layer],layer_z[traversal.to_layer]))
    if hi-lo<EPS: return {'length_mm':0.,'delay_ps':0.,'slices':[]}
    intervals=[]
    for m in media:
        if m.z1<=m.z0 or m.velocity_mm_per_ps<=0: raise ValueError('Invalid vertical medium')
        a,b=max(lo,m.z0),min(hi,m.z1)
        if b>a+EPS: intervals.append((a,b,m.velocity_mm_per_ps))
    intervals.sort();cursor=lo;slices=[]
    for a,b,v in intervals:
        if abs(a-cursor)>EPS: raise ValueError('Missing/overlapping vertical delay medium')
        slices.append({'z0':a,'z1':b,'length_mm':b-a,'delay_ps':(b-a)/v});cursor=b
    if abs(cursor-hi)>EPS: raise ValueError('Uncovered vertical traversal')
    return {'length_mm':hi-lo,'delay_ps':math.fsum(s['delay_ps'] for s in slices),'slices':slices}

def delay_budget(path: Sequence[Primitive], planar_velocity: dict, vias: Sequence[ViaTraversal],
                 layer_z: dict, vertical_media: Sequence[VerticalMedium], *,
                 component_delays_ps: dict[str,float] | None=None):
    planar=[]
    for p in path:
        v=planar_velocity[p.layer]
        if v<=0: raise ValueError('Nonpositive layer velocity')
        planar.append({'kind':type(p).__name__,'layer':p.layer,'length_mm':p.length,'delay_ps':p.length/v})
    vertical=[dict(name=v.name,from_layer=v.from_layer,to_layer=v.to_layer,**via_delay(v,layer_z,vertical_media)) for v in vias]
    components=dict(component_delays_ps or {})
    if any(not math.isfinite(v) for v in components.values()): raise ValueError('Invalid component delay')
    return {'planar':planar,'vertical':vertical,'component_delays_ps':components,
            'total_delay_ps':math.fsum(x['delay_ps'] for x in planar+vertical)+math.fsum(components.values()),
            'model':'Caller supplied velocities/components; excludes unmodeled discontinuities and tolerances.'}

def sample_path(path: Sequence[Primitive], pitch: float):
    if pitch<=0: raise ValueError('Pitch must be positive')
    total=path_length(path)
    distances=[min(i*pitch,total) for i in range(math.floor(total/pitch)+1)]
    if not distances or total-distances[-1]>EPS: distances.append(total)
    result=[];i=0;base=0.
    for s in distances:
        while i<len(path)-1 and s>base+path[i].length+EPS: base+=path[i].length;i+=1
        xy,tangent=path[i].at(min(path[i].length,max(0.,s-base)))
        result.append((s,xy,tangent))
    return result

def copper_geometry(p: Primitive, sagitta_mm: float):
    """Conservative Shapely copper envelope for clearance filtering.

    Arc chord approximation is inflated by its maximum sagitta; this avoids an
    optimistic under-estimate at the outer arc boundary.
    """
    from shapely.geometry import LineString
    if sagitta_mm<=0: raise ValueError('Positive sagitta required')
    if isinstance(p,Line): return LineString([p.start,p.end]).buffer((p.width/2)/math.cos(math.pi/64),quad_segs=16)
    max_angle=2*math.acos(max(-1.,1-min(sagitta_mm,p.radius)/p.radius))
    n=max(1,math.ceil(math.radians(abs(p.sweep_deg))/max_angle))
    coords=[p.at(p.length*i/n)[0] for i in range(n+1)]
    return LineString(coords).buffer((p.width/2+sagitta_mm)/math.cos(math.pi/64),quad_segs=16)

@dataclass(frozen=True)
class CopperObstacle:
    name: str
    geometry: object  # Shapely polygon describing actual/conservative copper
    net: str | None

@dataclass(frozen=True)
class DrillHole:
    name: str
    center: XY
    diameter: float

def shield_fence(path: Sequence[Primitive], *, pitch: float, center_offset: float,
                  via_diameter: float, via_hole: float, ground_net: str,
                  copper: Sequence[CopperObstacle], holes: Sequence[DrillHole],
                  board_polygon, copper_clearance: float, hole_clearance: float,
                  edge_clearance: float, minimum_via_center_spacing: float,
                  ground_regions: Sequence[object], keepouts: Sequence[object]=()):
    """Returns candidates accepted on both path sides plus rejected/gap report.

    Through-via candidates are tested against copper from EVERY traversed layer,
    all drill holes, board edge, optional body keepouts and all supplied connected
    ground regions. Caller supplies region intersections for intended GND planes.
    Neither legal pitch nor frequency adequacy is inferred. Rejected candidates
    can leave gaps; gap reporting must be reviewed before calling this a shield.
    """
    from shapely.geometry import Point
    if not path or via_diameter<=via_hole or via_hole<=0 or center_offset<=0: raise ValueError('Invalid fence parameters')
    if not ground_regions: raise ValueError('Supply connected ground-region geometry')
    if min(copper_clearance,hole_clearance,edge_clearance,minimum_via_center_spacing)<0: raise ValueError('Negative clearance')
    accepted=[];rejected=[];rad=via_diameter/2
    for s,xy,tangent in sample_path(path,pitch):
        for side in [-1,1]:
            c=add(xy,scale(left(tangent),side*center_offset));pt=Point(c);why=[]
            if not board_polygon.contains(pt) or pt.distance(board_polygon.boundary)<rad+edge_clearance-EPS: why.append('board_edge')
            for ob in copper:
                if ob.net!=ground_net and pt.distance(ob.geometry)<rad+copper_clearance-EPS: why.append('copper:'+ob.name)
            for h in holes:
                if math.dist(c,h.center)<(via_hole+h.diameter)/2+hole_clearance-EPS: why.append('hole:'+h.name)
            for k in keepouts:
                if pt.distance(k)<rad+copper_clearance-EPS: why.append('keepout')
            if any(not g.buffer(-rad).covers(pt) for g in ground_regions): why.append('ground_coverage')
            for v in accepted:
                if math.dist(c,(v['x'],v['y']))<max(minimum_via_center_spacing,via_hole+hole_clearance)-EPS: why.append('fence_spacing')
            rec={'x':c[0],'y':c[1],'diameter':via_diameter,'hole':via_hole,'net':ground_net,'side':side,'path_s_mm':s}
            if why: rejected.append(dict(rec,reasons=sorted(set(why))))
            else: accepted.append(rec)
    total=path_length(path);gaps={}
    for side in [-1,1]:
        ss=sorted(v['path_s_mm'] for v in accepted if v['side']==side)
        spans=[{'from_s_mm':a,'to_s_mm':b,'gap_mm':b-a} for a,b in zip([0.]+ss,ss+[total])]
        gaps[str(side)]={'max_path_station_gap_mm':max((v['gap_mm'] for v in spans),default=total),'spans_exceeding_requested_pitch':[x for x in spans if x['gap_mm']>pitch+EPS]}
    return {'accepted':accepted,'rejected':rejected,'gaps':gaps,'requested_pitch_mm':pitch,'frequency_adequacy':'not evaluated'}

def decode_arcs6(data: bytes):
    """Read native Altium Arc6 records; never writes a project or changes bytes.

    Offsets inside record body: layer0, netu16@3, centerx/y/radius int32@13,
    start/end double@25/33, line width int32@41; native unit=2.54e-6mm.
    """
    pos=0;out=[]
    while pos<len(data):
        if len(data)-pos<5 or data[pos]!=1: raise ValueError('Invalid Arc6 header')
        count=struct.unpack_from('<I',data,pos+1)[0]&0xffffff
        if count<45 or pos+5+count>len(data): raise ValueError('Truncated Arc6 record')
        b=data[pos+5:pos+5+count]
        x,y,r=[n*2.54e-6 for n in struct.unpack_from('<3i',b,13)];a0,a1=struct.unpack_from('<2d',b,25)
        sweep=(a1-a0)%360
        if abs(sweep)<EPS: sweep=360.
        arc=Arc((x,y),r,a0,sweep,b[0],struct.unpack_from('<i',b,41)[0]*2.54e-6)
        out.append({'arc':arc,'net_index':struct.unpack_from('<H',b,3)[0],'record_offset':pos,'body_size':count})
        pos+=5+count
    return out

def arc_matches_native(planned: Arc, native: Arc, *, tolerance_mm: float, angle_tolerance_deg: float):
    if planned.layer!=native.layer: return False
    if abs(planned.radius-native.radius)>tolerance_mm or abs(planned.width-native.width)>tolerance_mm: return False
    if math.dist(planned.center,native.center)>tolerance_mm: return False
    a,b=planned.native_angles();c,d=native.native_angles()
    delta=lambda x,y:abs((x-y+180)%360-180)
    return delta(a,c)<=angle_tolerance_deg and delta(b,d)<=angle_tolerance_deg and abs(abs(planned.sweep_deg)-abs(native.sweep_deg))<=angle_tolerance_deg

def validate_native_arc_set(planned: Sequence[Arc], records: Sequence[dict], net_indices: dict,
                            *, tolerance_mm: float, angle_tolerance_deg: float):
    """One-to-one readback match on specified RF nets, copper layers1..32 only.

    Checks native net index, copper layer, center/radius/width, start/end/sweep;
    reports missing AND extra records, including duplicate arcs. Net indices must
    be read from the same saved PCB as the Arc6 stream, not a stale PCB copy.
    """
    ids=set(net_indices.values())
    actual=[(i,r) for i,r in enumerate(records) if r['net_index'] in ids and 1<=r['arc'].layer<=32]
    unmatched=set(range(len(actual)));missing=[]
    for i,p in enumerate(planned):
        ni=net_indices[p.net]
        candidates=[j for j in unmatched if actual[j][1]['net_index']==ni and arc_matches_native(p,actual[j][1]['arc'],tolerance_mm=tolerance_mm,angle_tolerance_deg=angle_tolerance_deg)]
        if candidates:unmatched.remove(candidates[0])
        else:missing.append(i)
    return {'matched':not missing and not unmatched,'missing_plan_indices':missing,'unexpected_native_record_indices':[actual[j][0] for j in sorted(unmatched)]}

def symmetric_stripline_impedance(width_mm: float, *, plane_spacing_mm: float,
                                 copper_thickness_mm: float, dk: float):
    """Approximate IPC-style Eq7 in Analog Devices MT-094, NOT a field solver.

    B=full separation of reference-plane inner faces=2H+T for centered stripline.
    No coplanar copper, offsets, roughness, dispersion or via models included.
    MT-094 reports typical formula accuracy on the order of6%, not a guarantee.
    """
    if min(width_mm,plane_spacing_mm,copper_thickness_mm,dk)<=0: raise ValueError('Positive dimensions/Dk required')
    if copper_thickness_mm>=plane_spacing_mm: raise ValueError('Copper exceeds plane spacing')
    ratio=1.9*plane_spacing_mm/(.8*width_mm+copper_thickness_mm)
    if ratio<=1: raise ValueError('Outside useful approximation domain')
    return 60/math.sqrt(dk)*math.log(ratio)

def approximate_stripline_width(target_ohms: float, *, plane_spacing_mm: float,
                                copper_thickness_mm: float, dk: float):
    if target_ohms<=0 or min(plane_spacing_mm,copper_thickness_mm,dk)<=0: raise ValueError('Positive inputs required')
    w=(1.9*plane_spacing_mm*math.exp(-target_ohms*math.sqrt(dk)/60)-copper_thickness_mm)/.8
    if w<=0: raise ValueError('No positive width in approximate model')
    symmetric_stripline_impedance(w,plane_spacing_mm=plane_spacing_mm,copper_thickness_mm=copper_thickness_mm,dk=dk)
    return {'width_mm':w,'target_ohms':target_ohms,'plane_spacing_mm':plane_spacing_mm,'copper_thickness_mm':copper_thickness_mm,'dk':dk,'model':'MT-094 Eq7 approximate centered stripline; not an EM/fabrication guarantee','source':'https://www.analog.com/media/en/training-seminars/tutorials/MT-094.pdf'}
