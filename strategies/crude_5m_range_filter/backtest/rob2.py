from robust import *
G=[('pdl',[3,3.5,4,4.5,5]),('erth',[0.25,0.294737,0.3,0.35,0.4]),('erlb',[14,20,30]),('wait',[1,2,3]),('lks',[1.25,1.5,1.75]),('tks',[1.5,2,2.5]),('ttp',[2,2.5,3]),('ltp',[1.25,1.5,1.75]),('gap',[0.3,0.5,0.7]),('per',[80,100,120]),('mult',[2.5,3,3.5])]
rows=[]
for k,vs in G:
    for v in vs:
        D=run(**{k:v});r=st(D);D['n2']=D.pts-3-D.px*100*0.00024/100-0.4  # approx: 3pt slip + ~charges
        r2=st(D,'n2');r.update(param=k,value=v,base=(v==P0[k]),tight_share=round((D['mode']=='tight').mean(),2),net_after_costs=r2['net'],IS_ac=r2['IS'],OOS_ac=r2['OOS']);rows.append(r)
R=pd.DataFrame(rows)[['param','value','base','n','win','net','maxDD','IS','OOS','net_after_costs','IS_ac','OOS_ac','tight_share']]
R.to_csv('robustness.csv',index=False);print(R.to_string(index=False))
