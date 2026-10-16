"""Promote only the validated library and physical companion plan."""
from pathlib import Path
import hashlib,json,shutil,sys
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    assert sys.argv[1]=='promote'
    cp=H/'alignment_full_candidate.json';a=read(H/'alignment_full_audit.json')
    assert a['passed'] and a['candidate_sha256']==sha(cp)
    assert 'COMPLETE_NOT_SAVED' in (H/'native_alignment_delta.txt').read_text()
    lib=H/'library_staging/QD4_2SET_38.PcbLib';la=read(lib.with_name('library_xy_patch_audit.json'))
    assert la['passed'] and la['staged_library_sha256']==sha(lib) and la['only_pad_XY_fields_changed']
    freeze=read(H/'before_alignment/manifest.json');unchanged={}
    mutable={'QD4_2SET_38.PcbLib','circuit_plan.json','full_copper_candidate.json'}
    for item in freeze['files']:
        path=Path(item['source']);assert sha(Path(item['backup']))==item['sha256']
        if path.name in mutable:assert sha(path)==item['sha256']
        elif path.suffix.lower() in ('.schdoc','.schlib','.prjpcb') or path.name=='pin_mapping.csv':
            assert sha(path)==item['sha256'];unchanged[path.name]=item['sha256']
    changed=[]
    for source,target in ((lib,DEST/lib.name),(cp,DEST/'circuit_plan.json'),(cp,DEST/'full_copper_candidate.json')):
        shutil.copy2(source,target);assert sha(source)==sha(target)
        changed.append(dict(name=target.name,path=str(target),sha256=sha(target)))
    report=dict(candidate_sha256=sha(cp),library_sha256=sha(lib),project_unchanged_sha256=sha(DEST/(DEST.name+'.PrjPcb')),
      unchanged_sources=unchanged,changed=changed,schematic_or_pin_mapping_changes=False)
    (H/'alignment_source_promotion.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Promoted library and physical plans; schematic, net mapping and project unchanged.')
if __name__=='__main__':main()
