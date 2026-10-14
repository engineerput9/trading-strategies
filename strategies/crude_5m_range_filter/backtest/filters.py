import numpy as np,pandas as pd
src=open('bt.py').read().split("df=pd.DataFrame(T)")[0].replace("T.append(dict(time=d.dt[i],","T.append(dict(i=i,j=j,s=s,time=d.dt[i],")
exec(src)
df=pd.DataFrame(T)
# features
C=pd.Series(x,index=d.dt)
def htf(rule):
    r=C.resample(rule,label='right',closed='right').last().dropna()
    e50=r.ewm(span=50,adjust=False).mean();e200=r.ewm(span=200,adjust=False).mean()
    f=pd.DataFrame({'c':r,'t':np.sign(e50-e200),'p':np.sign(r-e50)})
    return f.reindex(d.dt,method='ffill').values  # completed HTF bars only (right-labelled)
h15=htf('15min');h60=htf('60min')
e50=pd.Series(x).ewm(span=50,adjust=False).mean().values;e200=pd.Series(x).ewm(span=200,adjust=False).mean().values
# ADX14
up_=np.r_[0,np.diff(H)];dn_=np.r_[0,-np.diff(L)]
pdm=np.where((up_>dn_)&(up_>0),up_,0);mdm=np.where((dn_>up_)&(dn_>0),dn_,0)
w=lambda a:pd.Series(a).ewm(alpha=1/14,adjust=False).mean().values
tr_s=w(tr);pdi=100*w(pdm)/tr_s;mdi=100*w(mdm)/tr_s
adx=w(100*abs(pdi-mdi)/(pdi+mdi+1e-9))
tp_=(H+L+x)/3;v=d.v.values.astype(float);g=d.dt.dt.date.values
vw=(pd.Series(tp_*v).groupby(g).cumsum()/pd.Series(v).groupby(g).cumsum().replace(0,np.nan)).values
atr_pct=pd.Series(atr).rolling(288*20,min_periods=500).rank(pct=True).values
I=df.i.values;S=df.s.values
df['hour']=df.time.dt.hour+df.time.dt.minute/60;df['dow']=df.time.dt.day_name().str[:3]
df['al15']=h15[I,1]*S;df['al60']=h60[I,1]*S;df['al60p']=h60[I,2]*S;df['al5']=np.sign(e50-e200)[I]*S
df['risk_atr']=df.risk_pts/atr[I];df['adx']=adx[I];df['atrp']=atr_pct[I]
df['vwap_atr']=S*(x[I]-vw[I])/atr[I]

# gap features
O=d.o.values;first={};last={}
for k,dd in enumerate(g):
    first.setdefault(dd,k);last[dd]=k
days=sorted(first);prevc={days[q]:x[last[days[q-1]]] for q in range(1,len(days))}
gp=[];gpp=[];gpa=[];gfill=[]
for t in df.itertuples():
    dd=g[t.i];f0=first[dd];pc=prevc.get(dd,np.nan);gap=O[f0]-pc
    gp.append(gap);gpp.append(100*gap/pc);gpa.append(gap/atr[f0])
    lo=L[f0:t.i+1].min();hi=H[f0:t.i+1].max()
    gfill.append(bool(lo<=pc) if gap>0 else bool(hi>=pc) if gap<0 else True)
df['gap_pts']=gp;df['gap_pct']=gpp;df['gap_atr']=gpa;df['gap_filled']=gfill
df['gap_with']=np.sign(df.gap_pts)*S
df['oos']=df.time>=pd.Timestamp('2026-04-01',tz='Asia/Kolkata')
# candle confirmation: enter on break of signal bar high/low within next 3 bars same day, same SL
def conf(t):
    i,j,s=t.i,t.j,t.s;lvl=H[i] if s>0 else L[i];sl=t.sl
    for q in range(i+1,min(i+4,j)):
        if (s>0 and H[q]>lvl) or (s<0 and L[q]<lvl):
            e=max(lvl,d.o.values[q]) if s>0 else min(lvl,d.o.values[q]);R=abs(e-sl)
            if R<=0: return None
            fav=[];adv=[]
            for k in range(q,j):
                hh=H[k] if k>q or s<0 else H[k]; fav.append(s*((H[k] if s>0 else L[k])-e));adv.append(s*(e-(L[k] if s>0 else H[k])))
            f=np.maximum.accumulate(fav)/R;a=np.maximum.accumulate(adv)/R;cl=s*(x[j-1]-e)/R
            return f,a,cl,R
    return None
def sim2(f,a,cl,tp):
    for q in range(len(f)):
        if a[q]>=1: return -1
        if f[q]>=tp: return tp
    return cl
w1=[];wo=[];rr=[];took=[]
for k,t in df.iterrows():
    tt=T[k]
    w1.append(sim(tt,1,1));wo.append((sim(tt,1,1)+sim(tt,1.5,1))/2)
