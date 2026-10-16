"""Limit RF search to the local endpoint span to prevent full-board detours."""
from pathlib import Path

H=Path(__file__).resolve().parent
source=(H/'route_rf_ring_clear.py').read_text()
old="            costs[live_hard]=np.inf"
new="""            costs[live_hard]=np.inf
            # A four-millimetre end margin admits the neighboring component
            # escape while avoiding unrelated opposite-end board detours.
            lower=max(0,int((min(jobs[ix]['a'][1],jobs[ix]['b'][1])-4.)/GRID))
            upper=min(NY,int((max(jobs[ix]['a'][1],jobs[ix]['b'][1])+4.)/GRID)+1)
            costs[:lower,:]=np.inf
            costs[upper:,:]=np.inf"""
assert old in source
source=source.replace(old,new)
helper='''def strip_collinear(points):
    """Remove redundant lattice joins without changing the route centreline."""
    result=[]
    for point in points:
        point=list(point)
        if result and math.dist(result[-1],point)<1e-9:
            continue
        while len(result)>1:
            u=np.subtract(result[-1],result[-2]);v=np.subtract(point,result[-1])
            if abs(u[0]*v[1]-u[1]*v[0])<1e-9 and np.dot(u,v)>0:
                result.pop()
            else:
                break
        result.append(point)
    return result

'''
source=source.replace('def main():',helper+'def main():')
source=source.replace('points=shortcuts(points,live_forbidden,others)',
                      'points=strip_collinear(shortcuts(points,live_forbidden,others))')
(H/'route_rf_corridor_bounded.py').write_text(source)
print('Prepared local-span RF router.')
