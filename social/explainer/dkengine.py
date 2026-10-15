"""Dka Brura explainer engine (rebuilt 15.10.2026).
Renders a 1080x1920 explainer: animated graphics + small avatar circle, all key UI inside the 4:5 safe area.
"""
import math, subprocess, json, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=1080,1920; FPS=30
SAFE_TOP,SAFE_BOT=285,1635          # 4:5 centered crop
NAVY=(15,42,71); TQ=(12,114,104); TQL=(17,151,138); TQD=(79,179,162); PAPER=(245,243,238)
STONE=(94,104,117); AMBER=(232,176,64); CORAL=(222,98,72); LINE=(220,216,207)
FD='/home/claude/pharaoh/fonts'; LOGO='/home/claude/pharaoh/logo/assets'
_fc={}
def F(size,w=700):
    k=(size,w)
    if k not in _fc: _fc[k]=ImageFont.truetype(f'{FD}/plex{w}.ttf',int(size),layout_engine=ImageFont.Layout.RAQM)
    return _fc[k]
def tb(d,t,f): return d.textbbox((0,0),t,font=f,direction='rtl',language='he')
def tw(t,f):
    d=ImageDraw.Draw(Image.new('L',(1,1))); b=tb(d,t,f); return b[2]-b[0], b
def clamp(x,a=0,b=1): return max(a,min(b,x))
def ease(x): x=clamp(x); return 1-(1-x)**3
def back(x):
    x=clamp(x); c1=1.70158; c3=c1+1; return 1+c3*(x-1)**3+c1*(x-1)**2
def prog(t,t0,dur=0.35): return clamp((t-t0)/dur)

def text_img(t,size,color,w=700,alpha=255):
    f=F(size,w); tw_,b=tw(t,f); h=int(size*1.45)
    im=Image.new('RGBA',(tw_+8,h),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.text((4-b[0],int(size*0.18)-0),t,font=f,fill=color+(alpha,),direction='rtl',language='he')
    return im
def rich_line(parts,size,w=700):
    """parts: [(text,color)] in reading order (right to left)."""
    f=F(size,w)
    adv=[f.getlength(t,direction='rtl',language='he') for t,_ in parts]
    total=int(sum(adv))+12; h=int(size*1.45)
    out=Image.new('RGBA',(total,h),(0,0,0,0)); d=ImageDraw.Draw(out); x=total-6
    for (t,c),a in zip(parts,adv):
        x-=a
        if t.strip(): d.text((x,int(size*0.18)),t,font=f,fill=c+(255,),direction='rtl',language='he')
    return out

def paste(base,im,cx,cy,scale=1.0,alpha=1.0,anchor='c'):
    if alpha<=0.01 or scale<=0.01: return
    if abs(scale-1)>0.01:
        im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.LANCZOS)
    if alpha<0.99:
        a=im.getchannel('A').point(lambda v:int(v*alpha)); im=im.copy(); im.putalpha(a)
    if anchor=='c': x=int(cx-im.width/2)
    elif anchor=='r': x=int(cx-im.width)
    else: x=int(cx)
    base.alpha_composite(im,(x,int(cy-im.height/2)))

