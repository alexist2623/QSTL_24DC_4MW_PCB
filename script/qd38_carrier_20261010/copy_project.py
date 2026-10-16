"""Create the explicitly requested isolated carrier project copy."""
from pathlib import Path
import configparser
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'QSTL_24DC_4MW_PCB'
DEST = ROOT / 'QSTL_QD4_2SET_38PAD'
OLD = 'QSTL_24DC_4MW_PCB'
NEW = 'QSTL_QD4_2SET_38PAD'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not DEST.exists(), 'Do not overwrite an existing working copy.'
project = configparser.RawConfigParser(strict=False)
project.optionxform = str
project.read(SOURCE / (OLD+'.PrjPcb'), encoding='utf-8-sig')
extensions = {'.pcbdoc', '.schdoc', '.pcblib', '.schlib'}
kept = []
removed = []
for section in list(project.sections()):
    if not section.startswith('Document'):
        continue
    path = project[section].get('DocumentPath')
    if path and Path(path).suffix.lower() in extensions:
        assert (SOURCE/path).is_file(), path
        kept.append(path)
        project[section]['DocumentPath'] = path.replace(OLD, NEW)
    else:
        removed.append(path)
        project.remove_section(section)
before = {p: sha(SOURCE/p) for p in kept + [OLD+'.PrjPcb']}
DEST.mkdir()
for name in kept:
    shutil.copy2(SOURCE/name, DEST/name.replace(OLD, NEW))
for name in ['SMP-FS-SBPCT.stp', '581-M25-113L461.STEP']:
    if (SOURCE/name).is_file():
        shutil.copy2(SOURCE/name, DEST/name)
with (DEST/(NEW+'.PrjPcb')).open('w', encoding='utf-8', newline='') as f:
    project.write(f, space_around_delimiters=False)
assert before == {p: sha(SOURCE/p) for p in before}
audit = dict(source=str(SOURCE), copy=str(DEST), status='Copied; QD replacement and rerouting pending',
             source_sha256=before, copied_documents=kept,
             excluded_stale_output_documents=removed, original_preserved=True)
(DEST/'copy_provenance.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
(DEST/'README.md').write_text('# QD4 / 2SET 38-pad carrier\n\nWork in progress. This is the requested copy of the current carrier. The source project remains unchanged.\n\nTarget: 38 DC channels, with bias tees on the 16 selected RF terminals, 5.3 x 4.3 mm cavity, bonding-aligned pads, and symmetric SMP placement. Routing and native DRC are pending. Stale manufacturing outputs are intentionally not part of this copied project.\n', encoding='utf-8')
print(json.dumps(audit, indent=2))
