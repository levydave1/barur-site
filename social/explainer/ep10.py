import sys, json, math, random, subprocess, os
sys.path.insert(0,'/home/claude/dk')
from dkengine import *
RAW='/home/claude/barur-site/social/heygen/raw/dk10-samebank.mp4'
WJ='/home/claude/barur-site/social/heygen/words/dk10-samebank.json'
OUT=sys.argv[1] if len(sys.argv)>1 else '/home/claude/dk/ep10.mp4'
PREVIEW=os.environ.get('PREVIEW')
words=json.load(open(WJ))['words']; S=lambda i: words[i]['s']; E_=lambda i: words[i]['e']
SPEECH_END=E_(74); HOLD=SPEECH_END+0.9; ENDC=1.7; TOTAL=HOLD+ENDC

# ---------- captions ----------
CH=[((0,2),[("רוצים ",0),("למחזר",1),(" משכנתה?",0)]),((3,5),[("ללכת לבנק שלכם,",0)]),((6,8),[("או לבנק ",0),("אחר?",1)]),
 ((9,13),[("בבנק שלכם זה ",0),("פשוט יותר:",1)]),((14,17),[("מכירים אתכם, פחות ניירת,",0)]),((18,20),[("ובאמת ",0),("רוב המחזורים",1)]),
 ((21,23),[("מתרחשים ",0),("בבנק המקורי.",1)]),((24,28),[("בבנק אחר צריך שמאות חדשה,",0)]),((29,30),[("טפסים, ולפעמים",0)]),
 ((31,33),[("גם להעביר ביטוחים.",0)]),((34,39),[("אבל יש דרך שמשלבת את ",0),("שניהם:",1)]),((40,43),[("מביאים הצעה מבנק אחר,",0)]),
 ((44,46),[("ונותנים לבנק שלכם",0)]),((47,48),[("להתמודד איתה.",0)]),((49,53),[("הרבה פעמים הוא פתאום יציע",0)]),
 ((54,56),[("הצעה ",0),("טובה יותר.",1)]),((57,59),[("התחרות עובדת ",0),("בשבילכם.",1)]),((60,60),[("תעקבו,",1)]),
 ((61,66),[("כל יום עוד דקה אחת ברורה.",0)]),((67,67),[("ומחר:",0)]),((68,70),[("הכסף שצריך לדירה,",0)]),((71,74),[("ואף אחד לא סופר.",0)])]
CAPS=[]
for k,((a,b),parts) in enumerate(CH):
    t0=S(a); t1=S(CH[k+1][0][0]) if k+1<len(CH) else HOLD
    CAPS.append((t0-0.02,t1-0.04,caption_img([(t,TQD if h else (255,255,255)) for t,h in parts])))
CAP_Y=1480

# ---------- assets ----------
HD=Header(); BG=Background()
stamp=pill([("דקה ברורה · טיפ #10",TQ)],36,bg=(255,255,255),shadow=False).rotate(4,expand=True,resample=Image.BICUBIC)
def stamp_draw(base,t):
    p=prog(t,0.1,0.35); q=ease(prog(t,1.5,0.3)); paste(base,stamp,760,700,scale=0.6+0.4*back(p),alpha=ease(p)*(1-q))
