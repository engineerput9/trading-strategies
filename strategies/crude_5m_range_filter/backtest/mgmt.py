import numpy as np,pandas as pd,pickle
src=open('bt.py').read().split("T=[];done=None")[0];exec(src)
X=pd.read_pickle('_lx.pkl');TT=pickle.load(open('_tt.pkl','rb'))
def run(t,be=None,ex=None,stopx=1.0):
    i,j,s,e,R=t['i'],t['j'],t['s'],t['entry'],t['risk_pts'];tot=0
    for tp in (1,1.5):
        sl=e-s*R*stopx;armed=False;res=None;mf=0
        for k,q in enumerate(range(i+1,j)):
            hi,lo=(H[q],L[q]) if s>0 else (-L[q],-H[q]);E=s*e;SL=s*sl
            if lo<=SL: res=SL-E;break
            if hi>=E+tp*R: res=tp*R;break
            mf=max(mf,hi-E)
            if ex and k+1==ex[1] and mf<ex[0]: res=s*(x[q]-e);break
            if be and not armed and mf>=be: sl=e+s*(be*0 if be>0 else 0);armed=True
        if res is None: res=s*(x[j-1]-e)
        tot+=res/2
    return tot
def stat(p):
    o=[]
    for m in [np.ones(len(X),bool),~X.oos.values,X.oos.values]:
        q=p[m];eq=np.cumsum(q);dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
        o+= [round((q>0).mean(),3),round(q.sum()),round(dd)]
    return o
rows=[]
b=np.array([run(t) for t in TT]);print('check base',stat(b),X.plan_pts.sum())
def add(name,p):
    L=b<0;rows.append([name,int(((p>=0)&L).sum()),int(((p<b)&~L).sum())]+stat(p))
add('baseline',b)
for be in [20,30,40,50,60,80]: add(f'BE after +{be}',np.array([run(t,be=be) for t in TT]))
for n in [1,2,3,4,6]:
  for xx in [5,10,15,20,30]: add(f'exit if MFE<{xx} after {n} bars',np.array([run(t,ex=(xx,n)) for t in TT]))
for n,xx,be in [(3,10,40),(3,10,50),(2,10,50),(4,15,50)]: add(f'exit MFE<{xx}@{n} + BE+{be}',np.array([run(t,ex=(xx,n),be=be) for t in TT]))
C=['rule','losers_cut','winners_hurt','ALL_win','ALL_net','ALL_dd','IS_win','IS_net','IS_dd','OOS_win','OOS_net','OOS_dd']
M=pd.DataFrame(rows,columns=C);pd.set_option('display.width',250);print(M.to_string(index=False));M.to_csv('_mgmt.csv',index=False)
