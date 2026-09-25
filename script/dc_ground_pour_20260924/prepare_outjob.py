"""Reuse the original project's native CAM settings in a reproducible OutJob."""
from pathlib import Path
import configparser

H = Path(__file__).resolve().parent
P = H.parents[1] / 'QSTL_24DC_4MW_PCB'
cfg = configparser.ConfigParser(interpolation=None, strict=False)
cfg.optionxform = str
cfg.read(P / 'QSTL_24DC_4MW_PCB.PrjPcb', encoding='utf-8-sig')
src = cfg['OutputGroup5']
out = configparser.ConfigParser(interpolation=None)
out.optionxform = str
out['OutputJobFile'] = {'Version':'1.0', 'Caption':'HDI fabrication',
    'Description':'Six copper layers, masks, silkscreen, outline, bottom blind pocket, and separate laser/PTH drills'}
g = {'Name':'HDI fabrication', 'TargetOutputMedium':'CAM', 'VariantName':'[No Variations]',
     'VariantScope':'0', 'OutputMedium1':'CAM', 'OutputMedium1_Type':'GeneratedFiles'}
for dest, original in ((1,12),(2,8)):
    for stem in ('OutputType','OutputName','OutputVariantName','OutputDefault'):
        g[f'{stem}{dest}'] = src[f'{stem}{original}']
    g[f'OutputDocumentPath{dest}'] = 'QSTL_24DC_4MW_PCB.PcbDoc'
    g[f'OutputCategory{dest}'] = 'Fabrication'
    g[f'OutputEnabled{dest}'] = '1'
    g[f'OutputEnabled{dest}_OutputMedium1'] = str(dest)
    for key,value in src.items():
        prefix = f'Configuration{original}_'
        if key.startswith(prefix):
            g[f'Configuration{dest}_' + key[len(prefix):]] = value
out['OutputGroup1'] = g
cam = str(P / 'fabrication/JLCPCB_HDI_20260924/Native_CAM')
out['PublishSettings'] = {'OutputFilePath1':cam+'\\', 'ReleaseManaged1':'0',
    'OutputBasePath1':cam, 'OutputPathMedia1':'', 'OutputPathOutputer1':'',
    'OutputFileName1':'', 'UseOutputNameForMulti1':'0', 'OpenOutput1':'0', 'PromptOverwrite1':'0'}
out['GeneratedFilesSettings'] = {'RelativeOutputPath1':cam+'\\', 'OpenOutputs1':'0',
    'AddToProject1':'0', 'TimestampFolder1':'0', 'UseOutputName1':'0',
    'OpenODBOutput1':'0', 'OpenGerberOutput1':'0', 'OpenNCDrillOutput1':'0',
    'OpenIPCOutput1':'0', 'EnableReload1':'0'}
target=P/'HDI_Fabrication.OutJob'
with target.open('w', encoding='utf-8', newline='\r\n') as f:
    out.write(f, space_around_delimiters=False)
Path(cam).mkdir(parents=True, exist_ok=True)
print(target)
