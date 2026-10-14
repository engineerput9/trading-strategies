import json,pandas as pd,numpy as np
d=json.load(open('raw.json'))
c=pd.DataFrame(d['cont'],columns='t o h l c v'.split()).drop_duplicates('t').sort_values('t').reset_index(drop=True)
c['dt']=pd.to_datetime(c.t,unit='s',utc=True).dt.tz_convert('Asia/Kolkata');c['day']=c.dt.dt.date
O,H,L,C=c.o.values,c.h.values,c.l.values,c.c.values;DAY=c.day.values;n=len(c)
idx={t:i for i,t in enumerate(c.dt)}
T=pd.read_csv('dynamic_trades.csv',parse_dates=['signal_time','entry_time','exit_time'])
def roll(d0,d1):  # approx MCX crude expiry/roll window: 16th-21st of month
    for dd in pd.date_range(d0,d1):
        if 16<=dd.day<=21 and dd.date()!=d0: return True
    return False
def sim(maxd,opp):
    R=[];busy=None
    for k,t in T.iterrows():
        if busy is not None and t.entry_time<busy: continue
        s=1 if t.direction=='long' else -1;ie=idx[t.entry_time];e=t.entry_price;sl,tp=t.stop_price,t.target_price
        nxt=T[T.entry_time>t.entry_time];opps=nxt[nxt.direction!=t.direction]
        oppt=idx[opps.entry_time.iloc[0]] if (opp and len(opps)) else None
        sess=0;j=ie+1;why=None
        while j<n:
            if DAY[j]!=DAY[j-1]:
                sess+=1
                if maxd==0 or (maxd is not None and sess>maxd): j-=1;px=C[j];why='time';break
            if oppt is not None and j==oppt: px=C[j];why='opp_signal';break
            if s*(sl-O[j])>=0: px=O[j];why='stop_gap' if DAY[j]!=DAY[j-1] else 'stop';break
            if s*(O[j]-tp)>=0: px=O[j];why='target_gap' if DAY[j]!=DAY[j-1] else 'target';break
            if (L[j]<=sl) if s>0 else (H[j]>=sl): px=sl;why='stop';break
            if (H[j]>=tp) if s>0 else (L[j]<=tp): px=tp;why='target';break
            j+=1
        else: j=n-1;px=C[j];why='open_eod_data'
        if why=='time' and maxd==0: why='session_end'
        busy=c.dt[j]
        R.append(dict(entry_time=t.entry_time,dir=t.direction,mode=t['mode'],entry=e,stop=sl,target=tp,exit_time=c.dt[j],exit_price=px,reason=why,pts=round(s*(px-e),2),
          hold_h=(c.dt[j]-t.entry_time).total_seconds()/3600,sessions=sess,roll=roll(t.entry_time.date(),c.dt[j].date()) and sess>0))
    return pd.DataFrame(R)
def st(r):
    p=r.pts;w=p[p>0];l=p[p<=0];eq=p.cumsum();dd=(eq.cummax().clip(lower=0)-eq).max()
    ls=m=0
    for v in p: m=m+1 if v<=0 else 0;ls=max(ls,m)
    IS=r.entry_time<pd.Timestamp('2026-04-01',tz='Asia/Kolkata')
    return dict(n=len(r),win=round(100*(p>0).mean(),1),net=round(p.sum()),avgW=round(w.mean(),1),avgL=round(l.mean(),1),maxDD=round(dd),streak=ls,worst=round(p.min()),hold_h=round(r.hold_h.mean(),1),IS=round(p[IS].sum()),OOS=round(p[~IS].sum()),rolls=int(r.roll.sum()))
V={'base_session_end':(0,False),'hold1d':(1,False),'hold2d':(2,False),'hold5d':(5,False),'unlimited':(None,False),
   'hold1d_opp':(1,True),'hold2d_opp':(2,True),'hold5d_opp':(5,True),'unlimited_opp':(None,True)}
rows=[];alls=[]
for k,(m,o) in V.items():
    r=sim(m,o);r['variant']=k;alls.append(r)
    rows.append(dict(variant=k,**st(r)));rows.append(dict(variant=k+'_exRoll',**st(r[~r.roll])))
S=pd.DataFrame(rows);print(S.to_string())
pd.concat(alls).to_csv('overnight.csv',index=False);S.to_csv('overnight_summary.csv',index=False)
b=alls[0];print(b.reason.value_counts())
se=b[b.reason=='session_end'];print(se.groupby('mode').pts.agg(['count','sum','mean']));print('all se',len(se),se.pts.sum(),se.pts.mean())
print(b[b.pts<=0].groupby('mode').pts.agg(['count','mean']),b[b.pts<=0].pts.mean())
print('orig csv check',T.pts.sum(),T.exit_reason.value_counts().to_dict())
u=alls[4];print(u.reason.value_counts().to_dict());print(u.nsmallest(5,'pts')[['entry_time','mode','reason','pts','sessions','roll']])
