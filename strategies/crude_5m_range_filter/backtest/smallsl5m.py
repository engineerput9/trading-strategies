exec(open('_ss_head.py').read())
def mkstop(kind,v,i,ie,ee,e,s,sl0,R0):
    a=B5['atr'][ie]
    if kind=='base': return e-s*1.5*R0
    if kind=='ind': d=v*R0
    elif kind=='cap': d=min(v,1.5*R0)
    elif kind=='atr': d=v*a
    elif kind=='swing':
        ext=L[ie-v+1:ie+1].min() if s>0 else H[ie-v+1:ie+1].max(); d=s*(ee-ext)+0.0
    elif kind=='conf':
        ext=L[i+1:ie+1].min() if s>0 else H[i+1:ie+1].max(); d=s*(ee-ext)
    return ee-s*max(d,1.0)
def run(kind,v,tgt):
    T=[];done=None
    for i in range(B5['start'],n):
        if day[i]==done or B5['flip'][i]==0: continue
        s=B5['flip'][i];done=day[i]
        if i+1>=n or day[i+1]!=day[i]: continue
        f=feats(B5,i,s);dt=B5['dt'][i]
        if not okf(f,dt): continue
        e=x[i];sl0=stopof(B5,i,s);R0=abs(e-sl0)
        r=persist(i,s,e,sl0,R0)
        if r is None: continue
        ie,ee=r
        sl=mkstop(kind,v,i,ie,ee,e,s,sl0,R0);R=abs(ee-sl)
        tp=e+s*1.5*R0 if tgt=='orig' else ee+s*tgt*R
        tt=(s*(tp-ee)/R,)*2
        T.append(dict(time=dt,pts=sim(B5,ie,ee,s,sl,R,tt),stop=R))
    return pd.DataFrame(T)
def dd(t):
    c=t.pts.cumsum();return round((c.cummax().clip(lower=0)-c).max(),0)
S=[('baseline 1.5x ind','base',0)]+[(f'{m}x ind','ind',m) for m in (0.5,0.75,1.0)]+[(f'cap {c}','cap',c) for c in (30,40,50,60)]+[(f'{m}x ATR','atr',m) for m in (1.0,1.5,2.0)]+[(f'{k}-bar swing','swing',k) for k in (3,5)]+[('confirm candles','conf',0)]
rows=[]
for nm,k,v in S:
    for tg in (['orig'] if k=='base' else ['orig',1.5,2,3]):
        t=run(k,v,tg);q=t.pts;I=t[t.time<OOS];O=t[t.time>=OOS]
        rows.append(dict(stop=nm,target='orig 1.5R price' if tg=='orig' else f'{tg}R new',n=len(t),win=round(100*(q>0).mean(),1),net=round(q.sum()),avg_win=round(q[q>0].mean(),1),avg_loss=round(q[q<=0].mean(),1),med_stop=round(t.stop.median(),1),maxDD=dd(t),IS_n=len(I),IS_win=round(100*(I.pts>0).mean(),1),IS_net=round(I.pts.sum()),OOS_win=round(100*(O.pts>0).mean(),1),OOS_net=round(O.pts.sum())))
R=pd.DataFrame(rows);b=R.iloc[0]
R['beats_both']=(R.IS_net>b.IS_net)&(R.OOS_net>b.OOS_net)
R['near']=(R.net>=0.85*b.net)&(R.med_stop<=0.7*b.med_stop)&(R.IS_net>0)&(R.OOS_net>0)
R.to_csv('smallsl5m.csv',index=False);pd.set_option('display.width',300);print(R.to_string(index=False))
