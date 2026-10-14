import json,numpy as np,pandas as pd
c=json.load(open('raw.json'))['cont']
d5=pd.DataFrame(c,columns='t o h l c v'.split()).drop_duplicates('t').sort_values('t')
d5['dt']=pd.to_datetime(d5.t,unit='s',utc=True).dt.tz_convert('Asia/Kolkata');d5=d5.reset_index(drop=True)
d15=d5.set_index('dt').resample('15min',label='left',closed='left').agg(dict(o='first',h='max',l='min',c='last',v='sum')).dropna().reset_index()
def ema(a,t):
    al=2/(t+1);o=np.full(len(a),np.nan);s=np.nan;buf=[]
    for i,v in enumerate(a):
        if np.isnan(v): continue
        if np.isnan(s):
            buf.append(v)
            if len(buf)==t: s=np.mean(buf)
        else: s=al*v+(1-al)*s
        o[i]=s
    return o
def build(d,per=100):
    x=d.c.values.astype(float);n=len(x);H=d.h.values.astype(float);L=d.l.values.astype(float);O=d.o.values.astype(float)
    dif=np.r_[np.nan,np.abs(np.diff(x))];r=ema(ema(dif,per),2*per-1)*3
    rf=np.zeros(n);rf[0]=x[0]
    for i in range(1,n):
        p=rf[i-1];R=r[i]
        if np.isnan(R): rf[i]=x[i];continue
        rf[i]=(p if x[i]-R<p else x[i]-R) if x[i]>p else (p if x[i]+R>p else x[i]+R)
    up=np.zeros(n);dn=np.zeros(n)
    for i in range(1,n):
        up[i]=up[i-1]+1 if rf[i]>rf[i-1] else 0 if rf[i]<rf[i-1] else up[i-1]
        dn[i]=dn[i-1]+1 if rf[i]<rf[i-1] else 0 if rf[i]>rf[i-1] else dn[i-1]
    ch=np.r_[False,x[1:]!=x[:-1]];lc=(x>rf)&(up>0)&ch;sc=(x<rf)&(dn>0)&ch
    ci=np.zeros(n)
    for i in range(1,n): ci[i]=1 if lc[i] else -1 if sc[i] else ci[i-1]
    flip=np.zeros(n,int);flip[1:]=np.where((lc[1:]&(ci[:-1]==-1)),1,np.where(sc[1:]&(ci[:-1]==1),-1,0))
    tr=np.maximum(H-L,np.maximum(abs(H-np.r_[np.nan,x[:-1]]),abs(L-np.r_[np.nan,x[:-1]])));tr[0]=H[0]-L[0]
    atr=np.full(n,np.nan);atr[13]=tr[:14].mean()
    for i in range(14,n): atr[i]=(atr[i-1]*13+tr[i])/14
    day=d.dt.dt.date.values;first={};last={}
    for k,dd in enumerate(day): first.setdefault(dd,k);last[dd]=k
    days=sorted(first);pos={dd:q for q,dd in enumerate(days)}
    return dict(d=d,x=x,H=H,L=L,O=O,rf=rf,r=r,ci=ci,flip=flip,atr=atr,day=day,first=first,last=last,days=days,pos=pos,n=n,start=3*per*2,dt=d.dt)
def feats(B,i,s):
    x,H,L,O,atr=B['x'],B['H'],B['L'],B['O'],B['atr'];dd=B['day'][i];q=B['pos'][dd];f0=B['first'][dd]
    if q==0: return None
    p=B['days'][q-1];pc=x[B['last'][p]];gap=O[f0]-pc
    lo=L[f0:i+1].min();hi=H[f0:i+1].max()
    gf=bool(lo<=pc) if gap>0 else bool(hi>=pc) if gap<0 else True
    pl=L[B['first'][p]:B['last'][p]+1].min();ph=H[B['first'][p]:B['last'][p]+1].max()
    return dict(gap_atr=gap/atr[f0],gap_filled=gf,pdl_atr=(x[i]-pl)/atr[i],pdr=ph-pl)
def okf(f,dt): return f is not None and dt.day_name()[:3]!='Fri' and not(f['gap_filled'] and abs(f['gap_atr'])>0.5) and f['pdl_atr']>=4
def stopof(B,i,s):
    e=B['x'][i];a=B['atr'][i]
    if s>0: raw=B['L'][i-10:i].min(); sl=e-a if e-raw<a else raw
    else: raw=B['H'][i-10:i].max(); sl=e+a if raw-e<a else raw
    return sl
def sim(B,i,e,s,stop,R,tps=(1,1.5),mg=None):
    H,L,x,day=B['H'],B['L'],B['x'],B['day'];legs=[[stop,e+s*tps[0]*R,None],[stop,e+s*tps[1]*R,None]];j=i+1;lastj=i
    while j<B['n'] and day[j]==day[i]:
        lastj=j
        for lg in legs:
            if lg[2] is not None: continue
            if (L[j]<=lg[0]) if s>0 else (H[j]>=lg[0]): lg[2]=lg[0]
            elif lg[1] is not None and ((H[j]>=lg[1]) if s>0 else (L[j]<=lg[1])): lg[2]=lg[1]
        if mg is not None and legs[1][2] is None: mg(j,legs,e,s,R)
        if all(lg[2] is not None for lg in legs): break
        j+=1
    return float(np.mean([s*((lg[2] if lg[2] is not None else x[lastj])-e) for lg in legs]))
def stats(df):
    if len(df)==0: return dict(n=0,win=np.nan,net=0,dd=0)
    q=df.pts.values;eq=np.cumsum(q);dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
    return dict(n=len(df),win=round((q>0).mean()*100,1),net=round(q.sum()),dd=round(dd),avgpts=round(q.mean(),1))
