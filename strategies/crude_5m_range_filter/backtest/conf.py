import numpy as np,pandas as pd
s=open('tf.py').read().split('rows=[]')[0].replace("T=g['T'];","T=g['T'];G.append(g);")
G=[];exec(s)
g15=G[1];b15=bars15()
# 15m RF state known at 5m entry: last 15m bar whose close (start+15m) <= 5m signal bar close (time+5m)
st15=pd.DataFrame(dict(close=b15.dt+pd.Timedelta('15min'),ci=g15['ci'],rfdir=np.sign(np.r_[0,np.diff(g15['rf'])])))
def upd(f): return (f.dow!='Fri')&~(f.gap_filled&(f.gap_atr.abs()>0.5))&(f.pdl_atr>=4)
for f in (f5,f15):
    f['sd']=np.where(f.dir=='BUY',1,-1);f['day']=f.time.dt.date;f['upd']=upd(f)
f5['close']=f5.time+pd.Timedelta('5min');f15['close']=f15.time+pd.Timedelta('15min')
def stats(b):
    q=b.pts.values;eq=np.cumsum(q);dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max() if len(q) else 0
    return dict(n=len(b),win=round((b.ro>0).mean()*100,1) if len(b) else np.nan,net=round(q.sum()),avgR=round(b.ro.mean(),3) if len(b) else np.nan,dd=round(dd))
rows=[];out=[]
def tag(a,b,ver):
    m=a.merge(b[['day','sd','close']],on='day',how='left',suffixes=('','_o'))
    m['rel']=np.where(m.sd_o.isna(),'none',np.where(m.sd==m.sd_o,'same','opp'))
    m['first']=np.where(m.sd_o.isna(),'',np.where(m.close_o<=m.close,'other<=this','this first'))
    m['gap_min']=(m.close-m.close_o).dt.total_seconds()/60
    return m
for ver in ['original','updated']:
  for tf,a,b in [('5m',f5,f15),('15m',f15,f5)]:
    A=a if ver=='original' else a[a.upd]
    B=b if ver=='original' else b[b.upd]
    m=tag(A,B,ver)
    if tf=='5m':
        both=m[m.rel!='none']
        out.append(f"[{ver}] 5m days {len(A)}, 15m days {len(B)}, both {len(both)}: same {(both.rel=='same').sum()}, opp {(both.rel=='opp').sum()}; 15m closed first/at-or-before 5m: {(both.close_o<=both.close).sum()}, 5m first: {(both.close_o>both.close).sum()}; median |gap| {both.gap_min.abs().median():.0f} min, median (5m close-15m close) {both.gap_min.median():.0f} min")
        m.assign(version=ver).to_csv(f'_conf_{ver}.csv',index=False)
    grp={'same':m.rel=='same','same, other fired at/before':(m.rel=='same')&(m.close_o<=m.close),'opp':m.rel=='opp','opp, other at/before':(m.rel=='opp')&(m.close_o<=m.close),'none':m.rel=='none','all':m.rel!='x'}
    for gn,gm in grp.items():
      for per,pm in [('ALL',True),('IS',~m.oos),('OOS',m.oos)]:
        rows.append(dict(kind='match',version=ver,tf=tf,group=gn,period=per,**stats(m[gm&pm])))
# entry filter: 15m RF state at 5m entry
k=pd.merge_asof(f5.sort_values('close'),st15.rename(columns={'close':'c15'}),left_on='close',right_on='c15',direction='backward')
f5f=k.sort_values('time')
for ver in ['original','updated']:
  A=f5f if ver=='original' else f5f[f5f.upd]
  for fn,fm in [('no filter',A.sd==A.sd),('15m RF signal state (ci) agrees',A.ci==A.sd),('15m RF slope agrees',A.rfdir==A.sd),('15m ci disagrees',A.ci==-A.sd)]:
    for per,pm in [('ALL',True),('IS',~A.oos),('OOS',A.oos)]:
      rows.append(dict(kind='filter',version=ver,tf='5m',group=fn,period=per,**stats(A[fm&pm])))
R=pd.DataFrame(rows);R.to_csv('confluence.csv',index=False)
pd.set_option('display.width',250);pd.set_option('display.max_rows',500)
print('\n'.join(out));print(R.to_string(index=False))
