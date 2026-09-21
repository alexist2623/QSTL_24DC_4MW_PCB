"""Compare full text records while ignoring bytes after fixed-string terminators."""
import struct

def text_fingerprint(data):
    rows=[];pos=0
    while pos<len(data):
        assert data[pos]==5
        size=struct.unpack_from('<I',data,pos+1)[0]&0xffffff
        body=bytearray(data[pos+5:pos+5+size]);pos+=5+size
        length=struct.unpack_from('<I',data,pos)[0]&0xffffff
        text=data[pos+4:pos+4+length];pos+=4+length
        # Native FontName and BarCodeFontName are 32 UTF-16 code-unit slots.
        # Save clears unused storage after the first NUL, without changing the
        # logical names. Native AuditText.pas independently checks both fonts.
        for start in (46,161):
            assert len(body)>=start+64
            end=next(i for i in range(start,start+64,2) if body[i:i+2]==b'\0\0')+2
            body[end:start+64]=b'\0'*(start+64-end)
        rows.append(bytes(body)+text)
    assert pos==len(data)
    return rows
