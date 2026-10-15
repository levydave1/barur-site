import sys, json, subprocess, os
from PIL import Image, ImageDraw, ImageFont
W,H=1080,1920; NAVY=(15,42,71); TQ=(79,179,162); W8=(255,255,255)
FONTS='/home/claude/pharaoh/fonts'
def font(p,s): return ImageFont.truetype(f'{FONTS}/{p}',s,layout_engine=ImageFont.Layout.RAQM)
def bb(d,t,f): return d.textbbox((0,0),t,font=f,direction='rtl',language='he')
def caption(parts,yc,path,size=66,maxw=820):
    img=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    full=''.join(t for t,_ in parts)
    while True:
        f=font('plex700.ttf',size); b=bb(d,full,f); w=b[2]-b[0]
        if w<=maxw: break
        size-=2
    px,py=40,26; h=size; x0=(W-w)//2-px; y0=int(yc-h/2-py)
    d.rounded_rectangle([x0,y0,x0+w+2*px,y0+h+2*py+8],radius=30,fill=NAVY+(225,))
    xr=(W+w)//2
    for t,c in parts:
        s=bb(d,t,f); sw=s[2]-s[0]
        d.text((xr-sw-s[0],y0+py-b[1]+4),t,font=f,fill=c,direction='rtl',language='he'); xr-=sw
    img.save(path)
# spec json: {src, out, L, caps:[[start,end,y,[[text,"w"|"t"],...]]]}
spec=json.load(open(sys.argv[1])); wd=os.path.dirname(os.path.abspath(sys.argv[1]))
ins=['-i',spec['src']]; chain=[]; L=spec['L']
pre=f"trim=end={L},setpts=PTS-STARTPTS," 
chain.append(f"[0:v]{pre}scale=1080:1920:flags=lanczos,fps=24,format=yuv420p,setsar=1,tpad=stop_mode=clone:stop_duration=1.9[v0]")
last='v0'
for i,(s,e,y,parts) in enumerate(spec['caps']):
    p=f'{wd}/cap{i}.png'; caption([(t,TQ if c=='t' else W8) for t,c in parts],y,p)
    ins+=['-i',p]; chain.append(f"[{last}][{i+1}:v]overlay=0:0:enable='between(t,{s},{e})'[c{i}]"); last=f'c{i}'
n=len(spec['caps'])
ins+=['-loop','1','-t','1.9','-framerate','24','-i','/home/claude/pharaoh/ov/slogan.png','-loop','1','-t','2.9','-framerate','24','-i','/home/claude/pharaoh/ov/endcard.png']
chain.append(f"[{n+1}:v]format=rgba,fade=in:st=0:d=0.25:alpha=1,setpts=PTS+{L}/TB[sl]")
chain.append(f"[{last}][sl]overlay=0:0:eof_action=pass,format=yuv420p,setsar=1[main]")
chain.append(f"[{n+2}:v]scale=1080:1920,fps=24,format=yuv420p,setsar=1[end]")
off=L+1.4; tot=off+2.9
chain.append(f"[main][end]xfade=transition=fade:duration=0.5:offset={off}[v]")
chain.append(f"[0:a]atrim=end={L},asetpts=PTS-STARTPTS,afade=t=out:st={L-0.3}:d=0.3,apad=whole_dur={tot}[a]")
cmd=['ffmpeg','-v','error','-y']+ins+['-filter_complex',';'.join(chain),'-map','[v]','-map','[a]','-t',str(tot),'-c:v','libx264','-preset','slow','-crf','18','-profile:v','high','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',spec['out']]
subprocess.run(cmd,check=True); print('ok',spec['out'],tot)