# ---------- static assets ----------
def rounded(w,h,r,fill,outline=None,ow=0,shadow=False):
    pad=30 if shadow else 0
    im=Image.new('RGBA',(w+2*pad,h+2*pad),(0,0,0,0))
    if shadow:
        sh=Image.new('RGBA',im.size,(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle([pad,pad+10,pad+w,pad+h+10],r,fill=(20,20,19,40))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(im).rounded_rectangle([pad,pad,pad+w,pad+h],r,fill=fill,outline=outline,width=ow)
    return im

def pill(parts,size=40,bg=(255,255,255),pad=(34,16),icon=None,shadow=True,w=700):
    t=rich_line(parts,size,w); iw=0
    if icon is not None: iw=icon.width+14
    bw=t.width+2*pad[0]+iw; bh=t.height+2*pad[1]-int(size*0.2)
    im=rounded(bw,bh,bh//2,bg+(255,),shadow=shadow); p=30 if shadow else 0
    im.alpha_composite(t,(p+pad[0],p+(bh-t.height)//2+2))
    if icon is not None: im.alpha_composite(icon,(p+bw-pad[0]-icon.width,p+(bh-icon.height)//2))
    return im

def icon(name,s=64,color=NAVY,width=5):
    im=Image.new('RGBA',(s,s),(0,0,0,0)); d=ImageDraw.Draw(im); c=color+(255,); k=s/64
    def L(*pts): d.line([(x*k,y*k) for x,y in pts],fill=c,width=int(width*k*1.2),joint='curve')
    if name=='bank':
        L((8,26),(32,10),(56,26),(8,26)); L((6,56),(58,56))
        for x in (16,28,40,50): L((x,30),(x,50))
    elif name=='check':
        L((14,34),(27,46),(50,20))
    elif name=='doc':
        L((16,8),(40,8),(50,18),(50,56),(16,56),(16,8)); L((24,28),(42,28)); L((24,38),(42,38)); L((24,47),(36,47))
    elif name=='scale':
        L((32,8),(32,54)); L((18,56),(46,56)); L((10,18),(54,18)); L((10,18),(4,36),(16,36),(10,18)); L((54,18),(48,36),(60,36),(54,18))
    elif name=='shield':
        L((32,6),(54,14),(52,36),(32,58),(12,36),(10,14),(32,6))
    elif name=='ruler':
        L((8,40),(40,8),(56,24),(24,56),(8,40)); L((22,26),(28,32)); L((30,18),(36,24)); L((14,34),(20,40))
    elif name=='arrow':
        L((8,32),(54,32)); L((40,18),(54,32),(40,46))
    elif name=='hand':
        L((26,58),(18,40),(22,36),(28,42),(28,12),(34,12),(34,32),(40,30),(46,32),(52,34),(52,48),(46,58))
    elif name=='trophy':
        L((20,8),(44,8),(42,30),(32,38),(22,30),(20,8)); L((32,38),(32,48)); L((22,56),(42,56)); L((20,14),(8,14),(12,26),(22,28)); L((44,14),(56,14),(52,26),(42,28))
    elif name=='calendar':
        L((10,14),(54,14),(54,54),(10,54),(10,14)); L((10,26),(54,26)); L((22,8),(22,18)); L((42,8),(42,18))
    return im

class Header:
    def __init__(self):
        lg=Image.open(f'{LOGO}/logo-horizontal-color.png').convert('RGBA'); lw=300
        self.logo=lg.resize((lw,int(lg.height*lw/lg.width)),Image.LANCZOS)
        self.ai=text_img('נוצר באמצעות AI',24,STONE,600)
        self.name=text_img('דוד לוי',32,NAVY,700); self.title=text_img('יועץ משכנתאות',24,STONE,600)
        self.R=118; self.cx,self.cy=220,SAFE_TOP+30+self.R+8
        R=self.R; m=Image.new('L',(2*R,2*R),0); ImageDraw.Draw(m).ellipse([0,0,2*R-1,2*R-1],fill=255); self.mask=m
        ring=Image.new('RGBA',(2*R+20,2*R+20),(0,0,0,0)); ImageDraw.Draw(ring).ellipse([0,0,2*R+19,2*R+19],fill=TQL+(255,))
        self.ring=ring
    def draw(self,base,face):
        R=self.R; base.alpha_composite(self.ring,(self.cx-R-10,self.cy-R-10))
        fc=face.resize((2*R,2*R),Image.LANCZOS).convert('RGBA'); fc.putalpha(self.mask)
        base.alpha_composite(fc,(self.cx-R,self.cy-R))
        paste(base,self.name,self.cx,self.cy+R+40); paste(base,self.title,self.cx,self.cy+R+78)
        paste(base,self.logo,W-70,self.cy-22,anchor='r'); paste(base,self.ai,W-74,self.cy+62,anchor='r')

class Background:
    def __init__(self,seed=3):
        r=random.Random(seed)
        self.circles=[(1000,600,170,(243,217,160)),(-40,1050,260,(232,214,198)),(900,1450,330,(220,239,235)),(150,1700,240,(220,239,235))]
        self.ph=[r.random()*6 for _ in self.circles]
    def draw(self,t,word=None,word_alpha=1.0):
        im=Image.new('RGBA',(W,H),PAPER+(255,)); d=ImageDraw.Draw(im,'RGBA')
        for (x,y,rr,c),p in zip(self.circles,self.ph):
            dx=math.sin(t*0.35+p)*28; dy=math.cos(t*0.27+p)*22
            d.ellipse([x+dx-rr,y+dy-rr,x+dx+rr,y+dy+rr],fill=c+(150,))
        if word:
            wi=text_img(word,330,(120,120,120),700,alpha=int(26*word_alpha))
            paste(im,wi,W/2+math.sin(t*0.2)*30,1000)
        return im

def caption_img(parts,size=44):
    t=rich_line(parts,size,700); bw=t.width+56; bh=int(size*1.75)
    im=Image.new('RGBA',(bw,bh),(0,0,0,0)); ImageDraw.Draw(im).rounded_rectangle([0,0,bw-1,bh-1],14,fill=NAVY+(255,))
    im.alpha_composite(t,(28,(bh-t.height)//2+3)); return im

def whoosh(path,dur=0.45,sr=48000):
    n=int(dur*sr); rng=np.random.default_rng(1); x=rng.standard_normal(n)
    # band-pass sweep via simple moving average difference
    env=np.sin(np.linspace(0,np.pi,n))**2
    y=np.convolve(x,np.ones(40)/40,'same')-np.convolve(x,np.ones(400)/400,'same')
    y=y/np.abs(y).max()*env*0.35
    import wave
    with wave.open(path,'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((y*32767).astype(np.int16).tobytes())

def read_frames(src,crop,size=240):
    x,y,s=crop
    p=subprocess.Popen(['ffmpeg','-v','error','-i',src,'-vf',f'fps={FPS},crop={s}:{s}:{x}:{y},scale={size}:{size}','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    while True:
        b=p.stdout.read(size*size*3)
        if len(b)<size*size*3: break
        yield Image.frombytes('RGB',(size,size),b)
