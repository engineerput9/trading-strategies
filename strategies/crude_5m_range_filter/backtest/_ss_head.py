exec(open('add5m.py').read())
def sim(B,i,e,s,stop,R,tps=(1,1.5),mg=None):
    H,L,x,day=B['H'],B['L'],B['x'],B['day'];legs=[[stop,None if t is None else e+s*t*R,None] for t in tps];j=i+1;lastj=i
    while j<B['n'] and day[j]==day[i]:
        lastj=j
        for lg in legs:
            if lg[2] is not None: continue
            if (L[j]<=lg[0]) if s>0 else (H[j]>=lg[0]): lg[2]=lg[0]
            elif lg[1] is not None and ((H[j]>=lg[1]) if s>0 else (L[j]<=lg[1])): lg[2]=lg[1]
        if mg and legs[1][2] is None: mg(j,legs,e,s,R)
        if all(lg[2] is not None for lg in legs): break
        j+=1
    return float(np.mean([s*((lg[2] if lg[2] is not None else x[lastj])-e) for lg in legs]))
B5=build(d5);OOS=pd.Timestamp('2026-04-01',tz='Asia/Kolkata')
n=B5['n'];x,H,L,ci,day=B5['x'],B5['H'],B5['L'],B5['ci'],B5['day']
def persist(i,s,e,sl,R):
    j=i+2
    if j>=n or day[j]!=day[i] or (ci[i:j+1]!=s).any(): return None
    if ((L[i+1:j+1]<=sl).any() if s>0 else (H[i+1:j+1]>=sl).any()): return None
    return j,x[j]
def be_after_tp1(j,legs,e,s,R):
    if legs[0][2] is not None and legs[0][2]!=legs[0][0]: legs[1][0]=e
def trailR(j,legs,e,s,R):  # after TP1, trail 1R behind best close
    if legs[0][2] is not None and legs[0][2]!=legs[0][0]:
        ns=x[j]-s*R; legs[1][0]=max(legs[1][0],ns) if s>0 else min(legs[1][0],ns)
