"""Inspect ancillary serialization changes after native model replacement."""
from pathlib import Path
import sys,json,struct,collections
import olefile
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/_support/qd_center_revision'))
from native_metadata_helpers import binary_records,properties
with olefile.OleFileIO(H/'baseline'/(P.name+'.PcbDoc')) as a,olefile.OleFileIO(P/(P.name+'.PcbDoc')) as b:
    out={}
    for stream in ('ShapeBasedComponentBodies6/Data',):
        aa=binary_records(a.openstream(stream).read(),12);bb=binary_records(b.openstream(stream).read(),12)
        def body_map(records):
            result={}
            for r in records:
                raw=r['body'];component=struct.unpack_from('<H',raw,7)[0];marker=raw.index(b'V7_LAYER=');length=struct.unpack_from('<I',raw,marker-4)[0]&0xffffff
                fields=dict(x.split('=',1) for x in raw[marker:marker+length].rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
                result[component]=(fields,raw[:marker-4],raw[marker+length:])
            return result
        am=body_map(aa);bm=body_map(bb)
        out[stream]=dict(counts=[len(aa),len(bb)],same_keys=am.keys()==bm.keys(),changes=[dict(component=k,fields={field:[am[k][0].get(field),bm[k][0].get(field)] for field in am[k][0].keys()|bm[k][0].keys() if am[k][0].get(field)!=bm[k][0].get(field)},prefix_equal=am[k][1]==bm[k][1],tail_equal=am[k][2]==bm[k][2]) for k in am if am[k]!=bm[k]])
    for stream in ('Board6/Data',):
        aa=properties(a.openstream(stream).read());bb=properties(b.openstream(stream).read())
        out[stream]=dict(counts=[len(aa),len(bb)],changes=[dict(index=i,changes={k:[x.get(k),y.get(k)] for k in x.keys()|y.keys() if x.get(k)!=y.get(k)}) for i,(x,y) in enumerate(zip(aa,bb)) if x!=y])
    def texts(blob):
        off=0;out={}
        while off<len(blob):
            assert blob[off]==5;n=struct.unpack_from('<I',blob,off+1)[0]&0xffffff;raw=blob[off+5:off+5+n];off+=5+n
            n=struct.unpack_from('<I',blob,off)[0]&0xffffff;t=blob[off+4:off+4+n];off+=4+n
            key=(struct.unpack_from('<H',raw,7)[0],t.hex());assert key not in out;out[key]=raw
        return out
    aa=texts(a.openstream('Texts6/Data').read());bb=texts(b.openstream('Texts6/Data').read())
    out['Texts6/Data']=dict(same_keys=aa.keys()==bb.keys(),changes=[dict(component=k[0],text=bytes.fromhex(k[1])[1:].decode('cp1252'),offsets=[i for i,(x,y) in enumerate(zip(v,bb[k])) if x!=y],before_len=len(v),after_len=len(bb[k])) for k,v in aa.items() if v!=bb.get(k)])
    samplekey=next(iter(aa));out['text_sample_hex']={label:{'60:110':v[60:110].hex(),'173:225':v[173:225].hex()} for label,v in [('before',aa[samplekey]),('after',bb[samplekey])]}
(H/'serialization.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k!='Texts6/Data'},indent=2))
print('TEXT_CHANGE_COUNT',len(out['Texts6/Data']['changes']))
print('TEXT_CHANGED_OFFSETS',sorted({i for r in out['Texts6/Data']['changes'] for i in r['offsets']}))