bank=icon('bank',120,NAVY,5); bank_t=icon('bank',120,TQ,5)
chk=icon('check',44,TQ,6)
def card(label,ic,w=340,h=300,hl=False):
    im=rounded(w,h,32,(255,255,255,255),shadow=True); p=30
    im.alpha_composite(ic,(p+(w-ic.width)//2,p+40))
    lt=text_img(label,44,TQ if hl else NAVY,700); im.alpha_composite(lt,(p+(w-lt.width)//2,p+h-90)); return im
CARD_MINE=card('הבנק שלכם',bank); CARD_OTHER=card('בנק אחר',bank_t,hl=True)
Q=text_img('?',90,STONE,700)
def chip(text,ic=None,color=NAVY): return pill([(text,color)],48,icon=ic,pad=(40,20))
CH_EASY=chip('פשוט יותר',chk); CH_KNOW=chip('מכירים אתכם',chk); CH_PAPER=chip('פחות ניירת',chk)
CH_APP=chip('שמאות חדשה',icon('ruler',44,CORAL,5)); CH_FORM=chip('טפסים',icon('doc',44,CORAL,5)); CH_INS=chip('להעביר ביטוחים',icon('shield',44,CORAL,5))
OFFER=pill([("הצעה",NAVY)],38,icon=icon('doc',40,TQ,5))
BETTER=pill([("הצעה ",NAVY),("טובה יותר",TQ)],52,icon=icon('check',46,TQ,6))
FOLLOW=pill([("+ עקבו",(255,255,255))],58,bg=NAVY,pad=(56,24))
HAND=icon('hand',90,NAVY,5)
random.seed(4); CONF=[(random.uniform(-1,1),random.uniform(-1.2,-0.3),random.choice([TQL,AMBER,CORAL,NAVY]),random.uniform(0,6)) for _ in range(60)]

def title_row(base,t,t0,txt_parts,ic,y=700):
    p=prog(t,t0,0.4); im=rich_line(txt_parts,72,700)
    row=Image.new('RGBA',(im.width+ic.width+20,max(im.height,ic.height)),(0,0,0,0))
    row.alpha_composite(im,(0,(row.height-im.height)//2)); row.alpha_composite(ic,(im.width+20,(row.height-ic.height)//2))
    paste(base,row,W/2,y+30*(1-ease(p)),alpha=ease(p))

def big_lines(base,t,items,y0,gap=120):
    for i,(t0,parts,size) in enumerate(items):
        p=prog(t,t0,0.35)
        if p<=0: continue
        paste(base,rich_line(parts,size,700),W/2,y0+i*gap,scale=0.7+0.3*back(p),alpha=ease(p))

# ---------- scenes ----------
def sc1(base,t):
    stamp_draw(base,t)
    p2=prog(t,1.6,0.4)  # headline moves up when cards come
    y=900-180*ease(p2); s=1-0.3*ease(p2)
    p=prog(t,0.2,0.35); paste(base,rich_line([("רוצים ",NAVY),("למחזר?",TQ)],120,700),W/2,y,scale=s*(0.7+0.3*back(p)),alpha=ease(p))
    pa=prog(t,S(4),0.35); paste(base,CARD_MINE,W/2+200,1060+40*(1-ease(pa)),scale=0.8+0.2*back(pa),alpha=ease(pa))
    pb=prog(t,S(7),0.35); paste(base,CARD_OTHER,W/2-200,1060+40*(1-ease(pb)),scale=0.8+0.2*back(pb),alpha=ease(pb))
    pq=prog(t,S(6),0.3); paste(base,Q,W/2,1060,scale=back(pq),alpha=ease(pq))
def sc2(base,t):
    title_row(base,t,S(9),[("בבנק ",NAVY),("שלכם",TQ)],icon('bank',70,NAVY,5),700)
    for i,(t0,c) in enumerate([(S(12),CH_EASY),(S(14),CH_KNOW),(S(16),CH_PAPER)]):
        p=prog(t,t0,0.35); paste(base,c,W/2+(1-ease(p))*60,870+i*135,alpha=ease(p))
    big_lines(base,t,[(S(19),[("רוב המחזורים",TQ)],92),(S(21),[("נעשים בבנק המקורי.",NAVY)],60)],1270,105)
def sc3(base,t):
    title_row(base,t,S(24),[("בבנק ",NAVY),("אחר",CORAL)],icon('bank',70,CORAL,5),700)
    for i,(t0,c) in enumerate([(S(27),CH_APP),(S(29),CH_FORM),(S(32),CH_INS)]):
        p=prog(t,t0,0.35); paste(base,c,W/2,880+i*150,scale=0.8+0.2*back(p),alpha=ease(p))
def sc4(base,t):
    p=prog(t,S(34),0.35); paste(base,rich_line([("דרך שמשלבת את ",NAVY),("שניהם",TQ)],70,700),W/2,720,alpha=ease(p),scale=0.85+0.15*back(p))
    pa=prog(t,S(40),0.35)
    paste(base,CARD_OTHER,W/2-230,1060,scale=0.85,alpha=ease(pa)); paste(base,CARD_MINE,W/2+230,1060,scale=0.85,alpha=ease(pa))
    pm=ease(prog(t,S(41),S(46)-S(41)))
    if t>=S(41):
        x=(W/2-230)+460*pm; y=1060-160*math.sin(math.pi*pm)
        paste(base,OFFER,x,y,alpha=ease(prog(t,S(41),0.25)))
    ps=prog(t,S(47),0.6)
    if 0<ps<1: paste(base,CARD_MINE,W/2+230,1060,scale=0.85+0.06*math.sin(ps*math.pi*4),alpha=0.0)
def sc5(base,t):
    p=prog(t,S(53),0.4); paste(base,BETTER,W/2,760,scale=0.6+0.4*back(p),alpha=ease(p))
    pa=prog(t,S(49),0.4); paste(base,icon('bank',110,TQ,5),W/2,920,alpha=ease(pa)*(1-ease(prog(t,S(57),0.3))))
    big_lines(base,t,[(S(57),[("התחרות",NAVY)],130),(S(58),[("עובדת בשבילכם.",TQ)],84)],1040,140)
    tc=t-S(58)
    if 0<tc<1.6:
        d=ImageDraw.Draw(base,'RGBA')
        for vx,vy,c,r in CONF:
            x=W/2+vx*520*tc; y=1060+vy*700*tc+600*tc*tc; a=int(255*clamp(1-tc/1.6))
            d.rounded_rectangle([x-9,y-5,x+9,y+5],3,fill=c+(a,))
def sc6(base,t):
    p=prog(t,S(60),0.35); paste(base,FOLLOW,W/2,780,scale=0.6+0.4*back(p),alpha=ease(p))
    if t>S(60)+0.2:
        tap=(math.sin((t-S(60))*5)+1)/2; paste(base,HAND,W/2+80,870+18*tap,alpha=ease(prog(t,S(60)+0.2,0.3)))
    pl=prog(t,S(61),0.4); paste(base,text_img('כל יום עוד דקה אחת ברורה',46,STONE,600),W/2,950,alpha=ease(pl))
    pc=prog(t,S(67),0.4)
    if pc>0:
        cw,chh=860,230; cd=rounded(cw,chh,26,(255,255,255,255),shadow=True); dd=ImageDraw.Draw(cd)
        dd.rectangle([30+cw-10,30,30+cw,30+chh],fill=AMBER+(255,))
        lab=text_img('מחר בדקה ברורה',34,AMBER,700); cd.alpha_composite(lab,(30+cw-lab.width-40,52))
        ws=[(68,'הכסף'),(69,'שצריך'),(70,'לדירה,'),(71,'ואף'),(72,'אחד'),(73,'לא'),(74,'סופר.')]
        line1=[(w+' ',NAVY if t>=S(i) else (190,190,190)) for i,w in ws[:3]]; line2=[(w+' ',NAVY if t>=S(i) else (190,190,190)) for i,w in ws[3:]]
        l1=rich_line(line1,48,700); l2=rich_line(line2,48,700)
        cd.alpha_composite(l1,(30+cw-l1.width-40,100)); cd.alpha_composite(l2,(30+cw-l2.width-40,160))
        paste(base,cd,W/2,1160+40*(1-ease(pc)),alpha=ease(pc))

SCENES=[(0,S(9)-0.05,sc1,'מחזור'),(S(9)-0.05,S(24)-0.05,sc2,'שלכם'),(S(24)-0.05,S(34)-0.05,sc3,'אחר'),
        (S(34)-0.05,S(49)-0.05,sc4,'שניהם'),(S(49)-0.05,S(60)-0.05,sc5,'תחרות'),(S(60)-0.05,HOLD,sc6,'עקבו')]
FADE=0.28
LOGO_END=Image.open(f'{LOGO}/logo-horizontal-color.png').convert('RGBA'); LOGO_END=LOGO_END.resize((560,int(LOGO_END.height*560/LOGO_END.width)),Image.LANCZOS)
SLOGAN=text_img('ברור שמשלמים פחות.',40,STONE,600)

def frame(t,face):
    if t>=HOLD:
        im=Image.new('RGBA',(W,H),PAPER+(255,)); p=ease(prog(t,HOLD,0.5))
        paste(im,LOGO_END,W/2,920,scale=0.9+0.1*p,alpha=p); paste(im,SLOGAN,W/2,1060,alpha=ease(prog(t,HOLD+0.35,0.4)))
        return im
    cur=[s for s in SCENES if s[0]<=t<s[1]][0]; i=SCENES.index(cur)
    base=BG.draw(t,cur[3],ease(prog(t,cur[0],0.5)))
    HD.draw(base,face)
    layer=Image.new('RGBA',(W,H),(0,0,0,0)); cur[2](layer,t)
    a=1.0
    if i+1<len(SCENES) and t>cur[1]-FADE: a=clamp((cur[1]-t)/FADE)
    if i>0 and t<cur[0]+0.15: a=min(a,clamp((t-cur[0])/0.15))
    if a<0.999: layer.putalpha(layer.getchannel('A').point(lambda v:int(v*a)))
    base.alpha_composite(layer)
    for t0,t1,ci in CAPS:
        if t0<=t<t1:
            p=prog(t,t0,0.12); paste(base,ci,W/2,CAP_Y+10*(1-ease(p)),alpha=ease(p))
    return base

if __name__=='__main__':
    crop=(190,330,720)
    if PREVIEW:
        faces=read_frames(RAW,crop); fl=[]
        ts=[float(x) for x in PREVIEW.split(',')]
        allf=list(read_frames(RAW,crop))
        for k,t in enumerate(ts):
            f=allf[min(len(allf)-1,int(t*FPS))]; frame(t,f).convert('RGB').save(f'/home/claude/dk/p_{k:02d}.png')
        sys.exit()
    os.makedirs('/home/claude/dk/tmp',exist_ok=True); whoosh('/home/claude/dk/tmp/whoosh.wav')
    n=int(TOTAL*FPS); faces=read_frames(RAW,crop); last=None
    enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
        '-i',RAW,'-i','/home/claude/dk/tmp/whoosh.wav','-filter_complex',
        f'[1:a]apad=whole_dur={TOTAL}[v];[2:a]adelay=50|50,volume=0.8[w];[v][w]amix=inputs=2:duration=first:normalize=0[a]',
        '-map','0:v','-map','[a]','-t',str(TOTAL),'-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-movflags','+faststart',OUT],stdin=subprocess.PIPE)
    for k in range(n):
        t=k/FPS
        try: f=next(faces); last=f
        except StopIteration: f=last
        enc.stdin.write(frame(t,f).convert('RGB').tobytes())
        if k%150==0: print(k,'/',n,flush=True)
    enc.stdin.close(); enc.wait(); print('done',OUT,TOTAL)
