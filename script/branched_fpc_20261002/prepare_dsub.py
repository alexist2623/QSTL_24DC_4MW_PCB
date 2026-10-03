"""Prepare the ZIF-finger to Micro-D adapter and guarded native Altium build."""
from pathlib import Path
import sys,json,re,struct,hashlib
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,olefile,GUID_TAGS
from cfb_copy_update import update_copy
OUT=R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002/ZIF_to_DSUB25'
OUT.mkdir(parents=True,exist_ok=True)
NAME='ZIF_to_DSUB25';PCB=OUT/(NAME+'.PcbDoc')
REF=json.loads((H/'reference/anton_connector.json').read_text())
plan={'name':NAME,'length_mm':40,'width_mm':31,'contact_width_mm':15.6,'assumptions':['40 mm overall length is provisional; no user dimension supplied.','DSUB mounting area uses a bonded back stiffener, nominal finished thickness 1.6 mm.'],'nets':[],'components':[],'pads':[],'regions':[],'tracks':[],'vias':[],'outline':[[0,0],[31,0],[31,15],[23.3,22.7],[23.3,40],[7.7,40],[7.7,22.7],[0,15]],'source_mapping':REF['mapping'],'source_hashes':REF['source_sha256']}
plan['components']=[{'ref':'A','x':15.5,'y':40,'pattern':'FPC51_P030_STAGGERED','layer':1},{'ref':'J1','x':7.88,'y':8.81,'pattern':'NORCOMP_381_025_112L565','layer':1}]
def trace(net,layer,points,width):
    for a,b in zip(points,points[1:]):
        if a!=b:plan['tracks'].append(dict(net=net,layer=layer,a=a,b=b,width=width))
def terminal(i):
    edge=[(0,.05),(.15,.05),(.25,.15),(1.1,.15),(1.2,.05),(2,.05),(2.1,.1),(3.05,.1)] if i%2 else [(0,.05),(1.1,.05),(1.2,.15),(2,.15),(2.1,.1),(3.05,.1)]
    return [[7.7+.3*i+w,40-x] for x,w in edge]+[[7.7+.3*i-w,40-x] for x,w in reversed(edge)]
inverse={int(v):int(k) for k,v in REF['mapping'].items()}
for pin in range(1,52):
    net=f'DSUB_{inverse[pin]:02d}' if pin in inverse else f'NC_A{pin:02d}'
    plan['nets'].append(net)
    plan['pads'].append(dict(ref='A',pin=str(pin),net=net,x=7.7+.3*pin,y=39.35,sx=.1,sy=.3,hole=0,layer=1,shape='rect'))
    plan['regions'].append(dict(name=f'A_CONTACT_{pin}',net=net,layer=1,points=terminal(pin)))
    if pin not in inverse:continue
    dp=inverse[pin];source=next(x for x in REF['pads'] if int(x['pin'])==dp)
    x=7.88+source['at_mm'][0];y=8.81-source['at_mm'][1];fx=7.7+.3*pin
    plan['pads'].append(dict(ref='J1',pin=str(dp),net=net,x=x,y=y,sx=.9652,sy=.9652,hole=.7112,layer=74,shape='round'))
    layer=1 if dp<=13 else 32
    end_y=36.95 if layer==1 else 23
    trace(net,layer,[[x,y],[x,11]],.10)
    trace(net,layer,[[x,11],[x,12],[fx,17],[fx,end_y]],.20)
    if layer==32:
        plan['vias'].append(dict(net=net,x=fx,y=23,diameter=.4,hole=.2))
        trace(net,1,[[fx,23],[fx,36.95]],.20)
for pin,x in [('BL1',3.245),('BL2',27.755)]:
    plan['pads'].append(dict(ref='J1',pin=pin,net=None,x=x,y=5,sx=3.3,sy=3.3,hole=2.69,layer=74,shape='round'))
plan['regions'].append(dict(name='A_COVERLAY_OPENING',net=None,layer=37,points=[[7.69,37],[23.31,37],[23.31,40.01],[7.69,40.01]]))
for x0,y0,x1,y1 in [(7.7,36,23.3,40),(0,0,31,15)]:
    trace(None,58,[[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]],.03)
(OUT/'design_plan.json').write_text(json.dumps(plan,indent=2)+'\n')