df['r1']=w1;df['ro']=wo;df['risk']=df.risk_pts
cf=df.copy();res=[conf(t) for t in df.itertuples()]
cf=cf[[r is not None for r in res]].copy();rv=[r for r in res if r is not None]
cf['r1']=[sim2(f,a,c,1) for f,a,c,R in rv];cf['ro']=[(sim2(f,a,c,1)+sim2(f,a,c,1.5))/2 for f,a,c,R in rv];cf['risk']=[R for *_,R in rv]
rows=[]
def rep(name,m,base=df):
    for per,mask in [('ALL',slice(None)),('IS',~base.oos),('OOS',base.oos)]:
        b=base[mask];b=b[m[mask]] if not isinstance(m,slice) else b
        if len(b)==0: continue
        rows.append(dict(filter=name,period=per,n=len(b),win_1R=(b.r1>0).mean(),win_orig=(b.ro>0).mean(),
          net_pts_orig=(b.ro*b.risk).sum(),exp_R_orig=b.ro.mean(),exp_pts_orig=(b.ro*b.risk).mean(),net_pts_1R=(b.r1*b.risk).sum()))
A=lambda c:np.ones(len(df),bool)&c.values
rep('baseline',slice(None))
hr=df.hour
for nm,c in [('skip 09:00 open',hr>=9.1),('09-10',hr<10),('10-14',(hr>=10)&(hr<14)),('14-17',(hr>=14)&(hr<17)),('17-23:30',hr>=17),('skip 09-10',hr>=10)]: rep('time '+nm,A(c))
for nm in ['al5','al15','al60','al60p']: rep(f'HTF align {nm}',A(df[nm]>0)); rep(f'HTF against {nm}',A(df[nm]<0))
for v_ in [1.0,1.25,1.5,2.0]: rep(f'risk<= {v_}xATR',A(df.risk_atr<=v_))
for v_ in [60,80,100,150]: rep(f'risk<= {v_}pts',A(df.risk_pts<=v_))
for v_ in [20,25,30]: rep(f'ADX>= {v_}',A(df.adx>=v_)); rep(f'ADX< {v_}',A(df.adx<v_))
rep('ATR pct>=0.5',A(df.atrp>=0.5));rep('ATR pct<0.5',A(df.atrp<0.5))
for v_ in [0,0.5,1.0]: rep(f'VWAP side >{v_}ATR',A(df.vwap_atr>v_))
rep('VWAP within 1.5ATR',A(df.vwap_atr.abs()<=1.5));rep('VWAP opposite side',A(df.vwap_atr<0))
for dn in ['Mon','Tue','Wed','Thu','Fri']: rep('dow '+dn,A(df.dow==dn))
ga=df.gap_atr
for nm,c in [('gap up >0.5ATR',ga>0.5),('gap down <-0.5ATR',ga<-0.5),('gap flat |g|<=0.5ATR',ga.abs()<=0.5),('gap big |g|>1ATR',ga.abs()>1)]: rep(nm,A(c))
rep('gap: signal WITH gap',A((df.gap_with>0)&(ga.abs()>0.5)));rep('gap: signal AGAINST gap',A((df.gap_with<0)&(ga.abs()>0.5)))
rep('gap filled before signal',A(df.gap_filled&(ga.abs()>0.5)));rep('gap NOT filled before signal',A(~df.gap_filled&(ga.abs()>0.5)))
rep('skip 09:00 signals on gap>0.5ATR',A(~((hr<9.1)&(ga.abs()>0.5))))
rep('candle confirm (break sig bar, 3 bars)',np.ones(len(cf),bool),cf)
P=pd.DataFrame(rows)
P.to_csv('_tmp.csv',index=False)
df.to_pickle('_feat.pkl');cf.to_pickle('_cf.pkl')
pd.set_option('display.width',250);pd.set_option('display.max_rows',500)
print(P.round(3).to_string(index=False))
print(df.risk_atr.describe().round(2).to_string())
for q in [3,4,5,6]: rep(f'risk<= {q}xATR',A(df.risk_atr<=q))
rep('skip Fri',A(df.dow!='Fri'))
nf=~(df.gap_filled&(df.gap_atr.abs()>0.5))
rep('gap not filled (or no gap)',A(nf))
combos={'C1 skip Fri + ADX<25':(df.dow!='Fri')&(df.adx<25),
'C2 skip Fri + gap not filled':(df.dow!='Fri')&nf,
'C3 skip Fri + ADX<25 + gap not filled':(df.dow!='Fri')&(df.adx<25)&nf,
'C4 ADX<25 + ATR pct>=0.5':(df.adx<25)&(df.atrp>=0.5),
'C5 skip Fri + ATR pct>=0.5':(df.dow!='Fri')&(df.atrp>=0.5),
'C6 skip Fri + ADX<25 + ATR pct>=0.5':(df.dow!='Fri')&(df.adx<25)&(df.atrp>=0.5),
'C7 against 1h EMA trend + skip Fri':(df.al60<0)&(df.dow!='Fri')}
for k,c in combos.items(): rep(k,A(c))
P=pd.DataFrame(rows).round(4);P.to_csv('filters.csv',index=False)
print(P.iloc[len(P)-3*14:].round(3).to_string(index=False))
