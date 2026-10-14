import numpy as np,pandas as pd,pickle
exec(open('mgmt.py').read().split("rows=[]")[0].replace("print('check base'","pass#"))
X=pd.read_pickle('_lx2.pkl');be=np.array([run(t,be=30) for t in TT])
X['plan_pts_BE30']=be
for nm,m in [('PDL',~(X.vs_pdl_atr<0)),('PDL4',~(X.vs_pdl_atr<4))]:
    m=m.values
    for lab,p in [('plan',X.plan_pts.values),('BE30',be)]:
        print(nm,lab,[ (int((pm&m).sum()),round((p[pm&m]>0).mean(),3),round(p[pm&m].sum()),round((lambda q:(np.maximum.accumulate(np.r_[0,np.cumsum(q)])[1:]-np.cumsum(q)).max())(p[pm&m]))) for pm in [np.ones(len(X),bool),~X.oos.values,X.oos.values]])
X['flag_below_PDL']=X.vs_pdl_atr<0;X['flag_within4ATR_PDL']=X.vs_pdl_atr<4
X.round(3).to_csv('losers.csv',index=False)
