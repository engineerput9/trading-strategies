exec(open('_ss_head.py').read())
import pandas as pd,numpy as np
T=pd.read_csv('dynamic_trades.csv')
t5=pd.DatetimeIndex(B5['dt'])
def sim(ie,ee,s,sl,tp):
    j=ie+1;last=ie
    while j<n and day[j]==day[ie]:
        last=j
        if (L[j]<=sl) if s>0 else (H[j]>=sl): return sl,'stop',t5[j]
        if (H[j]>=tp) if s>0 else (L[j]<=tp): return tp,'target',t5[j]
        j+=1
    return x[last],'session_end',t5[last]
T['ie']=[t5.get_loc(pd.Timestamp(v)) for v in T.entry_time]
T['s']=np.where(T.direction=='long',1,-1)
def run(fix,modes):
    rows=[]
    for _,r in T.iterrows():
        r=r.copy();s=r.s;ee=r.entry_price;sl=r.stop_price;tp=r.target_price
        if r['mode'] in modes:
            sd=abs(ee-sl);k={'locked':1.5,'tight':None}
            if fix=='A': tp=ee+s*(1.5*r.R0 if r['mode']=='locked' else abs(r.target_price-r.signal_price))
            elif fix=='A2_1.0': tp=ee+s*sd
            elif fix=='A2_1.5': tp=ee+s*1.5*sd
            elif fix=='B' and s*(tp-ee)<sd: continue
            elif fix=='max': tp=ee+s*max(s*(tp-ee),sd)
        px,why,et=sim(r.ie,ee,s,sl,tp)
        r.target_price=round(tp,2);r.target_pts=round(abs(tp-ee),2);r.stop_pts=round(abs(sl-ee),2)
        r.exit_price=px;r.exit_reason=why;r.exit_time=et;r.pts=round(s*(px-ee),2);r.win=int(r.pts>0)
        rows.append(r)
    return pd.DataFrame(rows)
def stats(d,name):
    p=d.pts.values;eq=np.cumsum(p);dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
    ls=c=0
    for v in p: c=c+1 if v<=0 else 0;ls=max(ls,c)
    is_=d[d.day<'2026-04-01'].pts.sum();oos=d[d.day>='2026-04-01'].pts.sum()
    return dict(variant=name,n=len(d),win=round(100*(p>0).mean(),1),net=round(p.sum()),avg_win=round(p[p>0].mean(),1),avg_loss=round(p[p<=0].mean(),1),maxDD=round(dd),lose_streak=ls,IS=round(is_),OOS=round(oos))
base=run(None,[]);out=[stats(base,'baseline')]
D={}
for f in ['A','A2_1.0','A2_1.5','B','max']:
    for m,lab in [(['locked'],'locked'),(['locked','tight'],'both')]:
        D[f+'_'+lab]=d=run(f,m);out.append(stats(d,f+'_'+lab))
R=pd.DataFrame(out);R['dIS']=R.IS-R.IS[0];R['dOOS']=R.OOS-R.OOS[0];R.to_csv('rrfix.csv',index=False);print(R.to_string())
for m in ['locked','tight']:
    q=T[T['mode']==m];b=q[q.stop_pts>q.target_pts];print(m,len(q),'stop>target:',len(b),'pts',round(b.pts.sum(),1),'wins',b.win.sum())
import pickle;pickle.dump(D,open('_rr.pkl','wb'))
