"""Prepare a native paste-only CAM audit job without changing a PCB/project.

The generated OutJob remains under script and is temporarily associated with
the live copied project during export, then removed without saving the project.
Altium execution is a separate, explicit step managed by the root.
"""
from pathlib import Path
import argparse
import configparser
from datetime import datetime, timezone
import hashlib
import json
import re
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
PCB=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'
PROJECT=DEST/'QSTL_QD4_2SET_38PAD.PrjPcb'
REVIEW=HERE/'review'
JOB=HERE/'Revision_Paste_Audit_Only.OutJob'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True,type=Path)
    parser.add_argument('--audit',required=True,type=Path)
    args=parser.parse_args()
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    candidate=args.candidate.resolve();audit_path=args.audit.resolve()
    audit=json.loads(audit_path.read_text())
    assert audit.get('passed') is True and audit.get('candidate_sha256')==digest(candidate)
    saved=json.loads((HERE/'saved_revision_audit.json').read_text())
    assert saved.get('passed') is True and saved.get('native_sha256')==digest(PCB) and saved.get('candidate_sha256')==digest(candidate)
    canonical=json.loads((HERE/'canonical_library_audit.json').read_text())
    library=DEST/'QD4_2SET_38.PcbLib'
    assert canonical.get('passed') is True and canonical.get('library_sha256')==digest(library) and canonical.get('candidate_sha256')==digest(candidate)
    token=uuid.uuid4().hex
    CAM=REVIEW/'paste_native_cam_revision'/token
    CAM.mkdir(parents=True,exist_ok=True)
    cfg=configparser.ConfigParser(interpolation=None,strict=False)
    cfg.optionxform=str
    cfg.read(ROOT/'script/branch_linear_proposal_20261006/Candidate_Fabrication.OutJob',encoding='cp1252')
    cfg['OutputJobFile']['Caption']='Internal paste aperture audit only'
    cfg['OutputJobFile']['Description']='Top and Bottom paste proof, not a fabrication release'
    group=cfg['OutputGroup1']
    for key in list(group):
        if re.match(r'(Output(?:Type|Name|Category|DocumentPath|VariantName|Enabled|Default)2|Configuration2_)',key):
            del group[key]
    group['Name']=JOB.name
    group['OutputDocumentPath1']=PCB.name
    group['OutputName1']='Paste aperture audit'
    params=dict(part.split('=',1) for part in group['Configuration1_Item2'].split('|') if '=' in part)
    params.update({'DocumentPath':str(PCB),'Plot.Set':'SerializeLayerHash.Version~2,ClassName~TPlotLayerStateArray,16973832~1,16973833~1',
                   'PlotBoardProfile':'False','OriginPosition':'Absolute','GenerateReports':'True',
                   'GenerateDRCRulesFile':'False','PlotUsedDrillDrawingLayerPairs':'False','PlotUsedDrillGuideLayerPairs':'False',
                   'NumberOfDecimals':'6','GerberUnit':'Metric','CentrePlots':'False'})
    group['Configuration1_Item2']='|'.join(k+'='+v for k,v in params.items())
    for section,key in [('PublishSettings','OutputFilePath1'),('PublishSettings','OutputBasePath1'),('GeneratedFilesSettings','RelativeOutputPath1')]:
        cfg[section][key]=str(CAM)+'\\'
    cfg['PublishSettings']['PromptOverwrite1']='0'
    with JOB.open('w',encoding='cp1252',newline='\r\n') as out:
        cfg.write(out,space_around_delimiters=False)
    pas=r'''Var PasteLog:TStringList;
Function BText(B:Boolean):String;Begin If B Then Result:='1' Else Result:='0';End;
Procedure MarkPaste(S:String);Begin PasteLog.Add(S);PasteLog.SaveToFile('__H__\revision_paste_export_native_log.txt');End;
Procedure ExportQD90PasteAuditLinked;
Var D:IServerDocument;B:IPCB_Board;I:IPCB_BoardIterator;C:IPCB_Component;P:IPCB_Pad;V:IPCB_Via;
    PC:TPadCache;Count:Integer;RefName:String;WS:IWorkspace;Project:IProject;AddedJob:Boolean;
Begin
 PasteLog:=TStringList.Create;MarkPaste('START');MarkPaste('TOKEN=__TOKEN__');MarkPaste('BOUND_NATIVE_SHA256=__NATIVE_SHA__');
 ResetParameters;AddStringParameter('ObjectKind','Project');AddStringParameter('FileName','__PROJECT__');RunProcess('WorkspaceManager:OpenObject');
 WS:=GetWorkspace;If WS=Nil Then Begin MarkPaste('STOP_NO_WORKSPACE');Exit;End;
 Project:=WS.DM_GetProjectFromPath('__PROJECT__');If Project=Nil Then Begin MarkPaste('STOP_NO_PROJECT');Exit;End;
 If LowerCase(Project.DM_ProjectFullPath)<>LowerCase('__PROJECT__') Then Begin MarkPaste('STOP_WRONG_PROJECT');Exit;End;
 Project.DM_SetAsCurrentProject;MarkPaste('PROJECT='+Project.DM_ProjectFullPath);
 D:=Client.OpenDocument('PCB','__PCB__');If D=Nil Then Begin MarkPaste('STOP_NO_DOCUMENT');Exit;End;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Begin MarkPaste('STOP_NO_BOARD');Exit;End;
 If LowerCase(B.FileName)<>LowerCase('__PCB__') Then Begin MarkPaste('STOP_WRONG_BOARD');Exit;End;
 MarkPaste('BOARD='+B.FileName);Count:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin Inc(Count);C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 If Count<>50 Then Begin MarkPaste('STOP_COMPONENT_COUNT='+IntToStr(Count));Exit;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin
  RefName:='MOUNT';If P.Component<>Nil Then RefName:=P.Component.Name.Text;
  PC:=P.GetState_Cache;
  PasteLog.Add('PAD|'+RefName+'|'+P.Name+'|'+IntToStr(P.X)+'|'+IntToStr(P.Y)+'|'+IntToStr(P.Layer)+'|'+IntToStr(PC.PasteMaskExpansion)+'|'+IntToStr(Ord(PC.PasteMaskExpansionValid))+'|'+BText(P.GetState_PasteMaskEnabled)+'|'+BText(P.GetState_IsTopPasteEnabled)+'|'+BText(P.GetState_IsBottomPasteEnabled));
  P:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);MarkPaste('PAD_FLAGS_READ');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;Count:=0;
 While V<>Nil Do Begin
  PC:=V.GetState_Cache;
  PasteLog.Add('VIA|'+IntToStr(Count)+'|'+IntToStr(V.X)+'|'+IntToStr(V.Y)+'|'+IntToStr(PC.PasteMaskExpansion)+'|'+IntToStr(Ord(PC.PasteMaskExpansionValid))+'|'+BText(V.GetState_PasteMaskEnabled));
  Inc(Count);V:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);MarkPaste('VIA_FLAGS_READ='+IntToStr(Count));
 D:=Client.OpenDocument('OUTPUTJOB','__JOB__');If D<>Nil Then Client.CloseDocument(D);
 AddedJob:=Project.DM_IndexOfSourceDocument('__JOB__')<0;
 Try
  If AddedJob Then Project.DM_AddSourceDocument('__JOB__');
  Project.DM_SetAsCurrentProject;
  MarkPaste('OUTJOB_PROJECT_INDEX='+IntToStr(Project.DM_IndexOfSourceDocument('__JOB__')));
  D:=Client.OpenDocument('OUTPUTJOB','__JOB__');If D=Nil Then Begin MarkPaste('STOP_NO_OUTJOB');Exit;End;Client.ShowDocument(D);
  MarkPaste('EXPORT_BEGIN');ResetParameters;AddStringParameter('ObjectKind','OutputBatch');AddStringParameter('Action','Run');RunProcess('WorkspaceManager:GenerateReport');
  MarkPaste('EXPORT_RETURNED');
 Finally
  If D<>Nil Then Client.CloseDocument(D);
  If AddedJob Then Begin Project.DM_RemoveSourceDocument('__JOB__');MarkPaste('TEMPORARY_OUTJOB_REMOVED');End;
 End;
 MarkPaste('COMPLETE');PasteLog.Free;
End;
'''
    for key,value in {'__H__':HERE,'__PCB__':PCB,'__PROJECT__':PROJECT,'__JOB__':JOB,'__TOKEN__':token,'__NATIVE_SHA__':digest(PCB)}.items():
        pas=pas.replace(key,str(value))
    (HERE/'ExportQD90PasteAuditLinked.pas').write_text(pas,encoding='ascii')
    (HERE/'ExportQD90PasteAuditLinked.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=ExportQD90PasteAuditLinked.pas\n[Generic_ScriptingSystem]\nStartProcName=ExportQD90PasteAuditLinked.pas>ExportQD90PasteAuditLinked\n',encoding='ascii')
    manifest=dict(status='PREPARED_NOT_EXECUTED',pcb=str(PCB),pcb_sha256=hashlib.sha256(PCB.read_bytes()).hexdigest(),
                  project_sha256=hashlib.sha256(PROJECT.read_bytes()).hexdigest(),outjob=str(JOB),cam_directory=str(CAM),
                  expected_cam_layers=['Top Paste','Bottom Paste'],output_layer_ids=[16973832,16973833],
                  expected_automatic_pad_apertures=dict(Top=53,Bottom=64),fabrication_release=False,
                  export_script='ExportQD90PasteAuditLinked',temporary_live_project_membership=True,
                  project_file_save_requested=False,export_token=token,prepared_utc=datetime.now(timezone.utc).isoformat(),
                  candidate_file=str(candidate),candidate_sha256=digest(candidate),candidate_audit_file=str(audit_path),candidate_audit_sha256=digest(audit_path),
                  saved_revision_audit_sha256=digest(HERE/'saved_revision_audit.json'),canonical_library_audit_sha256=digest(HERE/'canonical_library_audit.json'),
                  QD_library_file=str(library),QD_library_sha256=digest(library),
                  schematic_sha256=digest(DEST/'QSTL_QD4_2SET_38PAD.SchDoc'),outjob_sha256=digest(JOB),
                  export_pascal_sha256=digest(HERE/'ExportQD90PasteAuditLinked.pas'))
    (HERE/'revision_paste_audit_source_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
