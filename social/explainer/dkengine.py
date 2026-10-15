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
        paste(base,self.logo,W-70,self.cy,anchor='r')

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

# ---------- extra line icons (16.10 batch) ----------
def icon2(name,s=64,color=NAVY,width=5):
    base=icon(name,s,color,width)
    if base.getbbox(): return base
    im=Image.new('RGBA',(s,s),(0,0,0,0)); d=ImageDraw.Draw(im); c=color+(255,); k=s/64; lw=int(width*k*1.2)
    def L(*pts): d.line([(x*k,y*k) for x,y in pts],fill=c,width=lw,joint='curve')
    def O(x0,y0,x1,y1): d.ellipse([x0*k,y0*k,x1*k,y1*k],outline=c,width=lw)
    def A(x0,y0,x1,y1,a0,a1): d.arc([x0*k,y0*k,x1*k,y1*k],a0,a1,fill=c,width=lw)
    if name=='coin': O(10,10,54,54); L((32,20),(32,44)); L((24,26),(38,26)); L((26,38),(40,38))
    elif name=='house': L((8,30),(32,10),(56,30)); L((14,26),(14,56),(50,56),(50,26)); L((26,56),(26,40),(38,40),(38,56))
    elif name=='key': O(6,18,30,42); L((30,30),(58,30)); L((48,30),(48,40)); L((56,30),(56,38))
    elif name=='up': L((8,52),(24,36),(36,44),(56,16)); L((42,16),(56,16),(56,30))
    elif name=='down': L((8,14),(24,30),(36,22),(56,50)); L((42,50),(56,50),(56,36))
    elif name=='bell': L((14,46),(18,40),(18,26)); A(18,10,46,42,180,360); L((46,26),(46,40),(50,46),(14,46)); L((28,52),(36,52))
    elif name=='clock': O(8,8,56,56); L((32,18),(32,32),(42,40))
    elif name=='lock': L((12,28),(52,28),(52,58),(12,58),(12,28)); A(20,8,44,40,180,360); L((32,40),(32,48))
    elif name=='unlock': L((12,28),(52,28),(52,58),(12,58),(12,28)); A(30,6,54,38,180,330); L((32,40),(32,48))
    elif name=='chat': L((8,10),(56,10),(56,42),(26,42),(14,54),(16,42),(8,42),(8,10)); L((18,22),(46,22)); L((18,31),(38,31))
    elif name=='share': O(40,6,56,22); O(40,42,56,58); O(6,24,22,40); L((22,28),(40,18)); L((22,36),(40,46))
    elif name=='truck': L((6,16),(38,16),(38,46),(6,46),(6,16)); L((38,26),(50,26),(58,36),(58,46),(38,46)); O(10,42,22,54); O(42,42,54,54)
    elif name=='hammer': L((14,56),(38,32)); L((30,16),(46,8),(58,20),(50,36),(30,16))
    elif name=='percent': L((50,12),(14,52)); O(8,8,24,24); O(40,40,56,56)
    elif name=='building': L((14,58),(14,8),(42,8),(42,58)); L((42,24),(54,24),(54,58)); L((6,58),(58,58))
    elif name=='crane': L((16,58),(16,8)); L((8,14),(56,14)); L((16,8),(30,14)); L((48,14),(48,32)); L((42,32),(54,32),(54,40),(42,40),(42,32)); L((8,58),(26,58))
    elif name=='people': O(10,10,26,26); O(38,10,54,26); A(4,32,32,62,180,360); A(32,32,60,62,180,360)
    elif name=='warning': L((32,6),(60,56),(4,56),(32,6)); L((32,24),(32,40)); L((32,47),(32,49))
    elif name=='calc': L((12,6),(52,6),(52,58),(12,58),(12,6)); L((20,14),(44,14),(44,24),(20,24),(20,14)); L((20,34),(22,34)); L((31,34),(33,34)); L((42,34),(44,34)); L((20,46),(22,46)); L((31,46),(33,46)); L((42,46),(44,46))
    elif name=='mail': L((6,14),(58,14),(58,50),(6,50),(6,14)); L((6,14),(32,34),(58,14))
    elif name=='drawer': L((8,10),(56,10),(56,56),(8,56),(8,10)); L((8,33),(56,33)); L((26,22),(38,22)); L((26,45),(38,45))
    elif name=='gift': L((8,24),(56,24),(56,34),(8,34),(8,24)); L((12,34),(12,58),(52,58),(52,34)); L((32,24),(32,58)); A(18,10,32,26,180,0); A(32,10,46,26,180,0)
    elif name=='flag': L((14,58),(14,8)); L((14,10),(50,10),(42,22),(50,34),(14,34))
    elif name=='stamp': L((24,8),(40,8),(36,30),(28,30),(24,8)); L((10,30),(54,30),(54,44),(10,44),(10,30)); L((10,54),(54,54))
    elif name=='x': L((14,14),(50,50)); L((50,14),(14,50))
    elif name=='wallet': L((8,18),(52,18),(52,56),(8,56),(8,18)); L((8,18),(44,8),(48,18)); L((38,32),(58,32),(58,44),(38,44),(38,32))
    elif name=='bulb': A(14,6,50,42,140,40); L((24,40),(24,50),(40,50),(40,40)); L((26,56),(38,56))
    return im
