from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont
import math
S=1024; N=12
BODY=(158,200,246); HI=(196,224,252); LEG=(140,188,242); LEGB=(112,164,230); NAVY=(27,47,110)
FONT='/usr/share/fonts/truetype/sand-box/google/Nunito/Nunito-VariableFont_wght.ttf'
def cap(d,a,b,w,c):
    d.line([a,b],fill=c,width=w); r=w/2
    for p in (a,b): d.ellipse([p[0]-r,p[1]-r,p[0]+r,p[1]+r],fill=c)
def leg(d,hip,knee,foot,w,c):
    w=w*1.25
    pts=[]
    for j in range(41):
        u=j/40; x=(1-u)**2*hip[0]+2*u*(1-u)*knee[0]+u*u*foot[0]; y=(1-u)**2*hip[1]+2*u*(1-u)*knee[1]+u*u*foot[1]; pts.append((x,y))
    r=w/2
    for x,y in pts: d.ellipse([x-r,y-r,x+r,y+r],fill=c)
    h=tuple(min(255,v+20) for v in c[:3])+(255,); r2=w*0.17
    for x,y in pts[4:30]: d.ellipse([x-r2-w*0.12,y-r2-w*0.18,x+r2-w*0.12,y+r2-w*0.18],fill=h)
def body_layer(cx,cy,R,sq=1.0):
    L=Image.new('RGBA',(S,S),(0,0,0,0)); d=ImageDraw.Draw(L)
    rx,ry=R/ sq**0.5, R*sq**0.5
    box=[cx-rx,cy-ry,cx+rx,cy+ry]
    d.ellipse(box,fill=BODY+(255,))
    m=Image.new('L',(S,S),0); ImageDraw.Draw(m).ellipse(box,fill=255)
    def soft(box,col,a,b):
        m2=Image.new('L',(S,S),0); ImageDraw.Draw(m2).ellipse(box,fill=a); m2=m2.filter(ImageFilter.GaussianBlur(b))
        x=Image.new('RGBA',(S,S),col+(0,)); x.putalpha(m2); return x
    hl=soft([cx-rx*0.8,cy-ry*0.9,cx+rx*0.4,cy+ry*0.25],HI,150,50)
    sh=soft([cx-rx*0.1,cy+ry*0.15,cx+rx*1.4,cy+ry*1.5],(120,168,232),150,50)
    for x in (sh,hl):
        x.putalpha(ImageChops.multiply(x.getchannel('A'),m)); L.alpha_composite(x)
    return L
def face(d,cx,cy,blink=0.0,look=(0,0),mouth='smile'):
    for s in (-1,1):
        ex,ey=cx+s*100+look[0],cy+60+look[1]; r=30; ry=max(3,r*(1-blink))
        d.ellipse([ex-r,ey-ry,ex+r,ey+ry],fill=NAVY)
    mx,my=cx+look[0]*0.6,cy+120+look[1]*0.6
    if mouth=='smile': d.arc([mx-34,my-26,mx+34,my+16],20,160,fill=NAVY,width=11)
    elif mouth=='flat': cap(d,(mx-24,my),(mx+24,my),10,NAVY)
    elif mouth=='o': d.ellipse([mx-22,my-20,mx+22,my+28],fill=NAVY)
    elif mouth=='hmm': d.arc([mx-30,my,mx+30,my+40],200,340,fill=NAVY,width=10)
LEGS=[(k,s) for k in (3,2,1,0) for s in (-1,1)]
def legs(d,cx,cy,feet_fn,skip=(),front=None):
    for k,s in LEGS:
        if (k,s) in skip: continue
        if front is not None and (k<=1)!=front: continue
        hip=(cx+s*(60+k*55),cy+150+k*8)
        fx,fy=feet_fn(k,s)
        knee=(fx+s*20,hip[1]-20)
        c=LEGB if k%2 else LEG
        leg(d,hip,knee,(fx,fy),74,c+(255,))
def base_feet(cx,ground=920):
    return lambda k,s:(cx+s*(110+k*95),ground-k*35)
def render(L): return L.resize((512,512),Image.LANCZOS)
def blink_at(i,frames=(9,10)): return {frames[0]:0.6,frames[1]:1.0}.get(i,0.0)

