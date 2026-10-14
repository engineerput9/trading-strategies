exec(open('_ss_head.py').read())
B15=build(d15)
# 15m same-dir flips, available at bar close (start+15m)
f15=[(B15['dt'][k]+pd.Timedelta(minutes=15),B15['flip'][k]) for k in range(B15['start'],B15['n']) if B15['flip'][k]!=0]
t5=B5['dt']
# ADX14 and ER20 on 5m
tr=np.maximum(H-L,np.maximum(abs(H-np.r_[np.nan,x[:-1]]),abs(L-np.r_[np.nan,x[:-1]])));up=np.r_[0,np.diff(H)];dn=np.r_[0,-np.diff(L)]
pdm=np.where((up>dn)&(up>0),up,0);mdm=np.where((dn>up)&(dn>0),dn,0)
def w(a):
    o=np.zeros(n);o[0]=a[0]
    for k in range(1,n): o[k]=o[k-1]*13/14+a[k]/14
    return o
TR=w(np.nan_to_num(tr));pdi=100*w(pdm)/TR;mdi=100*w(mdm)/TR;dx=100*abs(pdi-mdi)/np.maximum(pdi+mdi,1e-9);adx=w(np.nan_to_num(dx))
er=np.full(n,np.nan)
for k in range(20,n): er[k]=abs(x[k]-x[k-20])/max(np.abs(np.diff(x[k-20:k+1])).sum(),1e-9)
# daily mean atr for percentile (prior 20 days only)
dATR=pd.Series({dd:np.nanmean(B5['atr'][B5['first'][dd]:B5['last'][dd]+1]) for dd in B5['days']})
def simw(ie,ee,s,sl,tp,jw=None,tpw=None):
    j=ie+1;last=ie
    while j<n and day[j]==day[ie]:
        last=j
        if (L[j]<=sl) if s>0 else (H[j]>=sl): return s*(sl-ee)
        if (H[j]>=tp) if s>0 else (L[j]<=tp): return s*(tp-ee)
        if jw is not None and j>=jw: tp=tpw
        j+=1
    return s*(x[last]-ee)
T=[];done=None
for i in range(B5['start'],n):
    if day[i]==done or B5['flip'][i]==0: continue
    s=B5['flip'][i];done=day[i]
    if i+1>=n or day[i+1]!=day[i]: continue
    f=feats(B5,i,s);dt=B5['dt'][i]
    if not okf(f,dt): continue
    e=x[i];sl0=stopof(B5,i,s);R0=abs(e-sl0);r=persist(i,s,e,sl0,R0)
    if r is None: continue
    ie,ee=r;a=B5['atr'][ie];dd=day[i];q=B5['pos'][dd]
    prev=dATR[B5['days'][max(0,q-20):q]];pct=(prev<a).mean() if len(prev) else .5
    # 15m same-dir flip after entry, same day -> first 5m bar index at/after its close
    jw=None
    for tc,fs in f15:
        if fs==s and tc>t5[ie] and tc.date()==dd:
            jw=int(np.searchsorted(t5.values,tc.to_datetime64()));break
        if tc.date()>dd: break
    row=dict(time=dt,R0=R0,ratr=R0/a,atr=a,pct=pct,pdr=f['pdr'],hr=dt.hour+dt.minute/60,adx=adx[ie],er=er[ie],pdl=f['pdl_atr'],has15=jw is not None)
    lk_sl=e-s*1.5*R0;lk_tp=e+s*1.5*R0
    row['locked']=simw(ie,ee,s,lk_sl,lk_tp)
    row['tight']=simw(ie,ee,s,ee-s*2*a,e+s*2.5*R0)
    for k in (1.5,2,3,4,6):
        for m in (4,6,8,10,12):
            row[f'atr_{k}_{m}']=simw(ie,ee,s,ee-s*k*a,ee+s*m*a)
    for wm in (2,2.5,3):
        row[f'lk15_{wm}']=simw(ie,ee,s,lk_sl,lk_tp,jw,e+s*wm*R0) if jw else row['locked']
        row[f'tt15_{wm}']=simw(ie,ee,s,ee-s*2*a,e+s*1.5*R0,jw,e+s*wm*R0) if jw else simw(ie,ee,s,ee-s*2*a,e+s*1.5*R0)
    T.append(row)
D=pd.DataFrame(T);IS=D.time<OOS
def st(q,tag):
    c=q.cumsum();m=cc=0
    for p in q: cc=cc+1 if p<=0 else 0;m=max(m,cc)
    return dict(rule=tag,n=len(q),win=round(100*(q>0).mean(),1),net=round(q.sum()),avg_win=round(q[q>0].mean(),1),avg_loss=round(q[q<=0].mean(),1),maxDD=round((c.cummax().clip(lower=0)-c).max()),lose_streak=m,IS_net=round(q[IS].sum()),OOS_net=round(q[~IS].sum()),IS_win=round(100*(q[IS]>0).mean(),1),OOS_win=round(100*(q[~IS]>0).mean(),1))
rows=[st(D.locked,'baseline locked'),st(D.tight,'static 2xATR/2.5R0')]
cands=[]
def fam(name,feat,alt='tight',dirs=(1,-1)):
    best=None
    for th in np.unique(np.quantile(D[feat][IS],np.linspace(.1,.9,17))):
        for dr in dirs:
            use=(D[feat]>th) if dr>0 else (D[feat]<=th)
            q=np.where(use,D[alt],D.locked);qi=q[IS.values].sum()
            if best is None or qi>best[0]: best=(qi,th,dr,q)
    _,th,dr,q=best;rows.append(st(pd.Series(q),f"{name}: {alt} if {feat}{'>' if dr>0 else '<='}{th:.3g} else locked"))
for feat in ['pct','atr','pdr','R0','ratr','hr','adx','er','pdl']: fam(feat,feat)
# k*ATR / m*ATR scaled by regime: pick per regime best (k,m) on IS
ac=[c for c in D if c.startswith('atr_')]
for c in ac: rows.append(st(D[c],'static '+c))
for feat in ['pct','atr','R0']:
    best=None
    for th in np.quantile(D[feat][IS],[.33,.5,.67]):
        hi=D[feat]>th;q=D.locked.copy()
        ch=[]
        for msk in (hi,~hi):
            opts=['locked','tight']+ac;b=max(opts,key=lambda c:D[c][IS&msk].sum());q[msk]=D[c][msk] if False else D[b][msk];ch.append(b)
        qi=q[IS].sum()
        if best is None or qi>best[0]: best=(qi,th,ch,q)
    _,th,ch,q=best;rows.append(st(q,f"regime {feat}>{th:.3g}: {ch[0]} else {ch[1]}"))
for c in [c for c in D if c.startswith(('lk15','tt15'))]: rows.append(st(D[c],'15m-confirm widen '+c))
R=pd.DataFrame(rows);b=R.iloc[0]
R['beats_both']=(R.IS_net>b.IS_net)&(R.OOS_net>b.OOS_net)
R.to_csv('dynamic.csv',index=False);pd.set_option('display.width',300);pd.set_option('display.max_colwidth',60)
print(R.to_string(index=False));print('has15',D.has15.sum())
for feat in ['er','pdl','ratr']:
  for th in np.quantile(D[feat][IS],np.linspace(.2,.8,7)):
    dr=-1 if feat in('atr','pdr','R0','hr') else 1
    q=pd.Series(np.where(D[feat]>th,D.tight,D.locked));print(feat,round(th,3),round(q[IS.values].sum()),round(q[~IS.values].sum()),'tight share',round((D[feat]>th).mean(),2))
