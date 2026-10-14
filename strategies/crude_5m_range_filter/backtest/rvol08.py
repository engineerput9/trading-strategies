exec(open('_rv_base.py').read())
dt=pd.read_csv('dynamic_trades.csv');assert len(dt)==len(D)
D['entry_time']=dt.entry_time.values;D['exit_reason']=dt.exit_reason.values;D['pts']=dt.pts.values
op=pd.read_csv('options_pnl.csv');D['opt']=op.net_pts_slip1.values
D['IS']=IS;D['month']=pd.to_datetime(D.time.astype(str).str[:7]).dt.strftime('%Y-%m')
def st(sub,col='pts',cost=4.7):
    q=sub[col].reset_index(drop=True);c=q.cumsum();pk=c.cummax().clip(lower=0);dd=pk-c;j=dd.idxmax()
    i0=(c[:j+1]).idxmax() if c[:j+1].max()>0 else 0
    ls=cc=0
    for p in q: cc=cc+1 if p<=0 else 0;ls=max(ls,cc)
    t=sub.time.reset_index(drop=True).astype(str).str[:10]
    m=sub['mode'].values
    return dict(n=len(q),win=round(100*(q>0).mean(),1),gross=round(q.sum()),after_cost=round((q-cost).sum()),avg_win=round(q[q>0].mean(),1),avg_loss=round(q[q<=0].mean(),1),DD=round(dd.max()),DD_from=t[i0],DD_to=t[j],streak=ls,IS=round(q[sub.IS.values].sum()),OOS=round(q[~sub.IS.values].sum()),
      IS_cost=round((q[sub.IS.values]-cost).sum()),OOS_cost=round((q[~sub.IS.values]-cost).sum()),tight=f"{(m=='tight').sum()} / {round(q[m=='tight'].sum())}",locked=f"{(m=='locked').sum()} / {round(q[m=='locked'].sum())}")
out=[]
for th in [None,0.7,0.8,0.9]:
    keep=np.ones(len(D),bool) if th is None else ~((D['mode']=='locked')&(D.rv_tod10<th)).values
    s=D[keep];r=st(s);r['rule']='baseline' if th is None else f'skip locked rv<{th}'
    o=st(s,'opt',0);r.update({'opt_net':o['gross'],'opt_DD':o['DD'],'opt_IS':o['IS'],'opt_OOS':o['OOS'],'opt_win':o['win']})
    out.append(r)
R=pd.DataFrame(out);pd.set_option('display.width',400);print(R.to_string(index=False))
sk=(D['mode']=='locked')&(D.rv_tod10<0.8)
D['skipped_rv08']=sk
D[['time','entry_time','mode','rv_tod10','exit_reason','pts','opt','IS','skipped_rv08']].to_csv('rvol08_trades.csv',index=False)
S=D[sk];print('skipped',len(S),'wins',(S.pts>0).sum(),'losses',(S.pts<=0).sum(),'pts',round(S.pts.sum(),1),'IS',round(S.pts[S.IS].sum()),'OOS',round(S.pts[~S.IS].sum()),'opt',round(S.opt.sum()))
print(S[['time','rv_tod10','exit_reason','pts']].assign(time=S.time.astype(str).str[:16]).to_string(index=False))
M=pd.DataFrame({'baseline':D.groupby('month').pts.sum(),'rvol08':D[~sk].groupby('month').pts.sum(),'skipped_n':D[sk].groupby('month').size()}).fillna(0).round(0)
M['diff']=M.rvol08-M.baseline;M.to_csv('rvol08_monthly.csv');print(M.to_string());print('neg months',(M.baseline<0).sum(),(M.rvol08<0).sum())
