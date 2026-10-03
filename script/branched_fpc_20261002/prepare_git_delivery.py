"""Update publication wording without changing design or validation state."""
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[1]
out = R / 'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002'
paths = list(out.rglob('README.md')) + [H/'publish_validation_status.py', H/'README.md', R/'QSTL_24DC_4MW_PCB/FPC_15015_0451/README.md']
replacements = {
    'No Git push, supplier upload or order was performed.': 'Git delivery to the existing repository was requested on 2026-10-03. No supplier upload, fabrication release or order was performed.',
    'No fabrication release, Git push, upload or order was performed.': 'Git delivery was requested on 2026-10-03. No fabrication release, supplier upload or order was performed.',
    'No fabrication release or Git push has been performed.': 'Git delivery was requested on 2026-10-03; the pending native validation remains documented and no fabrication release has been performed.',
    'No Gerber fabrication release, vendor upload, purchase or Git push was requested or performed for this cable.': 'Git delivery of this source cable and the two derivative adapters was requested on 2026-10-03. No Gerber fabrication release, vendor upload or purchase was performed.',
}
for path in paths:
    text = path.read_text(encoding='utf-8')
    for old, new in replacements.items():
        text = text.replace(old, new)
    path.write_text(text.rstrip()+'\n', encoding='utf-8')
for path in (R/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md', H/'inspect_sources.py', R/'script/fpc_15015_0451_20261002/build_native.py'):
    text=path.read_text(encoding='utf-8')
    path.write_text(text.rstrip()+'\n', encoding='utf-8')
print('Publication wording updated; design files and validation status preserved.')
