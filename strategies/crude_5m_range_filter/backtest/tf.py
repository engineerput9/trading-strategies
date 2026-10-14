import json,numpy as np,pandas as pd
src=open('bt.py').read().split("df=pd.DataFrame(T)")[0].replace("T.append(dict(time=d.dt[i],","T.append(dict(i=i,s=s,time=d.dt[i],")
pre,post=src.split("x=d.c.values",1); post="x=d.c.values"+post
c=json.load(open('raw.json'))['cont']
d5=pd.DataFrame(c,columns='t o h l c v'.split()).drop_duplicates('t').sort_values('t')
d5['dt']=pd.to_datetime(d5.t,unit='s',utc=True).dt.tz_convert('Asia/Kolkata');d5=d5.reset_index(drop=True)
def bars15():
    r=d5.set_index('dt').resample('15min',label='left',closed='left').agg(dict(o='first',h='max',l='min',c='last',v='sum')).dropna().reset_index()
    return r
def run(d):
    g=dict(d=d,np=np,pd=pd);exec(post,g)
    T=g['T'];df=pd.DataFrame(T);sim=g['sim'];x,H,L,O,atr=g['x'],g['H'],g['L'],d.o.values,g['atr']
    df['ro']=[(sim(t,1,1)+sim(t,1.5,1))/2 for t in T];df['r1']=[sim(t,1,1) for t in T]
    gd=d.dt.dt.date.values;first={};last={}
    for k,dd in enumerate(gd): first.setdefault(dd,k);last[dd]=k
    days=sorted(first);pos={dd:q for q,dd in enumerate(days)}
    ga=[];gf=[];pdl=[];pdlp=[]
    for t in df.itertuples():
        dd=gd[t.i];q=pos[dd];f0=first[dd]
        if q==0: ga.append(0);gf.append(False);pdl.append(np.nan);pdlp.append(np.nan);continue
        p=days[q-1];pc=x[last[p]];gap=O[f0]-pc;ga.append(gap/atr[f0])
        lo=L[f0:t.i+1].min();hi=H[f0:t.i+1].max()
        gf.append(bool(lo<=pc) if gap>0 else bool(hi>=pc) if gap<0 else True)
        pl=L[first[p]:last[p]+1].min();pdlp.append(x[t.i]-pl);pdl.append((x[t.i]-pl)/atr[t.i])
    df['gap_atr']=ga;df['gap_filled']=gf;df['pdl_atr']=pdl;df['pdl_pts']=pdlp;df['atr']=atr[df.i.values]
    df['dow']=df.time.dt.day_name().str[:3];df['oos']=df.time>=pd.Timestamp('2026-04-01',tz='Asia/Kolkata')
    df['pts']=df.ro*df.risk_pts
    return df.drop(columns=['_fav','_adv','_cl'])
def stats(b):
    q=b.pts.values;eq=np.cumsum(q);dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max() if len(q) else 0
    return dict(n=len(b),win=round((b.ro>0).mean()*100,1),win1R=round((b.r1>0).mean()*100,1),net=round(q.sum()),expR=round(b.ro.mean(),3),dd=round(dd),med_risk=round(b.risk_pts.median(),1))
f5=run(d5);f15=run(bars15())
# 5m ATR at 15m signal time (last completed 5m bar = signal bar close)
a5=pd.Series(run.__globals__ and None)
g5=dict(d=d5,np=np,pd=pd);exec(post.split("day=d.dt")[0],g5);A5=pd.Series(g5['atr'],index=d5.dt)
f15['atr5']=[A5.asof(t+pd.Timedelta('10min')) for t in f15.time];f15['pdl_atr5']=f15.pdl_pts/f15.atr5
rows=[]
for tf,f in [('5m',f5),('15m',f15)]:
    base=(f.dow!='Fri')&~(f.gap_filled&(f.gap_atr.abs()>0.5))
    V={'original':np.ones(len(f),bool),'updated (4 ATR on tf ATR)':base&(f.pdl_atr>=4)}
    if tf=='15m':
        V['updated (4 x 5m-ATR distance)']=base&(f.pdl_atr5>=4)
        k=(f15.atr/f15.atr5).median();V[f'updated (scaled {4/k:.2f} x 15m ATR)']=base&(f.pdl_atr>=4/k)
    for nm,m in V.items():
        for per,pm in [('ALL',np.ones(len(f),bool)),('IS Jun25-Mar26',~f.oos),('OOS Apr-Oct26',f.oos)]:
            rows.append(dict(tf=tf,version=nm,period=per,**stats(f[m&pm])))
R=pd.DataFrame(rows);R.to_csv('tf15.csv',index=False);f15.to_csv('trades15.csv',index=False)
pd.set_option('display.width',250);print(R.to_string(index=False))
print('15m/5m ATR ratio median',(f15.atr/f15.atr5).median(),'bars15',len(bars15()))
