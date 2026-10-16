"""Read-only native pad record comparison after connectivity reordering."""
from pathlib import Path
from collections import Counter
import json,sys
import olefile
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
sys.path.insert(0,str(ROOT/'script/_support/qd_center_revision'))
from native_metadata_helpers import pads_stream,properties


def keyed(path):
    with olefile.OleFileIO(path) as d:
        components=properties(d.openstream('Components6/Data').read())
        rows=pads_stream(d.openstream('Pads6/Data').read())
    result={}
    for row in rows:
        if row['component']==65535:
            key=('MOUNT',row['number'],*row['coords'][:2])
        else:
            c=components[row['component']]
            key=(c['SOURCEUNIQUEID'],row['number'])
        assert key not in result,key
        result[key]=row
    return result


def main():
    a=keyed(H/'before_alignment/QSTL_QD4_2SET_38PAD.PcbDoc')
    b=keyed(ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc')
    assert a.keys()==b.keys()
    diffs=[];counts=Counter()
    for key,old in a.items():
        new=b[key]
        for index,(x,y) in enumerate(zip(old['blocks'],new['blocks'])):
            assert len(x)==len(y),(key,index,len(x),len(y))
            offsets=[i for i,(u,v) in enumerate(zip(x,y)) if u!=v]
            if offsets:
                diffs.append(dict(key=key,block=index,offsets=offsets,old=[x[i] for i in offsets],new=[y[i] for i in offsets]))
                counts.update((index,i) for i in offsets)
    report=dict(pad_count=len(a),changed_blocks=diffs,offset_counts=[dict(block=k[0],offset=k[1],count=v) for k,v in sorted(counts.items())])
    (H/'pad_cache_identity_diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(pad_count=len(a),offset_counts=report['offset_counts']),indent=2))

if __name__=='__main__':main()
