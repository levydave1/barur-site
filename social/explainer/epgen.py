"""Spec-driven Dka Brura episode renderer (16.10.2026).
Usage: python3 -I epgen.py <spec_module_name> [out.mp4]      env PREVIEW=t1,t2 renders stills.
A spec module (specs/epNN.py) defines: NUM, RAW, WORDS, HL (highlight words), SCENES, END_FROM (anchor of the closing scene).
Anchors are words as spoken ("למחזר", "שלכם#2" = 2nd occurrence) or int word indexes.
Markup in texts: *x* = teal, ~x~ = coral, plain = navy.
"""
import sys, json, math, random, subprocess, os, re, importlib
sys.path.insert(0,'/home/claude/dk'); sys.path.insert(0,'/home/claude/dk/specs')
from dkengine import *

PUNCT=',.?:!;"\'״׳…-–'
def norm(w): return w.strip().strip(PUNCT).strip()

SCRIPTS=json.load(open('/home/claude/dk/batch/scripts.json'))
def align(ww,num):
    """Put the approved script text on Whisper's timings (Whisper sometimes mishears)."""
    import difflib
    txt=SCRIPTS.get(str(num))
    if not txt: return ww
    toks=txt.replace('״','"').split(); toks=[t.replace('"','״') for t in toks]
    A=[norm(t) for t in toks]; B=[norm(w['w']) for w in ww]
    out=[None]*len(toks)
    sm=difflib.SequenceMatcher(None,A,B,autojunk=False)
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal':
            for k in range(i2-i1): out[i1+k]=(ww[j1+k]['s'],ww[j1+k]['e'])
        elif tag=='replace' and j2>j1:
            s0,e0=ww[j1]['s'],ww[j2-1]['e']; L=[len(t)+1 for t in toks[i1:i2]]; tot=sum(L); acc=0
            for k in range(i2-i1):
                a=s0+(e0-s0)*acc/tot; acc+=L[k]; out[i1+k]=(a,s0+(e0-s0)*acc/tot)
    for i in range(len(out)):   # fill inserts
        if out[i] is None:
            j=i
            while j<len(out) and out[j] is None: j+=1
            s0=out[i-1][1] if i>0 else 0.0; e0=out[j][0] if j<len(out) else ww[-1]['e']
            n=j-i
            for k in range(n): out[i+k]=(s0+(e0-s0)*k/n,s0+(e0-s0)*(k+1)/n)
    return [{'w':t,'s':a,'e':b} for t,(a,b) in zip(toks,out)]

class Ep:
    def __init__(self,spec):
        self.sp=spec
        self.words=align(json.load(open(spec.WORDS))['words'],spec.NUM)
        self.N=[norm(w['w']) for w in self.words]
        self.end=self.words[-1]['e']; self.HOLD=self.end+0.9; self.TOTAL=self.HOLD+1.7
    def idx(self,a):
        if isinstance(a,int): return a
        w,_,n=a.partition('#'); n=int(n or 1); c=0
        for i,x in enumerate(self.N):
            if x==w or (len(w)>2 and x.endswith(w) and len(x)-len(w)<=2):
                c+=1
                if c==n: return i
        raise KeyError(f'anchor {a!r} not in: {" ".join(self.N)}')
    def S(self,a): return self.words[self.idx(a)]['s']
    def E(self,a): return self.words[self.idx(a)]['e']

def parts_of(txt,base=NAVY):
    out=[]
    for m in re.finditer(r'\*([^*]+)\*|~([^~]+)~|([^*~]+)',txt):
        if m.group(1): out.append((m.group(1),TQ))
        elif m.group(2): out.append((m.group(2),CORAL))
        else: out.append((m.group(3),base))
    return out
def fit(im,maxw=W-110): return min(1.0,maxw/im.width)

# ---------------- element renderers ----------------
_cache={}
def C(key,fn):
    if key not in _cache: _cache[key]=fn()
    return _cache[key]

def el_head(ep,base,t,a,txt,size=96,y=760):
    p=prog(t,ep.S(a),0.35)
    if p<=0: return
    im=C(('h',txt,size),lambda:rich_line(parts_of(txt),size,700)); s=fit(im)
    paste(base,im,W/2,y,scale=s*(0.7+0.3*back(p)),alpha=ease(p))
