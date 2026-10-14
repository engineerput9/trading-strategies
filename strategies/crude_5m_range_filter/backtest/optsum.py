import pandas as pd,numpy as np
o=pd.read_csv('options_pnl.csv',parse_dates=['entry_time'])
oos=o.entry_time>=pd.Timestamp('2026-04-01',tz='Asia/Kolkata')
def st(p):
    p=p.dropna();c=p.cumsum();dd=(c.cummax().clip(lower=0)-c).max()
    return dict(n=len(p),net=round(p.sum()),rs_lakh=round(p.sum()*100/1e5,2),win=round((p>0).mean()*100,1),aw=round(p[p>0].mean(),1),al=round(p[p<=0].mean(),1),dd=round(dd),IS=round(p[~oos].sum()),OOS=round(p[oos].sum()))
R={}
for col,lab in [('fut_pts','Futures gross'),('gross_pts','Options gross'),('net_pts_slip1','Opt net, costs+1pt/side'),('net_pts_slip2','Opt net, costs+2pt/side'),('m_lo_pts','Opt gross IV-10'),('m_hi_pts','Opt gross IV+10')]:
    R[lab]=st(o[col])
    for m in('tight','locked'): R[f'{lab} [{m}]']=st(o[o['mode']==m][col])
print(pd.DataFrame(R).T.to_string())
print('sources',o.source.value_counts().to_dict(),'cost Rs/trade',o.cost_rs.mean().round(1),'avg entry prem',o.prem_entry.mean().round(1),'avg IV',o.iv_model.mean().round(3))
ew=o.expiry_week; print('expiry week trades',ew.sum(),'net slip1',o[ew].net_pts_slip1.sum().round(),'win',(o[ew].net_pts_slip1>0).mean().round(2),'| fut pts',o[ew].fut_pts.sum().round())
print('capture ratio by mode',(o.groupby('mode').gross_pts.sum()/o.groupby('mode').fut_pts.sum()).round(2).to_dict())
print('session_end exits',o[o.exit_reason=='session_end'].groupby('mode')[['fut_pts','gross_pts']].sum().round().to_dict())
