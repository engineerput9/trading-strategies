from robust import *
D=run()
def chg(px):
    V=px*100;brk=40;txn=2*0.000021*V;sebi=2*V*1e-6;ctt=0.0001*V;stamp=0.00002*V;gst=0.18*(brk+txn+sebi)
    return brk+txn+sebi+ctt+stamp+gst
D['chg_rs']=D.px.map(chg);D['chg_pts']=D.chg_rs/100
print('charges Rs/RT mean %.0f min %.0f max %.0f'%(D.chg_rs.mean(),D.chg_rs.min(),D.chg_rs.max()))
rows=[]
cases=[('gross',0,0,False),('charges only',0,0,True)]+[(f'charges+{s}pt slip',s,0,True) for s in (2,3,5)]+[('charges+5pt slip+5pt extra on stops',5,5,True)]
for name,sl,ex,c in cases:
    D['net']=D.pts-sl-(ex*(D.why=='stop'))-(D.chg_pts if c else 0)
    for m in ('all','tight','locked'):
        q=D if m=='all' else D[D['mode']==m]
        r=st(q.reset_index(drop=True),'net');r.update(case=name,mode=m,net_rs=round(r['net']*100));rows.append(r)
R=pd.DataFrame(rows)[['case','mode','n','win','net','net_rs','avg_win','avg_loss','maxDD','IS','OOS']]
R.to_csv('costs.csv',index=False);print(R.to_string(index=False))
c=D.chg_pts
for m in ('all','tight','locked'):
    q=D if m=='all' else D[D['mode']==m]
    be=(q.pts-q.chg_pts).sum()/len(q);isq=q[q.time<OOS];oq=q[q.time>=OOS]
    print(m,'BE slip/trade %.1f  IS BE %.1f OOS BE %.1f'%(be,(isq.pts-isq.chg_pts).mean(),(oq.pts-oq.chg_pts).mean()))
print('stop exits',(D.why=='stop').sum())
