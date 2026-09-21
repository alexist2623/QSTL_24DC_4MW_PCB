from pathlib import Path
H=Path(__file__).resolve().parent;W=H.parent/'_support';OLD=W/'dc_direct_20260920'
s=(OLD/'render_rf_only.py').read_text(encoding='utf-8').replace('range(1, 5)','range(1, 7)').replace('range(1,5)','range(1,7)')
s=s.replace("assert len(tracks) == 19 and len(arcs) == 11","assert len(tracks) == 30 and len(arcs) == 18")
s=s.replace("'MW4': '24'}","'MW4': '24', 'MW5':'12', 'MW6':'18'}")
s=s.replace("HEIGHT = BOTTOM + 117","HEIGHT = BOTTOM + 190")
s=s.replace("4: '#69d4bd'","4: '#69d4bd', 5:'#ba9df5', 6:'#f88f76'")
s=s.replace("'RF 주 경로에 R 패드를 배치'","'R/C 안쪽 재배치 · RF 6채널'")
# Show connector ground pads as neutral context.
a=s.index('# QD\'s native lands')
s=s[:a]+"for p in n['pads']:\n    if p['component'] and p['component'].startswith('SMP') and p['number']!='1' and YMIN<p['y']<YMAX:\n        rectpad(p,'#334650')\n        circle(p['x'],p['y'],p['hole']/2,'#101820')\n\n"+s[a:]
a=s.index('labels = [');b=s.index("text(MARGIN, BOTTOM+23",a)
s=s[:a]+'''labels = [
 (3.1,49.9,'SMP4',4),(16.4,49.9,'SMP3',3),
 (7.35,48.7,'C4',4),(12.15,48.7,'C3',3),
 (6.7,47.25,'R4',4),(12.8,47.25,'R3',3),
 (16.4,33.15,'SMP2',2),(3.1,33.15,'SMP6',6),
 (16.9,39.5,'C2',2),(17.9,42.4,'R2',2),
 (2.55,39.2,'C6',6),(1.75,41.8,'R6',6),
 (16.4,26.0,'SMP1',1),(3.1,26.0,'SMP5',5),
 (12.6,28.1,'C1',1),(6.9,28.1,'C5',5),
 (15.6,31.3,'R1',1),(3.9,31.3,'R5',5),
 (8.05,44.25,'24',4),(11.45,44.25,'1',3),
 (11.30,42.15,'6',2),(13.1,39.45,'9',1),
 (10.1,40.75,'12',5),(8.2,41.45,'18',6),
]
for x,y,t,ch in labels:label(x,y,t,colors[ch],21 if t.startswith('SMP') else 19)
for ch in range(1,7):
    col=(ch-1)%3;row=(ch-1)//3
    text(MARGIN+col*405,BOTTOM+20+row*31,f'SMP{ch} → C{ch}/R{ch} → QD {expected[f"MW{ch}"]}',18,colors[ch],True)

'''+s[b:]
s=s.replace('BOTTOM+23','BOTTOM+94').replace('BOTTOM+57','BOTTOM+130')
s=s.replace('R–C 패드 간격 약 0.21 mm.','R/C 패드 중심 비아 적용.')
(H/'render_rf_only.py').write_text(s,encoding='utf-8')
print('Prepared six-channel saved-native RF render.')
