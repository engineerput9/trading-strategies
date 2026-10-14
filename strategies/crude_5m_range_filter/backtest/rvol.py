exec(open('_ss_head.py').read())
import json
raw=json.load(open('raw.json'))['cont']
vmap={pd.Timestamp(r[0],unit='s',tz='Asia/Kolkata'):r[5] for r in raw}
t5=B5['dt'];V=np.array([vmap.get(t,np.nan) for t in t5],float)
print('vol missing',np.isnan(V).sum())
er=np.full(n,np.nan)
for k in range(20,n): er[k]=abs(x[k]-x[k-20])/max(np.abs(np.diff(x[k-20:k+1])).sum(),1e-9)
def simw(ie,ee,s,sl,tp):
    j=ie+1;last=ie
    while j<n and day[j]==day[ie]:
        last=j
        if (L[j]<=sl) if s>0 else (H[j]>=sl): return s*(sl-ee)
        if (H[j]>=tp) if s>0 else (L[j]<=tp): return s*(tp-ee)
        j+=1
    return s*(x[last]-ee)
tod=pd.Series([t.strftime('%H%M') for t in t5]);dser=pd.Series(day)
cum=pd.Series(V).groupby(dser).cumsum().values
# per (day,tod) maps
key={(day[k],tod[k]):k for k in range(n)}
days=B5['days']
def sametime(i,N,arr):
    q=B5['pos'][day[i]];vals=[arr[key[(dd,tod[i])]] for dd in days[max(0,q-N):q] if (dd,tod[i]) in key]
    return np.nanmean(vals) if len(vals)>=max(3,N//2) else np.nan
T=[];done=None
for i in range(B5['start'],n):
    if day[i]==done or B5['flip'][i]==0: continue
    s=B5['flip'][i];done=day[i]
    if i+1>=n or day[i+1]!=day[i]: continue
    f=feats(B5,i,s);dt=B5['dt'][i]
    if not okf(f,dt): continue
    e=x[i];sl0=stopof(B5,i,s);R0=abs(e-sl0);r=persist(i,s,e,sl0,R0)
    if r is None: continue
    ie,ee=r;a=B5['atr'][ie]
    lk=simw(ie,ee,s,e-s*1.5*R0,e+s*1.5*R0);tt=simw(ie,ee,s,ee-s*2*a,e+s*2.5*R0)
    md='tight' if er[ie]>0.294737 else 'locked'
    c2=V[i+1:ie+1].sum();nb=ie-i
    T.append(dict(time=dt,mode=md,locked=lk,tight=tt,pts=tt if md=='tight' else lk,
      rv_tod10=V[i]/sametime(i,10,V),rv_tod20=V[i]/sametime(i,20,V),
      rv_20bar=V[i]/np.nanmean(V[i-20:i]),
      rv_conf=c2/(nb*np.nanmean(V[i-20:i])),
      rv_conf_tod=c2/np.nansum([sametime(k,20,V) for k in range(i+1,ie+1)]),
      rv_cum=cum[ie]/sametime(ie,20,cum)))
D=pd.DataFrame(T);IS=(D.time<OOS).values
print(len(D),round(D.pts.sum()),round(D.pts[IS].sum()),round(D.pts[~IS].sum()))
C=1.7+3
def st(q,tag,mask=None):
    q=pd.Series(np.asarray(q,float));m=~np.isnan(q.values);qq=q[m];isq=IS[m];c=qq.cumsum();ls=cc=0
    for p in qq: cc=cc+1 if p<=0 else 0;ls=max(ls,cc)
    md=D['mode'][m] if mask is None else mask[m]
    return dict(rule=tag,n=len(qq),win=round(100*(qq>0).mean(),1),net=round(qq.sum()),net_cost=round((qq-C).sum()),avg_win=round(qq[qq>0].mean(),1),avg_loss=round(qq[qq<=0].mean(),1),DD=round((c.cummax().clip(lower=0)-c).max()),streak=ls,IS=round(qq[isq].sum()),OOS=round(qq[~isq].sum()),IS_cost=round((qq[isq]-C).sum()),OOS_cost=round((qq[~isq]-C).sum()),tight_n=int((md=='tight').sum()),tight_net=round(qq[(md=='tight').values].sum()),locked_n=int((md=='locked').sum()),locked_net=round(qq[(md=='locked').values].sum()))
rows=[st(D.pts,'baseline')]
F=['rv_tod10','rv_tod20','rv_20bar','rv_conf','rv_conf_tod','rv_cum']
for f in F:
  v=D[f].values
  for th in (0.8,1.0,1.2,1.5):
    rows.append(st(np.where(v<th,np.nan,D.pts),f'{f} skip<{th}'))
  for th in (1.5,2.0,3.0):
    rows.append(st(np.where(v>th,np.nan,D.pts),f'{f} skip>{th}'))
  for scope in ('tight','locked'):
    for th in (0.8,1.0,1.2):
      q=np.where((D['mode']==scope)&(v<th),np.nan,D.pts);rows.append(st(q,f'{f} skip<{th} {scope}-only'))
  # mode switch: IS-chosen
  best=None
  for th in np.quantile(v[IS&~np.isnan(v)],np.linspace(.1,.9,17)):
    for dr in (1,-1):
      for kind in ('replace','and_er'):
        hi=(v>th) if dr>0 else (v<=th)
        use=hi if kind=='replace' else (hi&(D['mode']=='tight').values)
        q=np.where(use,D.tight,D.locked);qi=q[IS].sum()
        if best is None or qi>best[0]: best=(qi,th,dr,kind,q,use)
  _,th,dr,kind,q,use=best
  rows.append(st(q,f"{f} SWITCH({kind}) tight if {'>' if dr>0 else '<='}{th:.2f} [IS-picked]",pd.Series(np.where(use,'tight','locked'))))
R=pd.DataFrame(rows);b=R.iloc[0]
R['beats_both']=(R.IS>b.IS)&(R.OOS>b.OOS)
R['beats_both_cost']=(R.IS_cost>b.IS_cost)&(R.OOS_cost>b.OOS_cost)
R.to_csv('rvol.csv',index=False);pd.set_option('display.width',400);pd.set_option('display.max_rows',500)
print(R.to_string(index=False))
# IS-best skip per feature
for f in F:
  sub=R[R.rule.str.startswith(f+' skip')];bi=sub.loc[sub.IS.idxmax()];print('ISbest',bi.rule,bi.IS,bi.OOS,bi.net)
print(D[F].describe().round(2))
