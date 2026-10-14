import numpy as np,pandas as pd
src=open('bt.py').read().split("df=pd.DataFrame(T)")[0].replace("T.append(dict(time=d.dt[i],","T.append(dict(i=i,j=j,s=s,time=d.dt[i],")
exec(src)
F=pd.read_pickle('_feat.pkl')
nf=~(F.gap_filled&(F.gap_atr.abs()>0.5));keep=((F.dow!='Fri')&nf).values
idx=np.where(keep)[0];df=F.iloc[idx].copy().reset_index(drop=True);TT=[T[k] for k in idx]
O=d.o.values;V=d.v.values.astype(float);I=df.i.values;S=df.s.values;g=d.dt.dt.date.values
first={};last={}
for k,dd in enumerate(g): first.setdefault(dd,k);last[dd]=k
days=sorted(first);pos={dd:q for q,dd in enumerate(days)}
# RSI14
dl=np.r_[0,np.diff(x)];au=pd.Series(np.maximum(dl,0)).ewm(alpha=1/14,adjust=False).mean();ad=pd.Series(np.maximum(-dl,0)).ewm(alpha=1/14,adjust=False).mean()
rsi=(100-100/(1+au/ad)).values
vr=(pd.Series(V)/pd.Series(V).rolling(20).mean()).values
flips=np.where(np.r_[False,np.diff(ci)!=0])[0]
f=dict()
A=atr[I]
f['risk_pts']=df.risk_pts;f['risk_atr']=df.risk_atr
f['bar_rng_atr']=(H[I]-L[I])/A;f['body_atr']=S*(x[I]-O[I])/A
f['wick_against_atr']=np.where(S>0,np.minimum(O[I],x[I])-L[I],H[I]-np.maximum(O[I],x[I]))/A
f['wick_with_atr']=np.where(S>0,H[I]-np.maximum(O[I],x[I]),np.minimum(O[I],x[I])-L[I])/A
f['dist_rf_atr']=S*(x[I]-rf[I])/A
bs=[];pr=[];ptr=[];pdh=[];pdl=[];dop=[]
for k,i in enumerate(I):
    pf=flips[flips<i];bs.append(i-pf[-2] if len(pf)>=2 else np.nan)
    dd=g[i];q=pos[dd]
    if q==0: pr+=[np.nan];ptr+=[np.nan];pdh+=[np.nan];pdl+=[np.nan];dop+=[np.nan];continue
    p=days[q-1];a,b=first[p],last[p]+1;ph,pl=H[a:b].max(),L[a:b].min()
    pr.append((ph-pl)/A[k]);ptr.append(S[k]*(x[b-1]-O[a])/A[k])
    pdh.append((x[i]-ph)/A[k]);pdl.append((x[i]-pl)/A[k]);dop.append(S[k]*(x[i]-O[first[dd]])/A[k])
f['bars_since_prev_flip']=bs;f['prevday_range_atr']=pr;f['prevday_trend_with']=ptr
f['vs_pdh_atr']=pdh;f['vs_pdl_atr']=pdl;f['from_dayopen_with_atr']=dop
f['vwap_with_atr']=df.vwap_atr;f['adx']=df.adx;f['atr_pctile']=df.atrp
f['rsi_with']=np.where(S>0,rsi[I],100-rsi[I]);f['vol_ratio']=vr[I];f['hour']=df.hour
f['gap_atr_with']=df.gap_atr*S;f['gap_abs_atr']=df.gap_atr.abs()
f['al15']=df.al15;f['al60']=df.al60;f['al60p']=df.al60p
for n_ in [1,2,3]:
    f[f'mfe_{n_}bar_pts']=[t['_fav'][min(n_,len(t['_fav']))-1]*t['risk_pts'] for t in TT]
    f[f'close_{n_}bar_pts']=[t['_cl'][min(n_,len(t['_cl']))-1]*t['risk_pts'] for t in TT]
X=pd.DataFrame(f);X.insert(0,'time',df.time);X.insert(1,'dir',df.dir);X['plan_pts']=df.ro*df.risk;X['sl_hit']=df.sl_hit
X['loser']=X.plan_pts<0;X['oos']=df.oos.values
from scipy.stats import mannwhitneyu
rk=[]
for c in f:
    if c.startswith(('mfe_','close_')): continue
    a=X[c].astype(float);m=a.notna()
    def auc(mask):
        w=a[m&mask&~X.loser];l=a[m&mask&X.loser]
        return mannwhitneyu(w,l).statistic/(len(w)*len(l))
    rk.append(dict(feature=c,AUC_all=auc(True),AUC_IS=auc(~X.oos),AUC_OOS=auc(X.oos),win_med=a[~X.loser].median(),lose_med=a[X.loser].median()))
RK=pd.DataFrame(rk);RK['sep']=(RK.AUC_all-.5).abs();RK=RK.sort_values('sep',ascending=False)
pd.set_option('display.width',250)
print((X.loser).sum(),'losers of',len(X));print(RK.round(3).to_string(index=False))
def stat(pts,mask=None):
    out={}
    for per,pm in [('ALL',np.ones(len(X),bool)),('IS',~X.oos.values),('OOS',X.oos.values)]:
        mm=pm if mask is None else pm&mask;p=np.asarray(pts)[mm];eq=np.cumsum(p)
        dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max() if len(p) else 0
        out[per]=(len(p),(p>0).mean(),p.sum(),dd)
    return out
base=X.plan_pts.values
rows=[]
def rule(name,keepmask):
    s=stat(base,keepmask);L_=X.loser.values
    r=dict(rule=name,losers_removed=int((L_&~keepmask).sum()),winners_removed=int((~L_&~keepmask).sum()))
    for per,(n,w,net,dd) in s.items(): r.update({f'{per}_n':n,f'{per}_win':round(w,3),f'{per}_net':round(net),f'{per}_dd':round(dd)})
    rows.append(r)
rule('baseline',np.ones(len(X),bool))
for c in RK.feature[:12]:
    a=X[c].astype(float).values
    for q in [0.1,0.2,0.3,0.7,0.8,0.9]:
        th=np.nanquantile(a,q)
        km=~(a<th) if q<.5 else ~(a>th)
        rule(f'{c} {"<" if q<.5 else ">"} {th:.2f} skip',km)
R=pd.DataFrame(rows);good=R[(R.IS_net>R.IS_net[0])&(R.OOS_net>R.OOS_net[0])]
print(good.sort_values('ALL_net',ascending=False).head(25).to_string(index=False))
X.to_pickle('_lx.pkl');R.to_csv('_lrules.csv',index=False)
import pickle;pickle.dump(TT,open('_tt.pkl','wb'))