def idle(i):
    t=i/N; br=math.sin(2*math.pi*t)
    cx,cy=512,430-10*br
    L=Image.new('RGBA',(S,S),(0,0,0,0)); d=ImageDraw.Draw(L)
    bf=base_feet(cx)
    def ft(k,s):
        x,y=bf(k,s); tap=(k==0 and s==1)
        return (x, y-(40*max(0,math.sin(4*math.pi*t)) if tap else 0))
    legs(d,cx,cy,ft,front=False)
    L.alpha_composite(body_layer(cx,cy,270,1+0.03*br)); d=ImageDraw.Draw(L)
    legs(d,cx,cy,ft,front=True)
    face(d,cx,cy,blink_at(i,(8,9)))
    return L

def walking(i):
    t=i/N; p=2*math.pi*t
    cx=512+18*math.sin(p); cy=420-28*abs(math.sin(p))
    L=Image.new('RGBA',(S,S),(0,0,0,0)); d=ImageDraw.Draw(L)
    bf=base_feet(512)
    def ft(k,s):
        x,y=bf(k,s); ph=p+(math.pi if (k+(s>0))%2 else 0)
        return (x+70*math.cos(ph), y-75*max(0,math.sin(ph)))
    legs(d,cx,cy,ft,front=False)
    L.alpha_composite(body_layer(cx,cy,265,1-0.04*math.cos(2*p))); d=ImageDraw.Draw(L)
    legs(d,cx,cy,ft,front=True)
    face(d,cx,cy,blink_at(i,(6,7)),look=(25,0))
    return L

def glass(L,c,ang,glint):
    d=ImageDraw.Draw(L); x,y=c
    hx,hy=x-math.cos(ang)*170,y+math.sin(ang)*170
    cap(d,(x,y),(hx,hy),34,(70,120,200,255))
    d.ellipse([x-95,y-95,x+95,y+95],fill=(70,120,200,255))
    d.ellipse([x-72,y-72,x+72,y+72],fill=(220,238,255,200))
    g=-60+120*glint
    d.arc([x-56,y-56,x+56,y+56],200+g,250+g,fill=(255,255,255,255),width=12)
    return (hx,hy)
def scanning(i):
    t=i/N; p=2*math.pi*t; sw=math.sin(p)
    cx,cy=470,440
    L=Image.new('RGBA',(S,S),(0,0,0,0)); d=ImageDraw.Draw(L)
    bf=base_feet(cx)
    def ft(k,s):
        x,y=bf(k,s); shuffle=(k%2==0)
        return (x+(20*sw if shuffle else -20*sw), y)
    legs(d,cx,cy,ft,skip={(0,1)},front=False)
    L.alpha_composite(body_layer(cx,cy,255)); d=ImageDraw.Draw(L)
    legs(d,cx,cy,ft,skip={(0,1)},front=True)
    face(d,cx,cy,blink_at(i,(3,4)),look=(40*sw+20,-10),mouth='flat')
    gc=(cx+300+40*sw,cy+30-50*math.cos(p))
    hand=glass(L,gc,math.radians(55+15*sw),(i%N)/N)
    d=ImageDraw.Draw(L); hip=(cx+60,cy+150)
    leg(d,hip,((hip[0]+hand[0])/2+20,hip[1]+40),hand,74,LEG+(255,))
    d.ellipse([hand[0]-46,hand[1]-46,hand[0]+46,hand[1]+46],fill=LEG+(255,))
    return L

