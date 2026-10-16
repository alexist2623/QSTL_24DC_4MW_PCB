"""Run read-only saved audits in a new evidence namespace; never call Altium."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
OLD=ROOT/'script/qd38_rotation_20261011'
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BASE='1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
HELPERS={'copper':'audit_saved_revision.py','surface':'audit_saved_revision_surface.py',
         'models':'audit_saved_revision_models.py','canonical':'audit_canonical_library.py','paste':'verify_revision_paste_cam.py'}
OUTPUTS={'copper':'saved_revision_audit.json','surface':'saved_revision_surface.json','models':'saved_revision_models.json',
         'canonical':'canonical_library_audit.json','rules':'saved_alignment_rules.json','delta':'saved_alignment_delta.json',
         'paste':'revision_native_paste_cam_validation.json'}

def worker(stage,candidate,audit):
    sys.path[:0]=[str(H),str(OLD)]
    if stage in ('rules','delta'):
        import audit_alignment_delta as delta
        if stage=='delta':delta.main(candidate);return
        report=delta.inspect_rules(json.loads(candidate.read_text()),DEST/'QSTL_QD4_2SET_38PAD.PcbDoc')
        (H/OUTPUTS[stage]).write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        if not report['passed']:raise SystemExit(1)
        return
    path=OLD/HELPERS[stage];code=path.read_text();source_hash=sha(path)
    if stage=='copper':
        replacements={"H/'before_rotation/QSTL_QD4_2SET_38PAD.PcbDoc'":"H/'before_alignment/QSTL_QD4_2SET_38PAD.PcbDoc'",
                      "'f8356dd694810d2318a51e99544ab2345f8b9996de80e9ddc4456bbc6a14c632'":repr(BASE),
                      'from revision_invariants import contact_pool, assert_plan_contacts, via_groups':'from revision_invariants import contact_pool, assert_plan_contacts\nfrom alignment_invariants import via_groups',
                      'g=shape(m).simplify(.001,preserve_topology=True);parts=list(g.geoms) if hasattr(g,\'geoms\') else [g]':
                          'g=shape(m) if family==\'GND\' else shape(m).simplify(.001,preserve_topology=True);parts=list(g.geoms) if hasattr(g,\'geoms\') else [g]'}
        for old,new in replacements.items():
            assert code.count(old)==1, f'Review changed helper before reuse: {old}'
            code=code.replace(old,new)
    if stage=='surface':
        replacements={
            'expected = shape(geojson).simplify(.001, preserve_topology=True)':
                'expected = shape(geojson) if family == "GND" else shape(geojson).simplify(.001, preserve_topology=True)',
            '    field = rectangle(unary_union([p["geometry"] for p in pads if p["ref"] == "Q1"]), .15)\n    check(field.hausdorff_distance(shape(plan["qd_mask_field"])) < COORD_TOL, "QD_mask_field_geometry")':
                '    from alignment_surface_contract import retained_mask_field\n    field, retained_mask_audit = retained_mask_field(plan, pads, regions, native_path)\n    check(retained_mask_audit["passed"], "retained_mask_family_contract", retained_mask_audit["errors"])\n    results["retained_mask_family"] = retained_mask_audit'
        }
        for old,new in replacements.items():
            assert code.count(old)==1, f'Review changed surface helper before reuse: {old}'
            code=code.replace(old,new)
    if stage=='paste':
        old="HERE/'ExportQD90PasteAuditLinked.pas'"
        assert code.count(old)==1, 'Review changed paste helper before reuse'
        code=code.replace(old,"HERE/'ExportQD38PasteAlignment.pas'")
    args=[str(H/HELPERS[stage])]
    if stage in ('copper','surface','canonical'):args+=['--candidate',str(candidate)]
    if stage=='copper':args+=['--audit',str(audit)]
    if stage=='canonical':args+=['--library',str(DEST/'QD4_2SET_38.PcbLib')]
    sys.argv=args
    # __file__ deliberately names this new directory, so all helpers derive
    # their input logs/output reports here. Their repository root stays equal.
    virtual=H/HELPERS[stage]
    exec(compile(code,str(virtual),'exec'),{'__name__':'__main__','__file__':str(virtual)})
    assert sha(path)==source_hash,'Borrowed helper was changed during its run'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate',type=Path,default=H/'alignment_full_candidate.json')
    ap.add_argument('--audit',type=Path,default=H/'alignment_full_audit.json')
    ap.add_argument('--stages',default='copper,surface,models,canonical,rules,delta')
    ap.add_argument('--worker',choices=list(OUTPUTS))
    args=ap.parse_args();candidate=args.candidate.resolve();audit=args.audit.resolve()
    if args.worker:worker(args.worker,candidate,audit);return
    stages=args.stages.split(',');assert all(s in OUTPUTS for s in stages)
    required=[candidate,audit,H/'alignment_delta_manifest.json',H/'before_alignment/manifest.json',H/'native_validation.txt',H/'native_compile.txt',H/'Native_DRC.html']
    missing=[str(p) for p in required if not p.is_file()]
    if missing:
        print(json.dumps(dict(passed=False,status='MISSING_ALIGNMENT_EVIDENCE',missing=missing),indent=2));raise SystemExit(2)
    a=json.loads(audit.read_text());assert a.get('passed') is True and a.get('candidate_sha256')==sha(candidate)
    frozen=json.loads((H/'before_alignment/manifest.json').read_text())
    completion=Path(frozen['completion_evidence']);assert sha(completion)==frozen['completion_sha256']
    old_evidence=json.loads(completion.read_text())['evidence']
    protected={Path(v['path']):v['sha256'] for v in old_evidence.values() if Path(v['path']).parent==OLD}
    protected[completion]=sha(completion)
    assert all(sha(p)==digest for p,digest in protected.items())
    results=[]
    for stage in stages:
        log=H/f'alignment_audit_{stage}.txt'
        with log.open('w',encoding='utf-8') as out:
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',stage,'--candidate',str(candidate),'--audit',str(audit)],cwd=H,stdout=out,stderr=subprocess.STDOUT)
        report_path=H/OUTPUTS[stage]
        report=json.loads(report_path.read_text()) if report_path.is_file() else {}
        passed=result.returncode==0 and report.get('passed') is True
        results.append(dict(stage=stage,passed=passed,returncode=result.returncode,report=str(report_path),log=str(log),report_sha256=sha(report_path) if report_path.is_file() else None))
        print(json.dumps(results[-1]),flush=True)
        if not passed:break
    preserved=all(sha(p)==digest for p,digest in protected.items())
    report=dict(passed=len(results)==len(stages) and all(r['passed'] for r in results) and preserved,
                native_sha256=sha(DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'),candidate_sha256=sha(candidate),
                candidate_audit_sha256=sha(audit),baseline_native_sha256=BASE,old_evidence_preserved=preserved,
                results=results,completion=False,native_commands_executed=False,
                scope='Read-only saved evidence stages. Paste and final completion remain separate unless explicitly run and bound.')
    (H/'alignment_saved_audit_workflow.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
