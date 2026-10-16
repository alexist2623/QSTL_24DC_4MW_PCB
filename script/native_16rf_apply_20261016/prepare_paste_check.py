"""Prepare a temporary native paste export for saved-board verification."""
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
old=ROOT/'script/l3_l4_swap_apply_20261014'
text=(old/'paste_verification/Cap_Paste_Verification.OutJob').read_text(encoding='cp1252')
text=text.replace(str(old),str(H))
text=text.replace(str(ROOT/'QSTL_24DC_4MW_PCB'),str(ROOT/'QSTL_QD4_2SET_38PAD'))
text=text.replace('QSTL_24DC_4MW_PCB.PcbDoc','QSTL_QD4_2SET_38PAD.PcbDoc')
(H/'paste_verification/Native_CAM').mkdir(parents=True,exist_ok=True)
(H/'paste_verification/Cap_Paste_Verification.OutJob').write_text(text,encoding='cp1252')
pas=(old/'ExportCapPaste.pas').read_text().replace(str(old),str(H))
pas=pas.replace(str(ROOT/'QSTL_24DC_4MW_PCB'),str(ROOT/'QSTL_QD4_2SET_38PAD'))
pas=pas.replace('QSTL_24DC_4MW_PCB.PrjPcb','QSTL_QD4_2SET_38PAD.PrjPcb').replace('QSTL_24DC_4MW_PCB.PcbDoc','QSTL_QD4_2SET_38PAD.PcbDoc')
pas=pas.replace("WS.DM_OpenProject('"+str(ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PrjPcb')+"',True);",'')
(H/'ExportCapPaste.pas').write_text(pas,encoding='ascii')
(H/'ExportCapPaste.PrjScr').write_text((old/'ExportCapPaste.PrjScr').read_text())
print(H/'paste_verification/Cap_Paste_Verification.OutJob')
