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
day=d.dt.dt.date.values;T=[];done=None
start=3*per*2  # warmup
for i in range(start,n):
    if day[i]==done: continue
    L_=lc[i] and ci[i-1]==-1;S_=sc[i] and ci[i-1]==1
    if not(L_ or S_): continue
    done=day[i];e=x[i];a=atr[i]
    if L_: raw=L[i-10:i].min(); sl=e-a if e-raw<a else raw; s=1
    else: raw=H[i-10:i].max(); sl=e+a if raw-e<a else raw; s=-1
    R=abs(e-sl); j=i+1; fav=[];adv=[]
    while j<n and day[j]==day[i]:
        fav.append(s*((H[j] if s>0 else L[j])-e)); adv.append(s*(e-(L[j] if s>0 else H[j]))); j+=1
    if not fav: continue
    fav=np.maximum.accumulate(fav);adv=np.maximum.accumulate(adv)
    hit=np.where(adv>=R)[0]; k=hit[0] if len(hit) else len(adv)-1
    mfe_sl=fav[k-1] if len(hit) and k>0 else (0 if len(hit) else fav[k])
    exitpx=x[j-1]
    # original plan: 50% at TP1, 50% at TP2, else SL / EOD close; conservative SL first in same bar
    T.append(dict(time=d.dt[i],dir='BUY' if s>0 else 'SELL',entry=e,sl=round(sl,1),tp1=round(e+s*R,1),tp2=round(e+s*1.5*R,1),risk_pts=round(R,1),
      sl_hit=bool(len(hit)),mfe_pts=round(mfe_sl,1),mfe_R=round(mfe_sl/R,3),mae_pts=round(adv[k],1),mae_R=round(min(adv[k],R)/R,3),
      eod_mfe_R=round(fav[-1]/R,3),eod_mae_R=round(adv[-1]/R,3),eod_close_R=round(s*(exitpx-e)/R,3),_fav=fav/R,_adv=adv/R,_cl=s*(x[i+1:j]-e)/R))
def sim(t,tp,slm):
    f,a,cl=t['_fav'],t['_adv'],t['_cl']
    for q in range(len(f)):
        if a[q]>=slm: return -slm
        if f[q]>=tp: return tp
    return cl[-1]
def orig(t):
    return (sim(t,1,1)+sim(t,1.5,1))/2
df=pd.DataFrame(T);df['orig_R']=[orig(t) for t in T];df['orig_pts']=df.orig_R*df.risk_pts
df.drop(columns=['_fav','_adv','_cl']).to_csv('trades.csv',index=False)
o=[]
P=lambda s:'p10 %.2f p25 %.2f med %.2f p75 %.2f p90 %.2f max %.2f'%tuple(np.percentile(s,[10,25,50,75,90,100]))
o.append(f"Data {d.dt.iloc[0]} -> {d.dt.iloc[-1]}, bars {n}; signals from {df.time.min()} to {df.time.max()}: {len(df)} trades ({(df.dir=='BUY').sum()} buy/{(df.dir=='SELL').sum()} sell)")
o.append(f"Risk pts: median {df.risk_pts.median():.1f}, mean {df.risk_pts.mean():.1f}")
o.append("MFE_R before SL (or EOD): "+P(df.mfe_R)); o.append("MFE pts: "+P(df.mfe_pts))
o.append(f"Largest MFE: {df.mfe_pts.max()} pts / {df.mfe_R.max()}R on {df.loc[df.mfe_R.idxmax(),'time']}")
o.append(f"SL hit rate original stop: {df.sl_hit.mean():.1%}")
o.append("MAE_R full session (no stop): "+P(df.eod_mae_R))
for tp in [1,1.5,2,3,4]: o.append(f"TP {tp}R reached before 1R SL: {(df.mfe_R>=tp).mean():.1%}")
w=df[df.mae_R<1]; o.append("Winning-ish (SL not hit) MAE_R: "+P(w.mae_R) if len(w) else '')
o.append(f"Original plan (50% TP1/50% TP2, SL, EOD exit): win rate {(df.orig_R>0).mean():.1%}, net {df.orig_R.sum():.2f}R, net {df.orig_pts.sum():.0f} pts, expectancy {df.orig_R.mean():.3f}R")
for tp in [1,1.5]:
  s=np.array([sim(t,tp,1) for t in T]);o.append(f"  Single TP {tp}R: win {(s>0).mean():.1%} exp {s.mean():.3f}R net {(s*df.risk_pts).sum():.0f}pts")
g=[]
for slm in [0.5,0.75,1,1.25,1.5,2]:
  for tp in [0.75,1,1.5,2,2.5,3,4,99]:
    s=np.array([sim(t,tp,slm) for t in T]); g.append((slm,tp,(s>0).mean(),s.mean()/slm,(s*df.risk_pts).sum()))
G=pd.DataFrame(g,columns=['sl_x_origR','tp_origR','win','exp_per_risk','net_pts']).sort_values('net_pts',ascending=False)
G.to_csv('grid.csv',index=False);o.append("Top grid (SL & TP in multiples of original risk; tp99=EOD):\n"+G.head(8).round(3).to_string(index=False))
o.append("Bottom:\n"+G.tail(3).round(3).to_string(index=False))
open('summary.txt','w').write("\n".join(o));print("\n".join(o))
