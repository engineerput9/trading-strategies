import json,pickle,numpy as np,pandas as pd,datetime as dt
from scipy.stats import norm
from scipy.optimize import brentq
IST='Asia/Kolkata'; r=0.065
t=pd.read_csv('dynamic_trades.csv',parse_dates=['entry_time','exit_time'])
B5=pickle.load(open('_add.pkl','rb'))[0]; d=B5['d']
raw=json.load(open('optraw.json'))
def ser(s):
    c=raw.get(s) or []
    if not c: return None
    x=pd.DataFrame(c,columns='t o h l c v'.split()).drop_duplicates('t')
    x.index=pd.DatetimeIndex(pd.to_datetime(x.t,unit='s',utc=True)).tz_convert(IST); return x.sort_index()
def b76(F,K,T,s,cp):
    if T<=0: return max(F-K,0) if cp=='CE' else max(K-F,0)
    d1=(np.log(F/K)+.5*s*s*T)/(s*np.sqrt(T)); d2=d1-s*np.sqrt(T); D=np.exp(-r*T)
    return D*(F*norm.cdf(d1)-K*norm.cdf(d2)) if cp=='CE' else D*(K*norm.cdf(-d2)-F*norm.cdf(-d1))
def iv(p,F,K,T,cp):
    try: return brentq(lambda s:b76(F,K,T,s,cp)-p,0.01,5)
    except Exception: return np.nan
# expiry calendar: fut ~19th (prev weekday), option 2 business days earlier
def bd_back(x,n):
    while x.weekday()>4: x-=dt.timedelta(1)
    for _ in range(n):
        x-=dt.timedelta(1)
        while x.weekday()>4: x-=dt.timedelta(1)
    return x
def optexp(y,m): return bd_back(dt.date(y,m,19),2)
def nearest(day):
    y,m=day.year,day.month
    e=optexp(y,m)
    if day>e: m+=1; y+=m>12; m=(m-1)%12+1; e=optexp(y,m)
    return e
def T_of(ts,e): return max((pd.Timestamp(dt.datetime.combine(e,dt.time(23,30))).tz_localize(IST)-ts).total_seconds(),0)/(365*86400)
# realized vol: daily closes from 5m continuous, 20d
dd=d.copy(); dd['dt']=pd.to_datetime(dd['dt']); dc=dd.groupby(dd.dt.dt.date)['c'].last()
rv=np.log(dc).diff().rolling(20,min_periods=5).std().bfill()*np.sqrt(252); rv.index=pd.to_datetime(rv.index)
# implied vol from OCT ATM, Aug15-Oct12 (Oct expiry)
EOCT=optexp(2026,10); fut=ser('MCX:CRUDEOIL26OCTFUT'); ivrows=[]
for ts,F in fut.c.items():
    if ts.hour<10 or ts.date()>=EOCT: continue
    if ts.minute not in (0,30): continue
    K=int(round(F/100)*100); T=T_of(ts,EOCT); v=[]
    for cp in('CE','PE'):
        o=ser(f'MCX:CRUDEOIL26OCT{K}{cp}')
        if o is not None and ts in o.index: v.append(iv(o.c[ts],F,K,T,cp))
    if v: ivrows.append((ts.date(),np.nanmean(v)))
ivd=pd.DataFrame(ivrows,columns=['day','iv']).groupby('day').iv.median(); ivd.index=pd.to_datetime(ivd.index)
cmp=pd.concat([ivd,rv],axis=1,keys=['iv','rv']).dropna()
ratio=(cmp.iv/cmp.rv).median(); print('IV days',len(ivd),'median IV',ivd.median().round(3),'median RV',cmp.rv.median().round(3),'IV/RV',round(ratio,2))
print(cmp.resample('W').mean().round(3).to_string())
def ivfor(day):
    v=rv.asof(pd.Timestamp(day)); return float(np.clip(ratio*v,0.2,1.2))
# costs per lot (Rs)
def costs(pb,ps):
    tb,ts_=pb*100,ps*100; brk=40; ctt=0.0005*ts_; exch=0.000418*(tb+ts_); sebi=1e-6*(tb+ts_); stamp=0.00003*tb
    return brk+ctt+exch+sebi+stamp+0.18*(brk+exch+sebi)
