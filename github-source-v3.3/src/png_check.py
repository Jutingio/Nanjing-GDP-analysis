"""Validate the actual 8-bit RGBA PNG output, including checksums and raster bytes."""
import struct,zlib
def valid_png(path,width,height):
    try:
        data=path.read_bytes()
        if data[:8]!=b'\x89PNG\r\n\x1a\n':return False
        p=8;compressed=[];ended=False;header=False
        while p<len(data):
            n=struct.unpack('>I',data[p:p+4])[0];tag=data[p+4:p+8];body=data[p+8:p+8+n]
            crc=struct.unpack('>I',data[p+8+n:p+12+n])[0]
            if len(body)!=n or zlib.crc32(tag+body)&0xffffffff!=crc:return False
            if tag==b'IHDR':
                w,h,bits,color,cmp,flt,inter=struct.unpack('>IIBBBBB',body)
                if (w,h,bits,color,cmp,flt,inter)!=(width,height,8,6,0,0,0):return False
                header=True
            if tag==b'IDAT':compressed.append(body)
            p+=12+n
            if tag==b'IEND':ended=True;break
        raw=zlib.decompress(b''.join(compressed))
        row=width*4+1
        return header and ended and p==len(data) and len(raw)==row*height and all(raw[i] in range(5) for i in range(0,len(raw),row))
    except (OSError,ValueError,struct.error,zlib.error):return False