def el_lines(ep,base,t,items,y0=900,gap=110):
    for i,it in enumerate(items):
        a,txt,size=it[0],it[1],(it[2] if len(it)>2 else 64)
        p=prog(t,ep.S(a),0.35)
        if p<=0: continue
        im=C(('l',txt,size),lambda:rich_line(parts_of(txt),size,700)); s=fit(im)
        paste(base,im,W/2,y0+i*gap+20*(1-ease(p)),scale=s,alpha=ease(p))
def el_title(ep,base,t,a,txt,ic='bank',color=NAVY,y=720):
    p=prog(t,ep.S(a),0.4)
    if p<=0: return
    def mk():
        im=rich_line(parts_of(txt),72,700); i2=icon2(ic,70,color,5)
        row=Image.new('RGBA',(im.width+i2.width+20,max(im.height,i2.height)),(0,0,0,0))
        row.alpha_composite(im,(0,(row.height-im.height)//2)); row.alpha_composite(i2,(im.width+20,(row.height-i2.height)//2)); return row
    row=C(('t',txt,ic,color),mk); paste(base,row,W/2,y+30*(1-ease(p)),scale=fit(row),alpha=ease(p))
def chip_img(txt,ic=None,color=NAVY,size=48):
    i2=icon2(ic,44,TQ if color==NAVY else color,6 if ic=='check' else 5) if ic else None
    return pill(parts_of(txt,color),size,icon=i2,pad=(40,20))
def el_chips(ep,base,t,items,y0=880,gap=135,mode='slide'):
    for i,it in enumerate(items):
        a,txt=it[0],it[1]; ic=it[2] if len(it)>2 else None; col=it[3] if len(it)>3 else NAVY
        p=prog(t,ep.S(a),0.35)
        if p<=0: continue
        im=C(('c',txt,ic,col),lambda:chip_img(txt,ic,col))
        if mode=='slide': paste(base,im,W/2+(1-ease(p))*60,y0+i*gap,scale=fit(im),alpha=ease(p))
        else: paste(base,im,W/2,y0+i*gap,scale=fit(im)*(0.8+0.2*back(p)),alpha=ease(p))
def el_grid(ep,base,t,items,y0=800,gap=122,cols=2):
    """small pills in a grid, right-to-left fill"""
    cw=W/cols
    for i,it in enumerate(items):
        a,txt=it[0],it[1]; ic=it[2] if len(it)>2 else 'coin'
        p=prog(t,ep.S(a),0.3)
        if p<=0: continue
        im=C(('g',txt,ic),lambda:pill(parts_of(txt),46,icon=icon2(ic,42,TQ,5),pad=(32,18)))
        r,c=divmod(i,cols); x=W-cw/2-c*cw; y=y0+r*gap
        paste(base,im,x,y-30*(1-ease(p)),scale=min(fit(im,cw-30),1)*(0.7+0.3*back(p)),alpha=ease(p))
def card_img(label,ic,hl=False,w=340,h=300,col=None):
    im=rounded(w,h,32,(255,255,255,255),shadow=True); p=30; c=col or (TQ if hl else NAVY)
    i2=icon2(ic,120,c,5); im.alpha_composite(i2,(p+(w-i2.width)//2,p+40))
    lt=rich_line(parts_of(label,c),42,700); s=min(1,(w-30)/lt.width)
    if s<1: lt=lt.resize((int(lt.width*s),int(lt.height*s)),Image.LANCZOS)
    im.alpha_composite(lt,(p+(w-lt.width)//2,p+h-95+int((1-s)*20))); return im
def el_cards(ep,base,t,items,y=1060,mid=None,mid_at=None):
    n=len(items); xs=[W/2] if n==1 else ([W/2+225,W/2-225] if n==2 else [W/2+330,W/2,W/2-330])
    for (it,x) in zip(items,xs):
        a,label,ic=it[0],it[1],it[2]; hl=it[3] if len(it)>3 else False; col=it[4] if len(it)>4 else None
        p=prog(t,ep.S(a),0.35)
        if p<=0: continue
        w=300 if n==3 else 340
        im=C(('k',label,ic,hl,col,w),lambda:card_img(label,ic,hl,w,300,col))
        paste(base,im,x,y+40*(1-ease(p)),scale=0.8+0.2*back(p),alpha=ease(p))
    if mid and mid_at is not None:
        p=prog(t,ep.S(mid_at),0.3); im=C(('m',mid),lambda:text_img(mid,60,STONE,700)); paste(base,im,W/2,y,scale=back(p),alpha=ease(p))
def el_balance(ep,base,t,a,right,left,tilts,y=1080,ic_r=None,ic_l=None):
    """beam with two pans. tilts=[(anchor,deg)] ; positive deg = right side down"""
    p=prog(t,ep.S(a),0.4)
    if p<=0: return
    ang=0.0
    for an,dg in tilts:
        q=ease(prog(t,ep.S(an),0.6)); ang=ang+(dg-ang)*q
    ang+=math.sin(t*2.2)*1.2*(1 if p>=1 else 0)
    L_=330; r=math.radians(ang); cx,cy=W/2,y-120
    d=ImageDraw.Draw(base,'RGBA'); al=int(255*ease(p))
    d.polygon([(cx,cy),(cx-40,y+120),(cx+40,y+120)],fill=NAVY+(al,))
    xr,yr=cx+L_*math.cos(r),cy+L_*math.sin(r); xl,yl=cx-L_*math.cos(r),cy-L_*math.sin(r)
    d.line([(xl,yl),(xr,yr)],fill=NAVY+(al,),width=12); d.ellipse([cx-16,cy-16,cx+16,cy+16],fill=TQ+(al,))
    for (x,yy),lab,ic,col in (((xr,yr),right,ic_r,TQ),((xl,yl),left,ic_l,CORAL)):
        d.line([(x,yy),(x-60,yy+90)],fill=STONE+(al,),width=4); d.line([(x,yy),(x+60,yy+90)],fill=STONE+(al,),width=4)
        d.chord([x-110,yy+40,x+110,yy+150],0,180,fill=(255,255,255,al),outline=NAVY+(al,),width=5)
        im=C(('b',lab,ic,col),lambda:pill(parts_of(lab),44,icon=icon2(ic,40,col,5) if ic else None,pad=(28,16)))
        paste(base,im,x,yy+165,scale=fit(im,470),alpha=ease(p))
def el_timeline(ep,base,t,items,y=1000,line_at=None):
    """horizontal RTL timeline. items=[(anchor,label,icon)]"""
    n=len(items); x0,x1=W-110,110
    p=prog(t,ep.S(line_at if line_at is not None else items[0][0]),0.6)
    if p<=0: return
    d=ImageDraw.Draw(base,'RGBA'); xe=x0-(x0-x1)*ease(p)
    d.line([(x0,y),(xe,y)],fill=NAVY+(255,),width=8)
    d.polygon([(xe-22,y),(xe+2,y-16),(xe+2,y+16)],fill=NAVY+(255,))
    for i,it in enumerate(items):
        a,lab=it[0],it[1]; ic=it[2] if len(it)>2 else None
        q=prog(t,ep.S(a),0.35)
        if q<=0: continue
        x=x0-60-(x0-x1-120)*(i/(max(1,n-1)))
        rr=24*back(q); d.ellipse([x-rr,y-rr,x+rr,y+rr],fill=TQ+(255,),outline=(255,255,255,255),width=5)
        im=C(('tl',lab),lambda:rich_line(parts_of(lab),40,700))
        up=(i%2==0); yy=y-90 if up else y+90
        paste(base,im,x,yy+(20 if up else -20)*(1-ease(q)),scale=fit(im,330),alpha=ease(q))
        if ic:
            ii=C(('ti',ic),lambda:icon2(ic,70,TQ,5)); paste(base,ii,x,(y-180 if up else y+180),alpha=ease(q))
def el_meter(ep,base,t,a,label,frm,to,b,y=1100,color=CORAL,ic='up'):
    """vertical-ish bar that grows from frm to to between anchors a..b"""
    p=prog(t,ep.S(a),0.35)
    if p<=0: return
    g=ease(prog(t,ep.S(a),max(0.5,ep.S(b)-ep.S(a))))
    v=frm+(to-frm)*g; bw=640; bh=70; x0=W/2-bw/2
    d=ImageDraw.Draw(base,'RGBA'); al=int(255*ease(p))
    d.rounded_rectangle([x0,y-bh/2,x0+bw,y+bh/2],35,fill=(255,255,255,al),outline=LINE+(al,),width=3)
    fw=max(bh,bw*v); d.rounded_rectangle([x0+bw-fw,y-bh/2,x0+bw,y+bh/2],35,fill=color+(al,))
    im=C(('mt',label,ic,color),lambda:pill(parts_of(label),40,icon=icon2(ic,40,color,5),pad=(28,14),shadow=False,bg=PAPER))
    paste(base,im,W/2,y-95,alpha=ease(p))
def el_icon(ep,base,t,a,ic,x=W/2,y=1000,size=150,color=TQ,until=None,pulse=False):
    p=prog(t,ep.S(a),0.4)
    if p<=0: return
    q=1-ease(prog(t,ep.S(until),0.3)) if until is not None else 1
    s=1+(0.05*math.sin(t*6) if pulse else 0)
    im=C(('ic',ic,size,color),lambda:icon2(ic,size,color,5)); paste(base,im,x,y,scale=s*(0.6+0.4*back(p)),alpha=ease(p)*q)
def el_strike(ep,base,t,a,y,w=520,color=CORAL):
    p=ease(prog(t,ep.S(a),0.35))
    if p<=0: return
    d=ImageDraw.Draw(base,'RGBA'); d.line([(W/2+w/2,y),(W/2+w/2-w*p,y)],fill=color+(230,),width=10)
random.seed(4); CONF=[(random.uniform(-1,1),random.uniform(-1.2,-0.3),random.choice([TQL,AMBER,CORAL,NAVY])) for _ in range(60)]
def el_confetti(ep,base,t,a,y=1060):
    tc=t-ep.S(a)
    if 0<tc<1.6:
        d=ImageDraw.Draw(base,'RGBA')
        for vx,vy,c in CONF:
            x=W/2+vx*520*tc; yy=y+vy*700*tc+600*tc*tc; al=int(255*clamp(1-tc/1.6))
            d.rounded_rectangle([x-9,yy-5,x+9,yy+5],3,fill=c+(al,))
def el_bubble(ep,base,t,a,txt,y=760):
    p=prog(t,ep.S(a),0.35)
    if p<=0: return
    im=C(('bb',txt),lambda:pill(parts_of(txt),50,icon=icon2('chat',48,TQ,5),pad=(44,22)))
    paste(base,im,W/2,y+30*(1-ease(p)),scale=fit(im)*(0.7+0.3*back(p)),alpha=ease(p))

EL={'head':el_head,'lines':el_lines,'title':el_title,'chips':el_chips,'grid':el_grid,'cards':el_cards,'balance':el_balance,
    'timeline':el_timeline,'meter':el_meter,'icon':el_icon,'strike':el_strike,'confetti':el_confetti,'bubble':el_bubble}

# ---------------- closing scene (auto) ----------------
FOLLOW=pill([("+ עקבו",(255,255,255))],58,bg=NAVY,pad=(56,24)); HAND=icon('hand',90,NAVY,5)
SHARE=pill([("שתפו",NAVY)],44,icon=icon2('share',42,TQ,5),pad=(36,18))
def wrap(words,maxc=22):
    lines=[[]]; n=0
    for i,w in words:
        if n+len(w)>maxc and lines[-1]: lines.append([]); n=0
        lines[-1].append((i,w)); n+=len(w)+1
    return lines
def closing(ep):
    N=ep.N; ws=[w['w'] for w in ep.words]
    def find(cands,start):
        for i in range(start,len(N)):
            if N[i] in cands: return i
        return None
    st=ep.idx(ep.sp.END_FROM)
    i_cm=find({'תכתבו'},st); i_fo=find({'תעקבו','ותעקבו'},st); i_sh=find({'ותשלחו','תשלחו','שתפו'},st)
    i_tm=find({'ומחר'},st)
    i_tz=i_tm+1 if i_tm is not None and N[i_tm]=='ומחר' else None
    if i_tz is None:  # "ומחר אני עונה..." variants
        i_tm=find({'ומחר'},st); i_tz=i_tm+1
    sub=[(i,ws[i]) for i in range(i_fo+1,i_tm) if i!=i_tm] if i_fo is not None else []
    # drop the share sentence from the subline if share pill shown
    teaser=[(i,ws[i].rstrip(':')) for i in range(i_tz,len(ws))]
    return dict(cm=i_cm,fo=i_fo,sh=i_sh,tm=i_tm,sub=sub,tz=teaser,start=ep.S(st))
def draw_closing(ep,cl,base,t):
    y=760
    if cl['cm'] is not None:
        el_bubble(ep,base,t,cl['cm'],'תכתבו *בתגובות*',y=720); y=870
    p=prog(t,ep.words[cl['fo']]['s'],0.35); paste(base,FOLLOW,W/2,y,scale=0.6+0.4*back(p),alpha=ease(p))
    if p>0.5:
        tap=(math.sin(t*5)+1)/2; paste(base,HAND,W/2+175,y+55+14*tap,alpha=ease(prog(t,ep.words[cl['fo']]['s']+0.2,0.3)))
    y2=y+175
    if cl['sh'] is not None and cl['sh']>cl['fo']:
        q=prog(t,ep.words[cl['sh']]['s'],0.35); paste(base,SHARE,W/2,y2,scale=0.7+0.3*back(q),alpha=ease(q)); y2+=95
    elif cl['sub']:
        for ln in wrap(cl['sub'],30):
            txt=' '.join(w for _,w in ln).strip().rstrip('.')
            q=prog(t,ep.words[ln[0][0]]['s'],0.4)
            im=C(('sub',txt),lambda:text_img(txt,44,STONE,600)); paste(base,im,W/2,y2,scale=fit(im),alpha=ease(q)); y2+=68
        y2+=12
    # teaser card
    pc=prog(t,ep.words[cl['tm']]['s'],0.4)
    if pc>0:
        lines=wrap(cl['tz'],24); cw=880; chh=110+62*len(lines)
        cd=rounded(cw,chh,26,(255,255,255,255),shadow=True); dd=ImageDraw.Draw(cd)
        dd.rectangle([30+cw-10,30,30+cw,30+chh],fill=AMBER+(255,))
        lab=C(('lab',),lambda:text_img('מחר בדקה ברורה',34,AMBER,700)); cd.alpha_composite(lab,(30+cw-lab.width-40,52))
        for k,ln in enumerate(lines):
            parts=[(w+' ',NAVY if t>=ep.words[i]['s'] else (190,190,190)) for i,w in ln]
            li=rich_line(parts,48,700); cd.alpha_composite(li,(30+cw-li.width-40,100+62*k))
        yc=max(y2+60+chh/2,1100); yc=min(yc,1400-chh/2)
        paste(base,cd,W/2,yc+40*(1-ease(pc)),alpha=ease(pc))

# ---------------- captions (auto) ----------------
def captions(ep):
    hl=set(getattr(ep.sp,'HL',[])); ws=ep.words; chunks=[]; cur=[]; n=0
    for i,w in enumerate(ws):
        tw_=w['w'].strip(); cur.append(i); n+=len(tw_)+1
        endp=tw_[-1:] in ',.?:!'
        nxt=len(ws[i+1]['w'].strip()) if i+1<len(ws) else 0
        if (endp and n>=9) or n+nxt>24 or i==len(ws)-1: chunks.append(cur); cur=[]; n=0
    out=[]
    for k,ch in enumerate(chunks):
        parts=[]
        for j,i in enumerate(ch):
            w=ws[i]['w'].strip()+(' ' if j<len(ch)-1 else '')
            parts.append((w,TQD if norm(ws[i]['w']) in hl else (255,255,255)))
        t0=ws[ch[0]]['s']-0.02; t1=ws[chunks[k+1][0]]['s']-0.04 if k+1<len(chunks) else ep.HOLD
        out.append((t0,t1,caption_img(parts)))
    return out

# ---------------- main ----------------
def build(spec):
    ep=Ep(spec); HD=Header(); BG=Background(seed=spec.NUM)
    stamp=pill([(f"דקה ברורה · טיפ #{spec.NUM}",TQ)],36,bg=(255,255,255),shadow=False).rotate(4,expand=True,resample=Image.BICUBIC)
    sc=[];
    for k,s in enumerate(spec.SCENES):
        t0=0 if k==0 else ep.S(s['at'])-0.05
        sc.append([t0,None,s])
    cl=closing(ep); tcl=cl['start']-0.05
    for k in range(len(sc)): sc[k][1]=sc[k+1][0] if k+1<len(sc) else tcl
    sc.append([tcl,ep.HOLD,{'word':spec.END_WORD if hasattr(spec,'END_WORD') else 'עקבו','els':'closing'}])
    CAPS=captions(ep); FADE=0.28
    LOGO_END=Image.open(f'{LOGO}/logo-horizontal-color.png').convert('RGBA'); LOGO_END=LOGO_END.resize((560,int(LOGO_END.height*560/LOGO_END.width)),Image.LANCZOS)
    SLOGAN=text_img('ברור שמשלמים פחות.',40,STONE,600)
    def frame(t,face):
        if t>=ep.HOLD:
            im=Image.new('RGBA',(W,H),PAPER+(255,)); p=ease(prog(t,ep.HOLD,0.5))
            paste(im,LOGO_END,W/2,920,scale=0.9+0.1*p,alpha=p); paste(im,SLOGAN,W/2,1060,alpha=ease(prog(t,ep.HOLD+0.35,0.4)))
            return im
        cands=[s for s in sc if s[0]<=t<s[1]]; cur=cands[0] if cands else sc[-1]; i=sc.index(cur)
        base=BG.draw(t,cur[2].get('word'),ease(prog(t,cur[0],0.5))); HD.draw(base,face)
        layer=Image.new('RGBA',(W,H),(0,0,0,0))
        if i==0:
            p=prog(t,0.1,0.35); q=ease(prog(t,1.6,0.3)); paste(layer,stamp,760,700,scale=0.6+0.4*back(p),alpha=ease(p)*(1-q))
        if cur[2]['els']=='closing': draw_closing(ep,cl,layer,t)
        else:
            for e in cur[2]['els']: EL[e[0]](ep,layer,t,*e[1:])
        a=1.0
        if i+1<len(sc) and t>cur[1]-FADE: a=clamp((cur[1]-t)/FADE)
        if i>0 and t<cur[0]+0.15: a=min(a,clamp((t-cur[0])/0.15))
        if a<0.999: layer.putalpha(layer.getchannel('A').point(lambda v:int(v*a)))
        base.alpha_composite(layer)
        for t0,t1,ci in CAPS:
            if t0<=t<t1:
                p=prog(t,t0,0.12); paste(base,ci,W/2,1480+10*(1-ease(p)),scale=fit(ci,W-60),alpha=ease(p))
        return base
    frame.scenes=sc
    return ep,frame

if __name__=='__main__':
    spec=importlib.import_module(sys.argv[1]); out=sys.argv[2] if len(sys.argv)>2 else f'/home/claude/dk/out/{sys.argv[1]}.mp4'
    ep,frame=build(spec); RAW=spec.RAW; crop=(0,200,1080)
    PREVIEW=os.environ.get('PREVIEW')
    if PREVIEW:
        allf=list(read_frames(RAW,crop)); ts=[float(x) for x in PREVIEW.split(',')] if PREVIEW!='auto' else None
        if ts is None: ts=[0.8]+[b-0.35 for a,b,_ in frame.scenes]
        os.makedirs('/home/claude/dk/prev',exist_ok=True)
        for k,t in enumerate(ts):
            f=allf[min(len(allf)-1,int(t*FPS))]; frame(t,f).convert('RGB').resize((360,640)).save(f'/home/claude/dk/prev/{sys.argv[1]}_{k:02d}.png')
        ims=[Image.open(f'/home/claude/dk/prev/{sys.argv[1]}_{k:02d}.png') for k in range(len(ts))]
        S=Image.new('RGB',(360*len(ims),640),'white')
        for k,im in enumerate(ims): S.paste(im,(k*360,0))
        S.save(f'/home/claude/dk/prev/sheet_{sys.argv[1]}.png'); sys.exit()
    tmp=f'/home/claude/dk/tmp'; os.makedirs(tmp,exist_ok=True); os.makedirs(os.path.dirname(out),exist_ok=True)
    if not os.path.exists(f'{tmp}/whoosh.wav'): whoosh(f'{tmp}/whoosh.wav')
    TOTAL=ep.TOTAL; n=int(TOTAL*FPS); faces=read_frames(RAW,crop); last=None
    enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
        '-i',RAW,'-i',f'{tmp}/whoosh.wav','-filter_complex',
        f'[1:a]apad=whole_dur={TOTAL}[v];[2:a]adelay=50|50,volume=0.8[w];[v][w]amix=inputs=2:duration=first:normalize=0[a]',
        '-map','0:v','-map','[a]','-t',str(TOTAL),'-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-movflags','+faststart',out],stdin=subprocess.PIPE)
    for k in range(n):
        t=k/FPS
        try: f=next(faces); last=f
        except StopIteration: f=last
        enc.stdin.write(frame(t,f).convert('RGB').tobytes())
        if k%300==0: print(sys.argv[1],k,'/',n,flush=True)
    enc.stdin.close(); enc.wait(); print('done',out,round(TOTAL,2))
