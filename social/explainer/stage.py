"""stage.py N [N...]: copy rendered episode into repo, cover, posts.json (FB/IG reel 13:00), .vercelignore exception."""
import sys, json, shutil, subprocess, datetime
REPO='/home/claude/barur-site'; CAP=json.load(open('/home/claude/dk/batch/captions.json'))
base=datetime.date(2026,10,18)
posts=json.load(open(f'{REPO}/social/posts.json')); ids={p['id'] for p in posts['posts']}
vi=open(f'{REPO}/.vercelignore').read()
for n in map(int,sys.argv[1:]):
    src=f'/home/claude/dk/out/ep{n}.mp4' if n!=10 else f'{REPO}/social/video/dk10.mp4'
    dst=f'{REPO}/social/video/dk{n}.mp4'
    if src!=dst: shutil.copy(src,dst)
    subprocess.run(['ffmpeg','-v','error','-y','-ss','1.0','-i',dst,'-frames:v','1','-q:v','3',f'{REPO}/social/video/dk{n}-cover.jpg'],check=True)
    day=base+datetime.timedelta(days=n-10); c=CAP[str(n)]
    pid=f'{day.isoformat()}-dk{n}'
    if pid not in ids:
        posts['posts'].append({'id':pid,'publish_at':f'{day.isoformat()}T13:00',
          'text':f"{c['body']}\n\nדקה ברורה · טיפ #{n}\nהסרטון נוצר באמצעות AI.",
          'video':f'social/video/dk{n}.mp4','image':f'social/video/dk{n}-cover.jpg',
          'platforms':['facebook','instagram'],'status':'pending','format':'reel'})
    line=f'!social/video/dk{n}.mp4'
    if line not in vi: vi=vi.rstrip('\n')+'\n'+line+'\n'
    print('staged',n,day)
posts['posts'].sort(key=lambda p:p['publish_at'])
json.dump(posts,open(f'{REPO}/social/posts.json','w'),ensure_ascii=False,indent=2); open(f'{REPO}/.vercelignore','w').write(vi)