source=R/'script/fpc_15015_0451_20261002/before_stack.PcbDoc'
with olefile.OleFileIO(source) as o:d={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
b=properties(d['Board6/Data'])[0]
def mil(v):return f'{v/.0254:.9f}mil'
for prefix in ('V9_MASTERSTACK_','V9_SUBSTACK0_','LAYERMASTERSTACK_V8','LAYERSUBSTACK_V8_0'):
    b[prefix+'ISFLEX']='TRUE';b[prefix+'NAME']='Two copper flex';b[prefix+'SHOWTOPDIELECTRIC']='TRUE';b[prefix+'SHOWBOTTOMDIELECTRIC']='TRUE'
for k in ('V9_MASTERSTACK_STYLE','LAYERMASTERSTACK_V8STYLE','LAYERSTACKSTYLE'):b[k]='3'
for pattern,fmt in [(r'V9_STACK_LAYER(\d+)_(.*)',lambda i,s:f'V9_STACK_LAYER{i}_{s}'),(r'LAYER_V8_(\d+)(.*)',lambda i,s:f'LAYER_V8_{i}{s}')]:
    entries={}
    for k in list(b):
        m=re.fullmatch(pattern,k)
        if m:entries.setdefault(int(m[1]),{})[m[2]]=b.pop(k)
    for i,item in entries.items():
        if item.get('NAME') in ('Top Layer','Bottom Layer'):item['COPTHICK']=mil(.018)
        if item.get('NAME') in ('Top Solder','Bottom Solder'):item.update(DIELHEIGHT=mil(.025),DIELMATERIAL='Polyimide coverlay + adhesive',DIELCONST='3.5')
        if item.get('NAME')=='Dielectric 1':item.update(NAME='Polyimide core + adhesive',DIELHEIGHT=mil(.045),DIELMATERIAL='Polyimide + adhesive',DIELCONST='3.5',DIELTYPE='4')
        for k,v in item.items():b[fmt(i,k)]=v
b.update(LAYER1COPTHICK=mil(.018),LAYER32COPTHICK=mil(.018),LAYER1DIELHEIGHT=mil(.045),LAYER1DIELMATERIAL='Polyimide + adhesive',LAYER1DIELTYPE='4')
def packprops(p):
    raw=('|'+'|'.join(k+'='+str(v) for k,v in p.items())+'\0').encode('cp1252');return struct.pack('<I',len(raw))+raw
changes={'Board6/Data':packprops(b)}
cleared=['Nets6','Components6','Pads6','Tracks6','Regions6','ShapeBasedRegions6','Texts6','Connections6','PadViaCacheLibraryLinksSection','UniqueIDPrimitiveInformation','PrimitiveGuids']
for s in cleared:
    if s+'/Data' in d:changes[s+'/Data']=b''
    if s+'/Header' in d:changes[s+'/Header']=struct.pack('<I',0)
if not PCB.exists():update_copy(source,PCB,changes)
code=[r'''{ Build only the new adapter; preserve all original designs. }
Var B:IPCB_Board;Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('__H__\dsub_build.txt');End;
Procedure Reg(P:IPCB_Primitive);Begin B.AddPCBObject(P);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,P.I_ObjectAddress);End;
Procedure BuildAdapters;
Var D:IServerDocument;I:IPCB_BoardIterator;P:IPCB_Primitive;N:IPCB_Net;A,J:IPCB_Component;PD:IPCB_Pad;T:IPCB_Track;V:IPCB_Via;RG:IPCB_Region;C:IPCB_Contour;G:IPCB_GeometricPolygon;O:IPCB_BoardOutline;S:TPolySegment;PC:TPadCache;R:IPCB_Rule;CL:IPCB_ClearanceConstraint;WC:IPCB_MaxMinWidthConstraint;Count:Integer;
Begin
 Log:=TStringList.Create;Mark('START');
 D:=Client.OpenDocument('PCB','__PCB__');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('__PCB__') Then Exit;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;Count:=0;
 While P<>Nil Do Begin Inc(Count);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If Count<>0 Then Begin Mark('STOP_NOT_BLANK');Exit;End;
 PCBServer.PreProcess;
 Try
 O:=B.BoardOutline;O.PointCount:=8;S:=O.Segments[0];
''']
e=code.append
for i,(x,y) in enumerate(plan['outline']):e(f'S.Kind:=ePolySegmentLine;S.vx:=MMsToCoord({x});S.vy:=MMsToCoord({y});O.Segments[{i}]:=S;')
e('O.Segments[8]:=O.Segments[0];O.Invalidate;O.Rebuild;O.Validate;B.UpdateBoardOutline;B.RebuildSplitBoardRegions(True);')
for c in plan['components']:
    v='A' if c['ref']=='A' else 'J'
    e(f"{v}:=PCBServer.PCBObjectFactory(eComponentObject,eNoDimension,eCreate_Default);{v}.Name.Text:='{c['ref']}';{v}.Pattern:='{c['pattern']}';{v}.Layer:=eTopLayer;{v}.X:=MMsToCoord({c['x']});{v}.Y:=MMsToCoord({c['y']});{v}.NameOn:=False;{v}.CommentOn:=False;Reg({v});")
def layer(i):return {1:'eTopLayer',32:'eBottomLayer',37:'eTopSolder',38:'eBottomSolder',58:'eMechanical2',74:'eMultiLayer'}[i]
for net in plan['nets']+[None]:
    e("N:=Nil;" if net is None else f"N:=PCBServer.PCBObjectFactory(eNetObject,eNoDimension,eCreate_Default);N.Name:='{net}';Reg(N);")
    for p in [p for p in plan['pads'] if p['net']==net]:
        v='A' if p['ref']=='A' else 'J';shape='eRectangular' if p['shape']=='rect' else 'eRounded'
        e(f"PD:=PCBServer.PCBObjectFactory(ePadObject,eNoDimension,eCreate_Default);PD.Name:='{p['pin']}';PD.X:=MMsToCoord({p['x']});PD.Y:=MMsToCoord({p['y']});PD.Layer:={layer(p['layer'])};PD.Mode:=ePadMode_Simple;PD.TopShape:={shape};PD.MidShape:={shape};PD.BotShape:={shape};")
        e(f"PD.TopXSize:=MMsToCoord({p['sx']});PD.TopYSize:=MMsToCoord({p['sy']});PD.MidXSize:=PD.TopXSize;PD.MidYSize:=PD.TopYSize;PD.BotXSize:=PD.TopXSize;PD.BotYSize:=PD.TopYSize;PD.HoleSize:=MMsToCoord({p['hole']});PD.Plated:=True;PD.Net:=N;PD.SetState_PasteMaskEnabled(False);")
        e('PC:=PD.GetState_Cache;PC.PasteMaskExpansionValid:=eCacheManual;PC.PasteMaskExpansion:=MMsToCoord(-2);PC.SolderMaskExpansionValid:=eCacheManual;PC.SolderMaskExpansion:=MMsToCoord(0.05);PC.SolderMaskBottomExpansion:=MMsToCoord(0.05);PD.SetState_Cache(PC);'+v+'.AddPCBObject(PD);Reg(PD);')
    for r in [r for r in plan['regions'] if r['net']==net]:
        e('G:=PCBServer.PCBGeometricPolygonFactory;C:=PCBServer.PCBContourFactory;')
        for x,y in r['points']:e(f'C.AddPoint(MMsToCoord({x}),MMsToCoord({y}));')
        e(f"G.AddContourIsHole(C,False);RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={layer(r['layer'])};RG.Name:='{r['name']}';RG.SetGeometricPolygon(G);RG.Net:=N;Reg(RG);")
    for t in [t for t in plan['tracks'] if t['net']==net]:
        e(f"T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);T.X1:=MMsToCoord({t['a'][0]});T.Y1:=MMsToCoord({t['a'][1]});T.X2:=MMsToCoord({t['b'][0]});T.Y2:=MMsToCoord({t['b'][1]});T.Width:=MMsToCoord({t['width']});T.Layer:={layer(t['layer'])};T.Net:=N;Reg(T);")
    for v in [v for v in plan['vias'] if v['net']==net]:
        e(f"V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);V.X:=MMsToCoord({v['x']});V.Y:=MMsToCoord({v['y']});V.Size:=MMsToCoord({v['diameter']});V.HoleSize:=MMsToCoord({v['hole']});V.LowLayer:=eTopLayer;V.HighLayer:=eBottomLayer;V.Net:=N;V.SetState_PasteMaskEnabled(False);Reg(V);")
e(r'''
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
 While R<>Nil Do Begin
 If R.RuleKind=eRule_Clearance Then Begin CL:=R;CL.Gap:=MMsToCoord(0.0707);End;
 If R.RuleKind=eRule_MaxMinWidth Then Begin WC:=R;WC.MinWidth[eTopLayer]:=MMsToCoord(0.09999);WC.MinWidth[eBottomLayer]:=MMsToCoord(0.09999);WC.MaxWidth[eTopLayer]:=MMsToCoord(0.3);WC.MaxWidth[eBottomLayer]:=MMsToCoord(0.3);End;
 R:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.RebuildPadCaches;
 Finally PCBServer.PostProcess;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 Mark('SAVED');B.GraphicalView_ZoomOnRect(MMsToCoord(-2),MMsToCoord(-2),MMsToCoord(33),MMsToCoord(42));Mark('COMPLETE');Log.Free;
End;
''')
text='\n'.join(code).replace('__H__',str(H)).replace('__PCB__',str(PCB))
text=re.sub(r'(?<![\w])\.(\d)',r'0.\1',text)
(H/'BuildAdapters.pas').write_text(text,encoding='ascii')
(H/'BuildAdapters.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=BuildAdapters.pas\n[Generic_ScriptingSystem]\nStartProcName=BuildAdapters.pas>BuildAdapters\n')
(OUT/(NAME+'.PrjPcb')).write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath='+NAME+'.PcbDoc\n')
print(json.dumps({'pads':len(plan['pads']),'tracks':len(plan['tracks']),'vias':len(plan['vias']),'target':str(PCB)}))