def thinking(i):
    t=i/N; p=2*math.pi*t
    cx,cy=440,470
    L=Image.new('RGBA',(S,S),(0,0,0,0)); d=ImageDraw.Draw(L)
    bf=base_feet(cx)
    def ft(k,s):
        x,y=bf(k,s); tap=(k==1 and s==-1)
        return (x,y-35*max(0,math.sin(3*p)) if tap else y)
    legs(d,cx,cy,ft,skip={(0,1)},front=False)
    tilt=12*math.sin(p)
    L.alpha_composite(body_layer(cx+tilt*0.5,cy,250)); d=ImageDraw.Draw(L)
    legs(d,cx,cy,ft,skip={(0,1)},front=True)
    face(d,cx+tilt*0.5,cy,blink_at(i,(5,6)),look=(30,-35),mouth='hmm')
    hip=(cx+60,cy+150); chin=(cx+150+tilt*0.5,cy+215-12*abs(math.sin(2*p)))
    leg(d,hip,(hip[0]+170,hip[1]+60),chin,70,LEG+(255,))
    n=min(4,i//2)
    for j in range(min(3,n)):
        r=16+12*j; x,y=cx+300+60*j,cy-260-70*j
        d.ellipse([x-r,y-r,x+r,y+r],fill=NAVY+(255,))
    if n>=4:
        f=ImageFont.truetype(FONT,190)
        try:f.set_variation_by_name('Black')
        except:pass
        d.text((cx+500,cy-430+8*math.sin(3*p)),'?',font=f,fill=NAVY+(255,),anchor='mm')
    return L

RED=(226,48,48,255)
def drop(d,x,y,s=1.0):
    r=42*s; d.ellipse([x-r,y-r,x+r,y+r],fill=RED); d.polygon([(x-r*0.9,y-r*0.3),(x+r*0.9,y-r*0.3),(x,y-r*2.3)],fill=RED)
    d.ellipse([x-r*0.5,y-r*0.6,x-r*0.15,y-r*0.1],fill=(255,170,170,255))
def leak(i):
    t=i/N
    cx,cy=420,450; jit=(8 if i%2 else -8) if i>=7 else 0
    L=Image.new('RGBA',(S,S),(0,0,0,0)); d=ImageDraw.Draw(L)
    bf=base_feet(cx)
    def ft(k,s):
        x,y=bf(k,s); return (x,y-(30 if i>=7 and (k+s)%2 else 0))
    legs(d,cx+jit,cy,ft,skip={(0,1)},front=False)
    jump=-30 if i in (7,8) else 0
    L.alpha_composite(body_layer(cx+jit,cy+jump,250)); d=ImageDraw.Draw(L)
    legs(d,cx+jit,cy,ft,skip={(0,1)},front=True)
    alarmed=i>=7
    face(d,cx+jit,cy+jump,0,look=(45,20) if not alarmed else (35,-5),mouth='o' if alarmed else 'flat')
    if alarmed:
        for a in (-1,0,1):
            x0,y0=cx+jit+a*90,cy+jump-300
            cap(d,(x0,y0),(x0+a*25,y0-60),14,NAVY+(255,))
    hip=(cx+60,cy+150); tip=(cx+330,cy+(80 if alarmed else 150))
    leg(d,hip,(hip[0]+140,hip[1]+30),tip,70,LEG+(255,))
    px=800; gy=900
    # puddle grows after impact
    pw=40+min(i,11)*0 if i<6 else 70+(i-6)*14
    d.ellipse([px-pw,gy-18,px+pw,gy+18],fill=RED)
    if i<6:
        drop(d,px,120+i*130,1.0)
    elif i<9:
        k=i-5
        for a in (-1,1):
            d.ellipse([px+a*40*k-14,gy-60*k+18*k*k-14,px+a*40*k+14,gy-60*k+18*k*k+14],fill=RED)
    else:
        drop(d,px,120+(i-9)*60,0.7)
    return L

def to_gif(frames,path,dur):
    out=[]
    for f in frames:
        a=f.getchannel('A').point(lambda v:255 if v>=128 else 0)
        bg=Image.new('RGBA',f.size,(0,0,0,255)); bg.alpha_composite(f)
        q=bg.convert("RGB").quantize(255,method=2,dither=Image.Dither.NONE)
        q.putpalette(q.getpalette()[:765]+[0,0,0]); q.paste(255,mask=Image.eval(a,lambda v:255-v)); out.append(q)
    out[0].save(path,save_all=True,append_images=out[1:],duration=dur,loop=0,transparency=255,disposal=2)
OUT={'juicy_spider':idle,'spider_walking':walking,'spider_thinking':thinking,'spider_scanning':scanning,'spider_leak':leak}
for name,fn in OUT.items():
    fr=[render(fn(i)) for i in range(N)]
    # fit: crop common bbox to square
    import functools
    bb=[f.getbbox() for f in fr]; x0=min(b[0] for b in bb); y0=min(b[1] for b in bb); x1=max(b[2] for b in bb); y1=max(b[3] for b in bb)
    side=max(x1-x0,y1-y0)+20; cx,cy=(x0+x1)//2,(y0+y1)//2
    fr=[f.crop((cx-side//2,cy-side//2,cx-side//2+side,cy-side//2+side)).resize((512,512),Image.LANCZOS) for f in fr]
    to_gif(fr,f'../{name}.gif',90 if name!='spider_thinking' else 110)
    to_gif([f.resize((128,128),Image.LANCZOS) for f in fr],f'../{name}_128.gif',90 if name!='spider_thinking' else 110)
    strip=Image.new('RGBA',(160*N,170),(255,255,255,255))
    for j,f in enumerate(fr): strip.alpha_composite(f.resize((150,150),Image.LANCZOS),(160*j+5,10))
    short=name.replace('spider_','').replace('juicy_spider','idle')
    strip.save(f'../frames_{short}.png')
