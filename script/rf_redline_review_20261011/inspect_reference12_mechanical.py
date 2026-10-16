"""Read-only metadata inspection of the reference carrier mechanical files."""
from pathlib import Path
import hashlib
import json
import re
import struct
import olefile

SOURCE=Path('F:/Nextcloud/Lab/Instruments/CustomParts/Carrier_12MW_72DC/Mechanical')


def main():
    for path in sorted(SOURCE.iterdir()):
        if not path.is_file():continue
        raw=path.read_bytes()
        result=dict(name=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),header_hex=raw[:24].hex())
        if olefile.isOleFile(path):
            with olefile.OleFileIO(path) as ole:
                result['streams']=['/'.join(p) for p in ole.listdir()]
                hits=[]
                for stream in ole.listdir():
                    blob=ole.openstream(stream).read()
                    strings=re.findall(rb'[ -~]{4,}',blob)
                    decoded=[s.decode('ascii') for s in strings]
                    decoded += re.findall(r'[ -~]{4,}',blob.decode('utf-16le',errors='ignore'))
                    for text in decoded:
                        if re.search(r'\bM[234](?:[.,]5)?\b|hole|thread|tap|mount',text,re.I):
                            hits.append(dict(stream='/'.join(stream),text=text[:300]))
                result['possible_feature_names']=hits[:80]
        if path.suffix.lower()=='.stl' and len(raw)>84:
            count=struct.unpack_from('<I',raw,80)[0]
            result['triangle_count']=count
            if len(raw)==84+50*count:
                vertices=[struct.unpack_from('<3f',raw,84+50*i+12+12*j) for i in range(count) for j in range(3)]
                result['bounds_model_units']=[[min(v[k] for v in vertices) for k in range(3)],
                                               [max(v[k] for v in vertices) for k in range(3)]]
                result['stl_units']='STL has no explicit unit metadata'
        assert raw==path.read_bytes()
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
