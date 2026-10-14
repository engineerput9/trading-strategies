import json,numpy as np,pandas as pd
c=json.load(open('raw.json'))['cont']
d=pd.DataFrame(c,columns='t o h l c v'.split()).drop_duplicates('t').sort_values('t')
d['dt']=pd.to_datetime(d.t,unit='s',utc=True).dt.tz_convert('Asia/Kolkata'); d=d.reset_index(drop=True)
x=d.c.values;n=len(x);per=100
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
dif=np.r_[np.nan,np.abs(np.diff(x))]
r=ema(ema(dif,per),2*per-1)*3
rf=np.zeros(n);rf[0]=x[0]
for i in range(1,n):
    p=rf[i-1];R=r[i]
    if np.isnan(R): rf[i]=x[i];continue  # na range -> pine yields na arithmetic; warmup
    rf[i]=(p if x[i]-R<p else x[i]-R) if x[i]>p else (p if x[i]+R>p else x[i]+R)
up=np.zeros(n);dn=np.zeros(n)
for i in range(1,n):
    up[i]=up[i-1]+1 if rf[i]>rf[i-1] else 0 if rf[i]<rf[i-1] else up[i-1]
    dn[i]=dn[i-1]+1 if rf[i]<rf[i-1] else 0 if rf[i]>rf[i-1] else dn[i-1]
lc=(x>rf)&(up>0)&(np.r_[False,x[1:]!=x[:-1]]);sc=(x<rf)&(dn>0)&(np.r_[False,x[1:]!=x[:-1]])
ci=np.zeros(n)
for i in range(1,n): ci[i]=1 if lc[i] else -1 if sc[i] else ci[i-1]
H,L=d.h.values,d.l.values
tr=np.maximum(H-L,np.maximum(abs(H-np.r_[np.nan,x[:-1]]),abs(L-np.r_[np.nan,x[:-1]])));tr[0]=H[0]-L[0]
atr=np.full(n,np.nan);atr[13]=tr[:14].mean()
for i in range(14,n): atr[i]=(atr[i-1]*13+tr[i])/14
day=d.dt.dt.date.values;start=600
hrs=d.dt.dt.hour.values+d.dt.dt.minute.values/60;dow=d.dt.dt.dayofweek.values;O=d.o.values
first={};last={}
for k,dd in enumerate(day): first.setdefault(dd,k);last[dd]=k
days=sorted(first);prevc={days[q]:x[last[days[q-1]]] for q in range(1,len(days))}
sig={}
for i in range(start,n):
    L_=lc[i] and ci[i-1]==-1;S_=sc[i] and ci[i-1]==1
    if L_ or S_: sig.setdefault(day[i],[]).append((i,1 if L_ else -1))
def run(i,s,end):
    e=x[i];a=atr[i]
    if s>0: raw=L[i-10:i].min(); sl=e-a if e-raw<a else raw
    else: raw=H[i-10:i].max(); sl=e+a if raw-e<a else raw
    R=abs(e-sl)
    def leg(tp):
        for j in range(i+1,end+1):
            if s*(e-(L[j] if s>0 else H[j]))>=R: return -1
            if s*((H[j] if s>0 else L[j])-e)>=tp*R: return tp
        return s*(x[end]-e)/R
    return R,(leg(1)+leg(1.5))/2,leg(1)
rows=[]
for cap in [1,2,3,99]:
  for dd,S in sig.items():
    S=S[:cap]
    for q,(i,s) in enumerate(S):
        end=S[q+1][0] if q+1<len(S) else last[dd]
        if end<=i: continue
        R,pr,r1=run(i,s,end)
        f0=first[dd];pc=prevc.get(dd,np.nan);gap=O[f0]-pc;ga=gap/atr[f0]
        lo=L[f0:i+1].min();hi=H[f0:i+1].max();gf=(lo<=pc) if gap>0 else (hi>=pc) if gap<0 else True
        rows.append(dict(cap=cap,time=d.dt[i],nth=q+1,dir=s,hour=hrs[i],risk=R,plan_R=pr,r1_R=r1,plan_pts=pr*R,r1_pts=r1*R,
          fri=dow[i]==4,gapfill=bool(gf and abs(ga)>0.5),oos=d.dt[i]>=pd.Timestamp('2026-04-01',tz='Asia/Kolkata')))
D=pd.DataFrame(rows);D.to_csv('multi_signal_trades.csv',index=False)
def st(g):
    p=g.sort_values('time').plan_pts;eq=p.cumsum();dd=(eq.cummax().clip(lower=0)-eq).max()
    return pd.Series(dict(signals=len(g),plan_win=(g.plan_R>0).mean()*100,r1_win=(g.r1_R>0).mean()*100,net_pts=p.sum(),r1_net=g.r1_pts.sum(),exp_R=g.plan_R.mean(),maxDD=dd))
out=[]
for filt in ['none','skipFri+gapfill']:
  X=D if filt=='none' else D[~D.fri&~D.gapfill]
  for per,Y in [('all',X),('IS',X[~X.oos]),('OOS',X[X.oos])]:
    for cap,g in Y.groupby('cap'): out.append(dict(filter=filt,period=per,variant=f'max{cap}' if cap<99 else 'unlimited',**st(g)))
  U=X[X.cap==99].copy();U['bucket']=pd.cut(U.hour,[0,12,15,18,21,24],labels=['09-12','12-15','15-18','18-21','21-24'],right=False)
  U['nthb']=np.where(U.nth==1,'1st',np.where(U.nth==2,'2nd','3rd+'))
  for per,Y in [('all',U),('IS',U[~U.oos]),('OOS',U[U.oos])]:
    for nb,g in Y.groupby('nthb'): out.append(dict(filter=filt,period=per,variant=f'unl {nb} only',**st(g)))
    for (nb,b),g in Y[Y.nth>1].groupby(['nthb','bucket'],observed=True): out.append(dict(filter=filt,period=per,variant=f'unl {nb} {b}',**st(g)))
R=pd.DataFrame(out).round(2);R.to_csv('multi_signal.csv',index=False)
pd.set_option('display.width',250);print(R.to_string(index=False))
