import sys,time,json,pandas as pd
sys.path.insert(0,__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'..','..','..','common','fyers'))
from fyers_login import get_fyers
f=get_fyers()
t=pd.read_csv('dynamic_trades.csv',parse_dates=['entry_time','exit_time'])
out={}
def h(sym,d0,d1):
    r=f.history({"symbol":sym,"resolution":"5","date_format":"1","range_from":d0,"range_to":d1,"cont_flag":"1"}); time.sleep(0.5)
    return r.get('candles') or [], r.get('s'), str(r.get('message',''))[:60]
syms=set()
for i,r in t[t.entry_time>='2026-09-17'].iterrows():
    k=int(round(r.entry_price/50)*50)
    for kk in (k-50,k,k+50):
        for cp in ('CE','PE'): syms.add(f"MCX:CRUDEOIL26OCT{kk}{cp}")
for k in range(8000,10601,100):
    for cp in ('CE','PE'): syms.add(f"MCX:CRUDEOIL26OCT{k}{cp}")
syms.add("MCX:CRUDEOIL26OCTFUT")
for s in sorted(syms):
    c,st,m=h(s,"2026-08-15","2026-10-12"); out[s]=c; print(s,st,len(c),m,flush=True)
json.dump(out,open('optraw.json','w'))
