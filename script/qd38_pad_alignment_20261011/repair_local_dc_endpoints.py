"""Repair only direct-QD DC endpoint approaches in an offline candidate.

The guarded placement input has common pad ends and jointly validated vias.
All schematic assignments and each net's internal routing layer are retained.
No native document or prior completion evidence is edited.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import copy
import hashlib
import json
import math
import sys

from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

H = Path(__file__).resolve().parent
ROT = H.parent/'qd38_rotation_20261011'
sys.path.insert(0, str(ROT))
sys.path.insert(0, str(H.parent/'qd38_carrier_20261010'))
from route_circuit import pgeom
from audit_candidate import audit
from route_rf_rotated import arc_line
from local_dc_endpoint_templates import cut_prefix, clean, legal_shape, unit, endpoint_templates

BASE_SHA = '835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495'
PLACEMENT_SHA = '89829a12e11b6dc548c045df0735d62824996275f4f32d5fe4379d4804b3273c'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
WIDTH = .125
GUARD = .000005


def track(net, layer, a, b):
    return dict(net=net, layer=layer, width=WIDTH, a=list(a), b=list(b))


def line_geometry(points):
    return LineString(points)


def assemble_placement(source, proposal):
    p = copy.deepcopy(source)
    old = {x['pin']: x for x in source['physical_pads'] if x['ref']=='Q1'}
    new = {x['pin']: x for x in proposal['qd_pads']}
    assert old.keys()==new.keys() and len(new)==38
    for key in old:
        for attr in ('net','sx','sy','rotation','shape','layer','hole'):
            assert old[key][attr]==new[key][attr], (key,attr)
    p['physical_pads'] = [copy.deepcopy(new[x['pin']]) if x['ref']=='Q1' else x for x in p['physical_pads']]
    for pad in p['pads']:
        pin=str(pad['number']);dx=new[pin]['x']-old[pin]['x'];dy=new[pin]['y']-old[pin]['y']
        for key in ('inner','center','bond'):
            pad[key]=[pad[key][0]+dx,pad[key][1]+dy]
        pad['polygon']=[[x+dx,y+dy] for x,y in pad['polygon']]
        pad['common_inner_boundary_aligned']=True
    vv={v['label']:v for v in proposal['qd_vias']}
    assert len(vv)==22 and all(k.startswith('Q1-') for k in vv)
    p['vias']=[copy.deepcopy(vv[v['label']]) if v['label'] in vv else v for v in p['vias']]
    for v in p['vias']:
        if not v['label'].startswith('Q1-'):continue
        assert abs(v['diameter']-.35)<1e-12 and abs(v['hole']-.20)<1e-12
        q=v['label'].split('-')[1]
        p['dc_endpoints'][q].update(x=v['x'],y=v['y'])
    # RF terminal requests follow their pads. Existing RF copper stays intact.
    for job in p['route_jobs']:
        if job['kind']=='RF_QD':
            q=str(int(job['net'][2:]));op,np=old[q],new[q]
            for key in ('a','b'):
                if math.dist(job[key],(op['x'],op['y']))<1e-5:
                    job[key]=[np['x'],np['y']]
    for row in p.get('rf_routed_jobs',[]):
        job=row.get('job',{})
        if job.get('kind')=='RF_QD':
            q=str(int(job['net'][2:]));op,np=old[q],new[q]
            for key in ('a','b'):
                if key in job and math.dist(job[key],(op['x'],op['y']))<1e-5:
                    job[key]=[np['x'],np['y']]
            row['terminal_pad_moved_existing_copper_retained']=True
    return p


def layer_blockers(p, frozen_tracks, net, layer):
    """Forbidden centreline areas, including true whole-body envelopes."""
    blocks=[]
    def add(g, other, extra=0.):
        if other==net:return
        gap=.2 if other=='GND' else (.10 if (other or '').startswith('DC') else .15)
        blocks.append(g.buffer(WIDTH/2+gap+GUARD+extra,quad_segs=32))
    for pad in p['physical_pads']:
        if pad['layer'] in (layer,74):add(pgeom(pad),pad['net'])
    for v in p['vias']:
        if v['low']<=layer<=v['high']:
            add(Point(v['x'],v['y']),v['net'],v['diameter']/2)
    for t in frozen_tracks:
        if t['layer']==layer:add(LineString([t['a'],t['b']]),t['net'],t['width']/2)
    for a in p['arcs']:
        if a['layer']==layer:add(arc_line(a),a['net'],a['width']/2+.000001)
    groups=defaultdict(list)
    for pad in p['physical_pads']:
        ref=pad['ref'] or ''
        if ref.startswith('SMP') or (ref.startswith('R') and ref[1:].isdigit()):groups[ref].append(pad)
    for ref,pads in groups.items():
        hull=unary_union([pgeom(x) for x in pads]).convex_hull
        own=unary_union([pgeom(x) for x in pads if ref.startswith('R') and x['pin']=='2' and x['net']==net])
        blocks.append(hull.difference(own).buffer(WIDTH/2+.15+GUARD,quad_segs=32))
    cx,cy=p['sample_center'];cw,ch=p['cavity_mm']
    blocks.append(box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2).buffer(WIDTH/2+GUARD))
    allowed=Polygon(p['board_outline']).buffer(-WIDTH/2-GUARD)
    return STRtree(blocks),blocks,allowed


def clear_path(points, obstacles):
    tree,blocks,allowed=obstacles;g=LineString(points)
    if not allowed.covers(g):return False
    return not any(g.intersects(blocks[int(i)]) for i in tree.query(g))


def prepare_tails(source, p, prefix_length):
    oldvias={v['net']:v for v in source['vias'] if v['label'].startswith('Q1-')}
    newvias={v['net']:v for v in p['vias'] if v['label'].startswith('Q1-')}
    tails={}
    for row in source['dc_routed_jobs']:
        net=row['job']['net']
        if net not in oldvias:continue
        v=oldvias[net];points=[tuple(x) for x in row['points']]
        if math.dist(points[-1],(v['x'],v['y']))<1e-5:points.reverse()
        assert math.dist(points[0],(v['x'],v['y']))<1e-5,net
        prefix,suffix=cut_prefix(points,prefix_length)
        layer=row['job']['layer'];nv=newvias[net]
        tails[net]=dict(old_prefix=prefix,suffix=suffix,layer=layer,new_start=(nv['x'],nv['y']),job=copy.deepcopy(row['job']))
    assert len(tails)==22
    frozen=[t for t in source['tracks'] if not(t['net'] in tails and t['layer'] in (2,4))]
    for net,d in tails.items():
        frozen.extend(track(net,d['layer'],a,b) for a,b in zip(d['suffix'],d['suffix'][1:]))
    return tails,frozen


def solve_templates(p, source, prefix_length=2.):
    tails,frozen=prepare_tails(source,p,prefix_length)
    options={};summary={}
    for net,d in tails.items():
        outgoing=unit(d['suffix'][0],d['suffix'][1]);start=d['new_start'];anchor=d['suffix'][0]
        obs=layer_blockers(p,frozen,net,d['layer'])
        oldtrial=[start]+d['old_prefix'][1:]
        choices=[]
        if legal_shape(oldtrial,outgoing):choices.append(oldtrial)
        choices+=endpoint_templates(start,anchor,outgoing,max_local_length_mm=prefix_length+1.0)
        passing=[];seen=set()
        for points in choices:
            pp=clean(points);key=tuple((round(x,8),round(y,8)) for x,y in pp)
            if key in seen:continue
            seen.add(key)
            if clear_path(pp,obs):
                length=sum(math.dist(a,b) for a,b in zip(pp,pp[1:]))
                unchanged=len(pp)==len(d['old_prefix']) and all(math.dist(a,b)<1e-8 for a,b in zip(pp,d['old_prefix']))
                passing.append(dict(points=pp,geometry=LineString(pp),rank=(0 if unchanged else 1,len(pp),length)))
        passing.sort(key=lambda x:x['rank']);options[net]=passing
        summary[net]=dict(options=len(passing),layer=d['layer'],moved_endpoint_mm=math.dist(start,d['old_prefix'][0]))
        print(net,'options',len(passing),'moved',round(summary[net]['moved_endpoint_mm'],6),flush=True)
    if any(not v for v in options.values()):return None,dict(passed=False,reason='no_local_template',options=summary,prefix_length_mm=prefix_length)
    chosen={};nodes=0
    def visit():
        nonlocal nodes
        nodes+=1
        if len(chosen)==len(options):return True
        possibilities={}
        for net,rows in options.items():
            if net in chosen:continue
            valid=[row for row in rows if all(tails[net]['layer']!=tails[other]['layer'] or row['geometry'].distance(option['geometry'])>=WIDTH+.10+GUARD for other,option in chosen.items())]
            if not valid:return False
            possibilities[net]=valid
        net=min(possibilities,key=lambda n:(len(possibilities[n]),n))
        for row in possibilities[net]:
            chosen[net]=row
            if visit():return True
            del chosen[net]
        return False
    if not visit():return None,dict(passed=False,reason='joint_local_conflict',options=summary,nodes=nodes,prefix_length_mm=prefix_length)
    result=copy.deepcopy(p);result['tracks']=list(frozen);changes=[]
    newjobs=[]
    for row in source['dc_routed_jobs']:
        net=row['job']['net']
        if net not in tails:newjobs.append(copy.deepcopy(row));continue
        d=tails[net];prefix=chosen[net]['points'];joined=clean(prefix+d['suffix'][1:]);job=copy.deepcopy(row['job'])
        oldv=d['old_prefix'][0]
        for key in ('a','b'):
            if math.dist(job[key],oldv)<1e-5:job[key]=list(d['new_start'])
        newjobs.append(dict(job=job,points=[list(pt) for pt in joined]))
        result['tracks'].extend(track(net,d['layer'],a,b) for a,b in zip(prefix,prefix[1:]))
        changes.append(dict(net=net,layer=d['layer'],before_prefix=d['old_prefix'],after_prefix=prefix,unchanged_anchor=d['suffix'][0],changed=chosen[net]['rank'][0]!=0,moved_endpoint_mm=math.dist(d['new_start'],oldv)))
    result['dc_routed_jobs']=newjobs
    for job in result['route_jobs']:
        if job['kind']=='DC' and job['net'] in tails:
            d=tails[job['net']]
            for key in ('a','b'):
                if math.dist(job[key],d['old_prefix'][0])<1e-5:job[key]=list(d['new_start'])
    # A split at an artificial anchor is geometrically harmless; remove only
    # same-net collinear joins by rebuilding these already audited polylines.
    result['tracks']=[t for t in result['tracks'] if not(t['net'] in tails and t['layer'] in (2,4))]
    for row in newjobs:
        if row['job']['net'] in tails:
            result['tracks'].extend(track(row['job']['net'],row['job']['layer'],a,b) for a,b in zip(row['points'],row['points'][1:]))
    return result,dict(passed=True,scope='Local routing template selection; full merged audit follows',options=summary,nodes=nodes,prefix_length_mm=prefix_length,changes=changes)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--placement',type=Path,default=H/'aligned_qd_vias_land_0p35_candidate.json')
    ap.add_argument('--prefix',type=float,default=2.)
    args=ap.parse_args();source_path=H/'before_alignment/full_copper_candidate.json'
    assert sha(source_path)==BASE_SHA and sha(args.placement)==PLACEMENT_SHA
    source=json.loads(source_path.read_text());proposal=json.loads(args.placement.read_text())
    assert proposal['all_static_checks_passed'] and proposal['joint_solution_found']
    p=assemble_placement(source,proposal)
    repaired,report=solve_templates(p,source,args.prefix)
    (H/'local_dc_template_report.json').write_text(json.dumps(report,indent=2)+'\n')
    if repaired is None:raise SystemExit(2)
    repaired['status']='QD_PAD_ALIGNMENT_LOCAL_SIGNAL_ROUTING_CANDIDATE_SURFACES_PENDING'
    repaired['surface_validation']={'passed':False,'status':'Previous surfaces retained as baseline; recompute/revalidate after local signal repair'}
    repaired['qd_pad_alignment_revision']=dict(source_candidate_sha256=BASE_SHA,placement_file=str(args.placement),placement_sha256=PLACEMENT_SHA,local_routing=report,ground_and_mask_revalidation_pending=True)
    repaired['dc_routing_validation']={'passed':False,'status':'New full merged signal audit pending'}
    output=H/'alignment_routed_candidate.json'
    output.write_text(json.dumps(repaired,indent=2)+'\n')
    validation=audit(repaired)
    repaired['dc_routing_validation']={'passed':validation['passed'],'minimum_internal_DC_pair_gap_mm':validation['minimum_internal_DC_pair_gap_mm'],'disconnected_net_count':len(validation['disconnected_nets']),'invalid_turn_count':len(validation['invalid_turns']),'scope':'Full merged signal audit; unchanged surfaces remain pending'}
    output.write_text(json.dumps(repaired,indent=2)+'\n')
    validation.update(candidate_sha256=sha(output),source_candidate_sha256=BASE_SHA,placement_sha256=PLACEMENT_SHA,scope='Full merged signal copper/connectivity/shape and R/SMP envelopes. Explicit GND regions/masks/shields are separately pending.')
    (H/'alignment_signal_audit.json').write_text(json.dumps(validation,indent=2)+'\n')
    print('AUDIT',validation['passed'],'failures',len(validation['failures']),json.dumps(validation['failures'][:12]),flush=True)
    raise SystemExit(0 if validation['passed'] else 3)


if __name__=='__main__':main()
