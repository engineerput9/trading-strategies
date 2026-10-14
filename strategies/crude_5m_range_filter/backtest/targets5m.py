exec(open('add5m.py').read())
def sim(B,i,e,s,stop,R,tps=(1,1.5),mg=None):
    H,L,x,day=B['H'],B['L'],B['x'],B['day'];legs=[[stop,None if t is None else e+s*t*R,None] for t in tps];j=i+1;lastj=i
    while j<B['n'] and day[j]==day[i]:
        lastj=j
        for lg in legs:
            if lg[2] is not None: continue
            if (L[j]<=lg[0]) if s>0 else (H[j]>=lg[0]): lg[2]=lg[0]
            elif lg[1] is not None and ((H[j]>=lg[1]) if s>0 else (L[j]<=lg[1])): lg[2]=lg[1]
        if mg and legs[1][2] is None: mg(j,legs,e,s,R)
        if all(lg[2] is not None for lg in legs): break
        j+=1
    return float(np.mean([s*((lg[2] if lg[2] is not None else x[lastj])-e) for lg in legs]))
B5=build(d5);OOS=pd.Timestamp('2026-04-01',tz='Asia/Kolkata')
n=B5['n'];x,H,L,ci,day=B5['x'],B5['H'],B5['L'],B5['ci'],B5['day']
def persist(i,s,e,sl,R):
    j=i+2
    if j>=n or day[j]!=day[i] or (ci[i:j+1]!=s).any(): return None
    if ((L[i+1:j+1]<=sl).any() if s>0 else (H[i+1:j+1]>=sl).any()): return None
    return j,x[j]
def be_after_tp1(j,legs,e,s,R):
    if legs[0][2] is not None and legs[0][2]!=legs[0][0]: legs[1][0]=e
def trailR(j,legs,e,s,R):  # after TP1, trail 1R behind best close
    if legs[0][2] is not None and legs[0][2]!=legs[0][0]:
        ns=x[j]-s*R; legs[1][0]=max(legs[1][0],ns) if s>0 else min(legs[1][0],ns)
def run(stopm,conf,tps,mg):
    T=[];done=None
    for i in range(B5['start'],n):
        if day[i]==done or B5['flip'][i]==0: continue
        s=B5['flip'][i];done=day[i]
        if i+1>=n or day[i+1]!=day[i]: continue
        f=feats(B5,i,s);dt=B5['dt'][i]
        if not okf(f,dt): continue
        e=x[i];sl0=stopof(B5,i,s);R0=abs(e-sl0);ie,ee=i,e
        if conf:
            r=persist(i,s,e,sl0,R0)
            if r is None: continue
            ie,ee=r
        sl=e-s*stopm*R0                       # stop distance from signal price, scaled
        tp=[None if t is None else e+s*t*R0 for t in tps]  # target prices from original risk
        R=abs(ee-sl)
        tt=tuple(None if p is None else s*(p-ee)/R for p in tp)
        T.append(dict(time=dt,pts=sim(B5,ie,ee,s,sl,R,tt,mg)))
    return pd.DataFrame(T)
def st(t):
    S=stats(t);q=t.pts;S['avg_win']=round(q[q>0].mean(),1);S['avg_loss']=round(q[q<=0].mean(),1);return S
T={f'{a}/{b}R':((a,b),None) for a,b in [(1,1.5),(1,2),(1,2.5),(1,3),(1.5,2),(1.5,3),(2,3)]}
T.update({f'single {k}R':((k,k),None) for k in (1.5,2,2.5,3)})
T['1R + hold to EOD']=((1,None),None);T['1R + BE, hold EOD']=((1,None),be_after_tp1);T['1R + 1R trail']=((1,None),trailR)
M={'a current stop':(1,0),'b 1.5x stop':(1.5,0),'c 2-bar confirm':(1,1),'d 2-bar+1.5x':(1.5,1)}
rows=[]
for mk,(sm,cf) in M.items():
    for tk,(tps,mg) in T.items():
        t=run(sm,cf,tps,mg);S,I,O=st(t),stats(t[t.time<OOS]),stats(t[t.time>=OOS])
        rows.append(dict(mode=mk,targets=tk,**S,IS_win=I['win'],IS_net=I['net'],OOS_win=O['win'],OOS_net=O['net']))
R=pd.DataFrame(rows);b=R.iloc[0]
R['beats_both']=(R.IS_net>b.IS_net)&(R.OOS_net>b.OOS_net)
R.to_csv('targets5m.csv',index=False);pd.set_option('display.width',300);print(R.to_string(index=False))
