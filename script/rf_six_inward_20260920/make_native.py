from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;W=H.parent/'_support';U=2.54e-6;P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB'
g=json.loads((H/'geometry.json').read_text());rf=json.loads((H/'rf_routes.json').read_text());dc=json.loads((H/'dc_routes.json').read_text());n=json.loads((H/'baseline_native.json').read_text());q=lambda v:round(v/U)
assert hashlib.sha256((P/(B+'.PcbDoc')).read_bytes()).hexdigest()==n['source_sha256']
assert not rf['validation']['errors'] and not dc['validation']['errors']
oldpads=[p for p in n['pads'] if p['component']];np={p['component']+'-'+p['number']:p for p in g['pads'] if p['component']};oldc={c['designator']:c for c in n['components']};moving=[c for c in g['components'] if c['designator'].startswith(('R','C'))]
assert len(oldpads)==141 and len(moving)==12 and len(g['via_moves'])==65
init=[]
for i,p in enumerate(oldpads,1):
 z=np[p['component']+'-'+p['number']]
 init.append(f" PR[{i}]:='{p['component']}';PN[{i}]:='{p['number']}';PNet[{i}]:='{p['net'] or ''}';NewNet[{i}]:='{z['net'] or ''}';OX[{i}]:={q(p['x'])};OY[{i}]:={q(p['y'])};PX[{i}]:={q(z['x'])};PY[{i}]:={q(z['y'])};PA[{i}]:={z['rotation']};")
labels={'R1':(15.2,31),'C1':(14.5,28.3),'R5':(3.6,31),'C5':(4.5,28.3),'R2':(17,42.5),'C2':(16.5,39.2),'R6':(1.8,41.8),'C6':(2.4,38.5),'R3':(12.1,47),'C3':(11.7,48.4),'R4':(6.4,47),'C4':(7.3,48.4)}
for i,c in enumerate(moving,1):
 o=oldc[c['designator']];tx,ty=labels[c['designator']]
 init.append(f" CR[{i}]:='{c['designator']}';CX[{i}]:={q(c['x'])};CY[{i}]:={q(c['y'])};CA[{i}]:={c['rotation']};COX[{i}]:={q(o['x'])};COY[{i}]:={q(o['y'])};COA[{i}]:={o['rotation']};TX[{i}]:={q(tx)};TY[{i}]:={q(ty)};")
for i,v in enumerate(g['via_moves'],1):
 init.append(f" VOX[{i}]:={q(v['old'][0])};VOY[{i}]:={q(v['old'][1])};VX[{i}]:={q(v['new'][0])};VY[{i}]:={q(v['new'][1])};VN[{i}]:='{v['old_net']}';NewVN[{i}]:='{v['net']}';VR1[{i}]:='{v['paste_names'][0]}';VR2[{i}]:='{v['paste_names'][1]}';")
