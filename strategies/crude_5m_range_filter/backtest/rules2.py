import numpy as np,pandas as pd
X=pd.read_pickle('_lx.pkl');b=X.plan_pts.values;L=X.loser.values;S=np.where(X.dir=='BUY',1,-1)
X['in_pd_range']=(X.vs_pdl_atr>0)&(X.vs_pdh_atr<0)
X['room_pd_atr']=np.where(S>0,-X.vs_pdh_atr,X.vs_pdl_atr)  # distance to opposing prior-day extreme in trade dir
def st(m):
    o=[int((L&~m).sum()),int((~L&~m).sum())]
    for pm in [np.ones(len(X),bool),~X.oos.values,X.oos.values]:
        q=b[pm&m];eq=np.cumsum(q);dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
        o+=[len(q),round((q>0).mean(),3),round(q.sum()),round(dd)]
    return o
R={'baseline':np.ones(len(X),bool),
'skip below prior-day low':~(X.vs_pdl_atr<0),
'skip below PDL (sells only)':~((X.vs_pdl_atr<0)&(S<0)),
'skip below PDL (buys only)':~((X.vs_pdl_atr<0)&(S>0)),
'skip within 4ATR above PDL':~(X.vs_pdl_atr<4),
'skip signal bar body>1.2ATR':~(X.body_atr>1.2),
'skip signal bar range>2ATR':~(X.bar_rng_atr>2),
'skip with 1h trend (al60>0)':~(X.al60>0),
'skip room to PD extreme<2ATR':~(X.room_pd_atr<2),
}
for th in [1.0,1.5,2.0]: R[f'skip body>{th}ATR']=~(X.body_atr>th)
R['A: skip below PDL + body>1.5ATR']=R['skip below prior-day low']&~(X.body_atr>1.5)
R['B: skip below PDL + with-1h']=R['skip below prior-day low']&~(X.al60>0)
C=['losers_cut','winners_cut']+[f'{p}_{k}' for p in ['ALL','IS','OOS'] for k in ['n','win','net','dd']]
T=pd.DataFrame([st(m.values if hasattr(m,'values') else m) for m in R.values()],index=R.keys(),columns=C)
pd.set_option('display.width',250);print(T.to_string())
print(pd.crosstab([X.dir,X.vs_pdl_atr<0],X.loser))
X.to_pickle('_lx2.pkl')
