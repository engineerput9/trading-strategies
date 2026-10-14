exec(open('add5m.py').read())
import numpy as np,pandas as pd
src=open('add5m.py').read()
def build2(d,per=100,mult=3):
    B=build.__wrapped__(d,per,mult) if hasattr(build,'__wrapped__') else None
exec(src.split('def build')[0])
exec('def buildm(d,per=100,mult=3):'+src.split('def build(d,per=100):')[1].split('def feats')[0].replace(')*3',')*mult'))
OOS=pd.Timestamp('2026-04-01',tz='Asia/Kolkata')
cache={}
def getB(per,mult):
    k=(per,mult)
    if k not in cache:
        B=buildm(d5,per,mult);x=B['x']
        for lb in (14,20,30):
            er=np.full(B['n'],np.nan)
            ad=np.abs(np.diff(x,prepend=x[0]));cs=np.cumsum(ad)
            er[lb:]=np.abs(x[lb:]-x[:-lb])/np.maximum(cs[lb:]-cs[:-lb],1e-9)
            B['er%d'%lb]=er
        cache[k]=B
    return cache[k]
P0=dict(per=100,mult=3,pdl=4,erth=0.294737,erlb=20,wait=2,lks=1.5,tks=2,ttp=2.5,ltp=1.5,gap=0.5)
def run(**kw):
    p={**P0,**kw};B=getB(p['per'],p['mult']);n=B['n'];x,H,L,ci,day=B['x'],B['H'],B['L'],B['ci'],B['day']
    T=[];done=None
    for i in range(B['start'],n):
        if day[i]==done or B['flip'][i]==0: continue
        s=B['flip'][i];done=day[i]
        if i+1>=n or day[i+1]!=day[i]: continue
        f=feats(B,i,s);dt=B['dt'][i]
        if f is None or dt.day_name()[:3]=='Fri' or (f['gap_filled'] and abs(f['gap_atr'])>p['gap']) or f['pdl_atr']<p['pdl']: continue
        e=x[i];sl0=stopof(B,i,s);R0=abs(e-sl0);j=i+p['wait']
        if j>=n or day[j]!=day[i] or (ci[i:j+1]!=s).any(): continue
        if ((L[i+1:j+1]<=sl0).any() if s>0 else (H[i+1:j+1]>=sl0).any()): continue
        ie,ee=j,x[j];a=B['atr'][ie]
        tight=B['er%d'%p['erlb']][ie]>p['erth']
        if tight: sl=ee-s*p['tks']*a;tp=e+s*p['ttp']*R0
        else: sl=e-s*p['lks']*R0;tp=e+s*p['ltp']*R0
        k=ie+1;last=ie;pts=None;why='session_end'
        while k<n and day[k]==day[ie]:
            last=k
            if (L[k]<=sl) if s>0 else (H[k]>=sl): pts=s*(sl-ee);why='stop';break
            if (H[k]>=tp) if s>0 else (L[k]<=tp): pts=s*(tp-ee);why='target';break
            k+=1
        if pts is None: pts=s*(x[last]-ee)
        T.append(dict(px=ee,time=dt,mode='tight' if tight else 'locked',pts=pts,why=why))
    return pd.DataFrame(T)
def st(D,col='pts'):
    q=D[col].values;IS=(D.time<OOS).values;c=np.cumsum(q)
    return dict(n=len(q),win=round(100*(q>0).mean(),1),net=round(q.sum()),avg_win=round(q[q>0].mean(),1),avg_loss=round(q[q<=0].mean(),1),maxDD=round((np.maximum.accumulate(np.r_[0,c])[1:]-c).max()),IS=round(q[IS].sum()),OOS=round(q[~IS].sum()))
if __name__=='__main__':
    D=run();print(st(D));import pickle;pickle.dump(D,open('_base_final.pkl','wb'))