src=(W/'rf_stubless_20260920/ApplyStubless.pas').read_text();helpers=src[src.index('Function FindNet'):src.index('Procedure ApplyStubless;')]
vsrc=(W/'rf_revision/rf_native_helpers.pas').read_text();helpers+=vsrc[vsrc.index('Function AddShieldVia'):vsrc.index('{ Layer material')].replace('AddShieldVia','AddSignalVia')
psrc=(W/'zif_revision_v2/native_helpers/FinalizeV2.pas').read_text();helpers+=psrc[psrc.index('Procedure V2AddPasteAperture'):psrc.index('Function V2RebuildExplicitPasteForAllVias')]
body=src[src.index('Procedure ApplyStubless;'):].replace('ApplyStubless','ApplyRF6').replace('stubless_apply.txt','rf6_apply.txt').replace('1..64','1..65').replace('To 64','To 65').replace('(NV<>64)','(NV<>65)').replace('(NR<>128)','(NR<>130)').replace('(NT<>388)','(NT<>284)').replace('(NA<>17)','(NA<>11)')
body=body.replace('Poly:IPCB_Polygon;','Poly:IPCB_Polygon;NN:IPCB_Net;PC:TPadCache;')
body=body.replace('PCBServer.PreProcess;\n Try','PCBServer.PreProcess;\n Try\n@NETS@')
body=body.replace("For J:=1 To 141 Do If (Copy(PR[J],1,1)='R') Or (Copy(PR[J],1,1)='C') Then Begin","For J:=1 To 141 Do Begin")
body=body.replace('P.Rotation:=PA[J];','P.Rotation:=PA[J];P.Net:=FindNet(B,NewNet[J]);')
a=body.index('  For J:=1 To 65 Do If (VX[J]');b=body.index('\n',a)
body=body[:a]+"  For J:=1 To 65 Do Begin VS[J].MoveToXY(VX[J],VY[J]);VS[J].Net:=FindNet(B,NewVN[J]);A1[J].MoveByXY(VX[J]-VOX[J],VY[J]-VOY[J]);A2[J].MoveByXY(VX[J]-VOX[J],VY[J]-VOY[J]);End;\n@NEWVIAS@\n@ROUTES@"+body[b:]
# Original script embeds generated routes: remove them up to the transaction end.
a=body.index('@ROUTES@')+len('@ROUTES@');b=body.index(' Finally PCBServer.PostProcess;',a);body=body[:a]+'\n'+body[b:]
body=body.replace(' B.SetState_DocumentHasChanged;'," I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));NN:=I.FirstPCBObject;While NN<>Nil Do Begin NN.ConnectivelyInValidate;NN.Rebuild;NN:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;\n B.SetState_DocumentHasChanged;")
body=body.replace("L.Add('SAVED');", "L.Add('SAVED');D:=Client.GetDocumentByPath(Path+'QSTL_24DC_4MW_PCB.SchDoc');If D<>Nil Then Client.CloseDocument(D);D:=Client.GetDocumentByPath(Path+'QSTL_24DC_4MW_PCB.SchLib');If D<>Nil Then Client.CloseDocument(D);")
nets=[]
for net in ['S5','MW5','S6','MW6']:nets.append(f" NN:=PCBServer.PCBObjectFactory(eNetObject,eNoDimension,eCreate_Default);NN.Name:='{net}';B.AddPCBObject(NN);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,NN.I_ObjectAddress);")
newvias=[]
for v in g['added_vias']:
 newvias.append(" V:=AddSignalVia(B,FindNet(B,'%s'),%.12f,%.12f,0.5,0.25);PC:=V.GetState_Cache;PC.SolderMaskExpansion:=MMsToCoord(0.025);PC.SolderMaskBottomExpansion:=MMsToCoord(0.025);PC.SolderMaskExpansionValid:=eCacheManual;V.SetState_Cache(PC);V.SetState_IsTenting_Top(True);V.SetState_IsTenting_Bottom(True);V2AddPasteAperture(B,V,eTopPaste,'ZIFV2_PASTE_T_RF6_%s');V2AddPasteAperture(B,V,eBottomPaste,'ZIFV2_PASTE_B_RF6_%s');"%(v['net'],v['x'],v['y'],v['pin'],v['pin']))
route=[]
for t in [t for t in n['tracks'] if t['layer']==1]+dc['tracks']+rf['tracks']:
 route.append(" AddRFTrack(B,FindNet(B,'%s'),%s,%s);"%(t['net'],{1:'eTopLayer',2:'eMidLayer1',4:'eMidLayer3',32:'eBottomLayer'}[t['layer']],','.join(f'{t[k]:.12f}' for k in ['x1','y1','x2','y2','width'])))
for a in rf['arcs']:route.append(" AddRFArc(B,FindNet(B,'%s'),eBottomLayer,%s);"%(a['net'],','.join(f'{a[k]:.12f}' for k in ['cx','cy','radius','width','start_angle','end_angle'])))
header=src[:src.index('Procedure InitPlan;')].replace('PR,PN,PNet:','PR,PN,PNet,NewNet:').replace('1..64','1..65').replace('VN,VR1,VR2:','VN,NewVN,VR1,VR2:')
script=header+'Procedure InitPlan;Begin\n'+'\n'.join(init)+'\nEnd;\n'+helpers+body.replace('@NETS@','\n'.join(nets)).replace('@NEWVIAS@','\n'.join(newvias)).replace('@ROUTES@','\n'.join(route))
assert '(NT<>284)' in script and 'PREFLIGHT_PASSED' in script and script.count('NN:=PCBServer.PCBObjectFactory(eNetObject')==4
assert script.index('PREFLIGHT_PASSED')<script.index('NN:=PCBServer.PCBObjectFactory(eNetObject')<script.index('V:=AddSignalVia')
(H/'ApplyRF6.pas').write_text(script,encoding='utf-8')
s=(W/'connection_audit_20260920/ReopenAudit.pas').read_text().replace('connection_reopen_check.txt','rf6_reopen_check.txt').replace('Connections_DRC.html','RF6_DRC.html');(H/'ReopenAudit.pas').write_text(s)
s=(W/'dc_direct_20260920/ValidateSchematic.pas').read_text().replace('dc_direct_schematic_compile.txt','rf6_schematic_compile.txt');(H/'ValidateSchematic.pas').write_text(s)
print('Native script prepared:',len(route),'route primitives;',len(g['added_vias']),'new pad-centre vias.')
