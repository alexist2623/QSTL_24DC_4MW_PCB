"""Readable review rendering from saved SchDoc primitives, not an Altium export."""
from pathlib import Path
import argparse,json,sys
from PIL import Image,ImageDraw,ImageFont
from validate_v2_schematic import blocks,props,olefile,ROOT,P,sha

def render(doc,destination):
    with olefile.OleFileIO(doc) as o:rows=[props(b) for f,b in blocks(o.openstream('FileHeader').read())]
    scale=3;width=1500;height=1000;margin=45
    im=Image.new('RGB',((width+2*margin)*scale,(height+2*margin)*scale),'white');draw=ImageDraw.Draw(im)
    fonts={s:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',s*scale) for s in (7,8,9,10,12)}
    blue='#274977';red='#9c2235';green='#16724e';gray='#697482'
    def xy(x,y):return (round((float(x)+margin)*scale),round((height-float(y)+margin)*scale))
    def pos(r,prefix='Location.'):return float(r.get(prefix+'X',0)),float(r.get(prefix+'Y',0))
    def line(a,b,color=blue,weight=1):draw.line([xy(*a),xy(*b)],fill=color,width=max(1,round(weight*scale)))
    def text(x,y,value,size=8,color=blue,anchor='la',rotation=0):
        if not rotation:draw.text(xy(x,y),value,font=fonts[size],fill=color,anchor=anchor)
        else:
            font=fonts[size];box=font.getbbox(value);layer=Image.new('RGBA',(box[2]-box[0]+8,box[3]-box[1]+8));ld=ImageDraw.Draw(layer);ld.text((4-box[0],4-box[1]),value,font=font,fill=color)
            layer=layer.rotate(rotation,expand=True);px,py=xy(x,y)
            im.paste(layer,(int(px-layer.width/2),int(py-layer.height if anchor=='la' else py)),layer)
    draw.rectangle([xy(20,980),xy(1480,20)],outline='#d5dbe1',width=2)
    for r in rows:
        if r.get('RECORD')=='14':
            x,y=pos(r);xx,yy=pos(r,'Corner.');p1,p2=xy(min(x,xx),max(y,yy)),xy(max(x,xx),min(y,yy))
            draw.rectangle([p1,p2],fill='#f1f5fb' if r.get('IsSolid')=='T' else None,outline=blue,width=3)
        elif r.get('RECORD')=='13':line(pos(r),pos(r,'Corner.'),blue,1.6)
    for r in rows:
        if r.get('RECORD')=='27':
            pp=[(r['X'+str(i)],r['Y'+str(i)]) for i in range(1,int(r['LocationCount'])+1)]
            for a,b in zip(pp,pp[1:]):line(a,b,green,.65)
        elif r.get('RECORD')=='2':
            x,y=pos(r);d=int(r.get('PinConglomerate',0))&3;dx,dy=((1,0),(0,1),(-1,0),(0,-1))[d];length=int(r['PinLength']);ex,ey=x+dx*length,y+dy*length
            line((x,y),(ex,ey),blue,.65)
            if d in (0,2):
                text((x+ex)/2,y+1,r['Designator'],7,anchor='mb')
                text(x-dx*3,y,r['Name'],7,anchor='rm' if d==0 else 'lm')
            else:
                text(x+1,(y+ey)/2,r['Designator'],7,anchor='la',rotation=90)
                text(x,y-dy*4,r['Name'],7,anchor='la' if d==3 else 'ra',rotation=90)
        elif r.get('RECORD')=='22':
            x,y=pos(r);line((x-2,y-2),(x+2,y+2),red,.6);line((x-2,y+2),(x+2,y-2),red,.6)
    for r in rows:
        typ=r.get('RECORD')
        if typ=='25':
            x,y=pos(r);vertical=int(r.get('Orientation',0))%2==1
            text(x,y+1,r['Text'],8,green,anchor=('la' if r.get('Justification')=='0' else 'ra') if vertical else ('lb' if r.get('Justification')=='0' else 'rb'),rotation=90 if vertical else 0)
        elif typ=='34':text(*pos(r),r['Text'],10,color=red,anchor='lb')
        elif typ in ('4','41') and r.get('IsHidden')!='T' and 'Text' in r and (typ=='4' or r.get('Name')=='Comment'):
            text(*pos(r),r['Text'],8,color=gray,anchor='lb')
    text(35,12,'Saved native schematic review | 16 components / 123 symbol pins / 33 named nets / 31 intentional NC | PCB adds6 standalone GND mounting pads',7,color=gray,anchor='lb')
    destination.parent.mkdir(parents=True,exist_ok=True);im.save(destination)
    provenance={'source':str(doc),'source_sha256':sha(doc),'output':str(destination),'renderer':'Read-only native SchDoc primitive renderer; not an Altium screenshot','size':list(im.size)}
    (P/'schematic_preview_provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(provenance))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--doc',type=Path,required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args();render(args.doc.resolve(),args.output.resolve())
