exec(open('add5m.py').read())
import pickle
def baseline(B,stopm=1.0,tgt='R'):
    T=[];done=None
    for i in range(B['start'],B['n']):
        if B['day'][i]==done or B['flip'][i]==0: continue
        s=B['flip'][i];done=B['day'][i]
        if i+1>=B['n'] or B['day'][i+1]!=B['day'][i]: continue
        f=feats(B,i,s);dt=B['dt'][i]
        if not okf(f,dt): continue
        e=B['x'][i];sl=stopof(B,i,s);R=abs(e-sl)
        T.append(dict(i=i,time=dt,s=s,e=e,R=R,pts=sim(B,i,e,s,sl,R),**f))
    return pd.DataFrame(T)
B5=build(d5);B15=build(d15)
t5=baseline(B5);t15=baseline(B15)
oos=lambda t:t.time>=pd.Timestamp('2026-04-01',tz='Asia/Kolkata')
for t in(t5,t15): print(stats(t),stats(t[~oos(t)]),stats(t[oos(t)]))
pickle.dump((B5,B15,t5,t15),open('_add.pkl','wb'))
