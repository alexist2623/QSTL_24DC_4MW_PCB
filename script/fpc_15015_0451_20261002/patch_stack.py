"""Update only the closed cable document's native V9/V8 stack records.

Altium reopens and resaves the result before delivery. The previous native file
is retained beside the helper, and all other compound streams are preserved.
"""
from pathlib import Path
import sys, struct, re, shutil, json
H=Path(__file__).resolve().parent
R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,olefile
from cfb_copy_update import update_copy
OUT=R/'QSTL_24DC_4MW_PCB/FPC_15015_0451'
P=OUT/'FPC_15015_0451.PcbDoc'
BACK=H/'before_stack.PcbDoc'
assert not BACK.exists(), 'One-time patch; do not overwrite the backup.'
shutil.copy2(P,BACK)
with olefile.OleFileIO(BACK) as o:
    boards=properties(o.openstream('Board6/Data').read())
    rules=o.openstream('Rules6/Data').read()
b=boards[0]
def mil(mm):return f'{mm/.0254:.9f}mil'
for prefix in ('V9_MASTERSTACK_','V9_SUBSTACK0_','LAYERMASTERSTACK_V8','LAYERSUBSTACK_V8_0'):
    b[prefix+'ISFLEX']='TRUE'
    b[prefix+'SHOWBOTTOMDIELECTRIC']='TRUE'
    b[prefix+'NAME']='Single copper flex' if 'MASTER' in prefix else 'Flex body'
for k in ('V9_MASTERSTACK_STYLE','LAYERMASTERSTACK_V8STYLE','LAYERSTACKSTYLE'):b[k]='3'
for pattern,fmt in [(r'V9_STACK_LAYER(\d+)_(.*)',lambda i,s:f'V9_STACK_LAYER{i}_{s}'),(r'LAYER_V8_(\d+)(.*)',lambda i,s:f'LAYER_V8_{i}{s}')]:
    entries={}
    for k in list(b):
        m=re.fullmatch(pattern,k)
        if m:entries.setdefault(int(m[1]),{})[m[2]]=b.pop(k)
    retained=[]
    for i,row in sorted(entries.items()):
        name=row.get('NAME')
        if name in ('Bottom Layer','Bottom Solder'):continue
        if name=='Top Layer':row['COPTHICK']=mil(.018)
        if name=='Top Solder':row.update(DIELHEIGHT=mil(.050),DIELMATERIAL='Polyimide coverlay + adhesive',DIELCONST='3.5')
        if name=='Dielectric 1':row.update(NAME='Polyimide base + adhesive',DIELHEIGHT=mil(.045),DIELMATERIAL='Polyimide + adhesive',DIELCONST='3.5',DIELTYPE='4')
        if name=='Mechanical 1':row['NAME']='Cable fabrication notes'
        if name=='Mechanical 2':row['NAME']='Back stiffener boundary'
        retained.append(row)
    for i,row in enumerate(retained):
        for k,v in row.items():b[fmt(i,k)]=v
b.update(LAYER1NEXT='0',LAYER32PREV='0',LAYER1COPTHICK=mil(.018),LAYER1DIELHEIGHT=mil(.045),LAYER1DIELMATERIAL='Polyimide + adhesive',LAYER1DIELTYPE='4')
def packprops(p):
    v=('|'+'|'.join(k+'='+str(v) for k,v in p.items())+'\0').encode('cp1252')
    return struct.pack('<I',len(v))+v
# The staggered drawing's opposed 45-degree necks have a nominal minimum
# Euclidean separation of 0.1/sqrt(2) mm. Preserve geometry and set its actual rule.
pos=0;rr=[]
while pos<len(rules):
    kind=rules[pos:pos+2];n=struct.unpack_from('<I',rules,pos+2)[0]
    row=properties(rules[pos+2:pos+6+n])[0]
    if row.get('RULEKIND')=='Clearance':
        for k in list(row):
            if k=='GAP' or k.startswith('CLEARANCE'):row[k]=mil(.0707)
        row['COMMENT']='Molex staggered fingers: nominal diagonal gap 0.0707107 mm; 0.10 mm straight gap.'
    rr.append(kind+packprops(row));pos+=6+n
TEMP=H/'stack_updated.PcbDoc'
update_copy(BACK,TEMP,{'Board6/Data':b''.join(map(packprops,boards)),'Rules6/Data':b''.join(rr)})
shutil.copy2(TEMP,P)
(H/'stack_patch.json').write_text(json.dumps({'removed_layers':['Bottom Layer','Bottom Solder'],'copper_mm':.018,'base_mm':.045,'coverlay_mm':.050,'flex':True},indent=2))
print('Patched closed FPC document; requires native reopen/save validation.')