rows=[]
for i,x in t.iterrows():
    cp='CE' if x.direction=='long' else 'PE'; e=nearest(x.entry_time.date())
    K=int(round(x.entry_price/50)*50); Te,Tx=T_of(x.entry_time,e),T_of(x.exit_time,e)
    ivx=ivfor(x.entry_time.date()-dt.timedelta(1))
    rec=dict(entry_time=x.entry_time,exit_time=x.exit_time,direction=x.direction,mode=x['mode'],fut_entry=x.entry_price,fut_exit=x.exit_price,fut_pts=x.pts,exit_reason=x.exit_reason,
             opt=cp,strike=K,opt_expiry=e,dte_entry=round(Te*365,2),expiry_week=(e-x.entry_time.date()).days<=6,iv_model=round(ivx,3))
    for tag,s in (('m',ivx),('m_lo',max(ivx-.10,.05)),('m_hi',ivx+.10)):
        pe,px=b76(x.entry_price,K,Te,s,cp),b76(x.exit_price,K,Tx,s,cp); rec[f'{tag}_entry']=round(pe,2); rec[f'{tag}_exit']=round(px,2); rec[f'{tag}_pts']=round(px-pe,2)
    rec['source']='model'
    if e==EOCT:
        o=ser(f'MCX:CRUDEOIL26OCT{K}{cp}')
        if o is not None:
            pe=o.c.asof(x.entry_time); px=o.c.asof(x.exit_time)
            stale=(x.entry_time not in o.index) or (x.exit_time not in o.index)
            rec.update(real_entry=pe,real_exit=px,real_pts=px-pe,real_stale=stale,source='real')
            F=fut.c.asof(x.entry_time); rec['real_iv_entry']=round(iv(pe,F,K,Te,cp),3); rec['fut_oct_entry']=F
    rows.append(rec)
o=pd.DataFrame(rows)
o['prem_entry']=np.where(o.source=='real',o.get('real_entry'),o.m_entry); o['prem_exit']=np.where(o.source=='real',o.get('real_exit'),o.m_exit)
o['gross_pts']=o.prem_exit-o.prem_entry
o['cost_rs']=[costs(a,b) for a,b in zip(o.prem_entry,o.prem_exit)]
for s in(1,2): o[f'net_pts_slip{s}']=(o.gross_pts-o.cost_rs/100-2*s).round(2)
o.to_csv('options_pnl.csv',index=False)
# model check on real trades + pseudo check: Aug15-Sep16 trades priced with OCT series (next month) real vs model
chk=[]
for i,x in t[(t.entry_time>='2026-08-17')].iterrows():
    cp='CE' if x.direction=='long' else 'PE'; os_=ser(f'MCX:CRUDEOIL26OCT{int(round(x.entry_price/50)*50)}{cp}')
    F0=fut.c.asof(x.entry_time); F1=fut.c.asof(x.exit_time); K=int(round(F0/50)*50); os_=ser(f'MCX:CRUDEOIL26OCT{K}{cp}')
    if os_ is None: continue
    s=ivfor(x.entry_time.date()-dt.timedelta(1))
    me,mx=b76(F0,K,T_of(x.entry_time,EOCT),s,cp),b76(F1,K,T_of(x.exit_time,EOCT),s,cp)
    chk.append(dict(entry=x.entry_time,real_e=os_.c.asof(x.entry_time),mod_e=me,real_d=os_.c.asof(x.exit_time)-os_.c.asof(x.entry_time),mod_d=mx-me))
c=pd.DataFrame(chk); c.to_csv('_optcheck.csv',index=False)
print('check n',len(c),'entry prem MAPE',(abs(c.mod_e-c.real_e)/c.real_e).mean().round(3),'bias',((c.mod_e-c.real_e)/c.real_e).mean().round(3),
 'P&L corr',c[['real_d','mod_d']].corr().iloc[0,1].round(3),'MAE pnl',abs(c.real_d-c.mod_d).mean().round(1),'sum real',c.real_d.sum().round(1),'sum model',c.mod_d.sum().round(1))
