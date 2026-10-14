exec(open('tf.py').read().split("rows=[]")[0])
d=bars15();H,L,C=d.h.values,d.l.values,d.c.values;day=d.dt.dt.date.values;n=len(d)
H5,L5=d5.h.values,d5.l.values;idx5=pd.Series(range(len(d5)),index=d5.dt)
base=(f15.dow!='Fri')&~(f15.gap_filled&(f15.gap_atr.abs()>0.5))&(f15.pdl_atr>=4)
F=f15[base].copy();assert len(F)==93
def sim(i,s,e,R,t1,t2):
    j=i+1;out=[None,None];last=e
    while j<n and day[j]==day[i]:
        adv=s*(e-(L[j] if s>0 else H[j]));fav=s*((H[j] if s>0 else L[j])-e);last=C[j]
        if adv>=R:
            for k in range(2):
                if out[k] is None: out[k]=-R
            break
        for k,t in enumerate((t1,t2)):
            if out[k] is None and fav>=t: out[k]=t
        if None not in out: break
        j+=1
    out=[o if o is not None else s*(last-e) for o in out]
    return sum(out)/2
def stopdist(t,m):
    i,s,e,a=t.i,t.s,t.entry,t.atr;R0=t.risk_pts
    sw=lambda b:(e-L[i-b:i].min()) if s>0 else (H[i-b:i].max()-e)
    if m=='orig':return R0
    if m[0]=='f':return R0*m[1]
    if m[0]=='atr':return a*m[1]
    if m[0]=='sw':return max(sw(m[1]),1.0)
    if m[0]=='cap':return min(R0,m[1])
    if m[0]=='5m':
        k=idx5[t.time+pd.Timedelta('10min')];a5=g5['atr'][k]
        r=(e-L5[k-10:k].min()) if s>0 else (H5[k-10:k].max()-e);return max(r,a5)
M=[('orig','orig')]+[(f'{x}x indicator stop',('f',x)) for x in (.5,.6,.75)]+[(f'{x}x 15m ATR',('atr',x)) for x in (1,1.5,2)]+[(f'swing {b} bars',('sw',b)) for b in (3,5)]+[(f'cap {c} pts',('cap',c)) for c in (50,60,75)]+[('5m swing10/ATR14 wider',('5m',))]
rows=[];rec=[]
for nm,m in M:
  for tg in ['R-multiple','orig pts']:
    if nm=='orig' and tg=='orig pts':continue
    P=[];Rs=[];RR=[]
    for t in F.itertuples():
        R=stopdist(t,m);R0=t.risk_pts
        t1,t2=(R,1.5*R) if tg=='R-multiple' else (R0,1.5*R0)
        p=sim(t.i,t.s,t.entry,R,t1,t2);P.append(p);Rs.append(R);RR.append(p/R)
    G=pd.DataFrame(dict(p=P,R=Rs,r=RR,oos=F.oos.values))
    for per,pm in [('ALL',G.oos|~G.oos),('IS',~G.oos),('OOS',G.oos)]:
        b=G[pm];eq=b.p.cumsum().values;dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
        rows.append(dict(stop=nm,targets=tg,period=per,n=len(b),win=round((b.p>0).mean()*100,1),net=round(b.p.sum()),expR=round(b.r.mean(),3),dd=round(dd),med_stop=round(b.R.median(),1)))
R=pd.DataFrame(rows);R.to_csv('stops15.csv',index=False)
W=R.pivot_table(index=['stop','targets'],columns='period',values=['n','win','net','expR','dd','med_stop'],sort=False)
pd.set_option('display.width',300);print(W[[('win','ALL'),('net','ALL'),('expR','ALL'),('dd','ALL'),('med_stop','ALL'),('net','IS'),('net','OOS'),('win','IS'),('win','OOS'),('dd','IS'),('dd','OOS')]].to_string())
