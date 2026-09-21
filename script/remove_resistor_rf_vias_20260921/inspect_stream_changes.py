"""Inspect saved serialization changes before accepting unchanged geometry."""
from pathlib import Path
import sys,struct,collections,json
H=Path(__file__).resolve().parent;W=H.parent/'_support';P=H.parents[1]/'QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic')]
from build_routed_copy import snapshot
from native_metadata_helpers import binary_records
old=snapshot(H/'before.PcbDoc');new=snapshot(P/'QSTL_24DC_4MW_PCB.PcbDoc')
for stream in ('Tracks6/Data','Texts6/Data'):
    a,b=old[stream],new[stream];diff=[(i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y];print(stream,'lengths',len(a),len(b),'changed_bytes',len(diff),'first',diff[:50])
    if stream.startswith('Tracks'):
        aa=binary_records(a,4);bb=binary_records(b,4);print('Track record multiset equal:',collections.Counter(x['body'] for x in aa)==collections.Counter(x['body'] for x in bb))
    else:
        def records(buf):
            rows=[];pos=0
            while pos<len(buf):
                assert buf[pos]==5;size=struct.unpack_from('<I',buf,pos+1)[0]&0xffffff;body=buf[pos+5:pos+5+size];pos+=5+size
                length=struct.unpack_from('<I',buf,pos)[0]&0xffffff;txt=buf[pos+4:pos+4+length];pos+=4+length;rows.append((body,txt))
            assert pos==len(buf);return rows
        aa,bb=records(a),records(b);print('Text counts',len(aa),len(bb));changed=collections.Counter();details=[]
        for (ar,at),(br,bt) in zip(aa,bb):
            assert len(ar)==len(br) and at==bt
            changed.update(i for i,(x,y) in enumerate(zip(ar,br)) if x!=y)
            d=[(i,x,y) for i,(x,y) in enumerate(zip(ar,br)) if x!=y]
            details.append(dict(text=at.hex(),length=len(ar),changes=d))
        print('Changed text body offsets',sorted(changed));(H/'serialization_changes.json').write_text(json.dumps(dict(track_record_multiset_equal=collections.Counter(x['body'] for x in binary_records(old['Tracks6/Data'],4))==collections.Counter(x['body'] for x in binary_records(new['Tracks6/Data'],4)),text_differences=details),indent=2))
print('First text font data',repr(aa[0][0][35:125]),repr(aa[0][0][145:235]))
