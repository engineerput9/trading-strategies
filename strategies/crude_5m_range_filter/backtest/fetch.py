import sys,time,json,datetime as dt
sys.path.insert(0,__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'..','..','..','common','fyers')); from fyers_login import get_fyers
f=get_fyers(); out={}
def pull(sym,cont):
    rows=[]; end=dt.date(2026,10,12)
    for i in range(5):
        st=end-dt.timedelta(days=99)
        r=f.history({"symbol":sym,"resolution":"5","date_format":"1","range_from":st.isoformat(),"range_to":end.isoformat(),"cont_flag":"1" if cont else "0"})
        c=r.get('candles') or []; print(sym,cont,st,end,r.get('s'),len(c),str(r.get('message',''))[:80]); rows+=c; end=st-dt.timedelta(days=1); time.sleep(0.6)
        if not c and i>0: break
    return rows
out['cont']=pull("MCX:CRUDEOIL26OCTFUT",True)
for s in ["MCX:CRUDEOIL26SEPFUT","MCX:CRUDEOIL26OCTFUT"]: out[s]=pull(s,False)
json.dump(out,open('raw.json','w'))
