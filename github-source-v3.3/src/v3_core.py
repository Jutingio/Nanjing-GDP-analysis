"""Deterministic district narrative and same-year city-share validation."""
import math, random

METRICS=('gdp','resident_population','retail_sales')
def share_pct(value,total):
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (value,total)):
        raise ValueError('Share requires finite numeric source values')
    if value<0 or total<=0 or value>total: raise ValueError('Invalid city denominator or district value')
    return value/total*100

def select_regions(codes,seed):
    pool=sorted(set(codes))
    if len(pool)<3: raise ValueError('Three distinct eligible regions required')
    return random.Random(seed).sample(pool,3)

def smooth(x):
    x=max(0,min(1,x)); return x*x*x*(x*(x*6-15)+10)
def ramp(t,a,b): return smooth((t-a)/(b-a))
def window(t,a,b,c,d): return ramp(t,a,b)*(1-ramp(t,c,d))

def stage(t,selected):
    if not 0<=t<=60 or len(selected)!=3: raise ValueError('Invalid timeline')
    focus=None;detail=0;index=None
    for i,(a,b,c,d) in enumerate([(21,22,29,30),(30,31,37,38),(38,39,45,46)]):
        alpha=window(t,a,b,c,d)
        if alpha>0: focus=selected[i]; detail=alpha;index=i;break
    return {'intro':window(t,0,1,8,10),'focus':focus,'detail':detail,'index':index,
            'orbit':1-ramp(t,6,12)+ramp(t,54,60),
            'region':ramp(t,12,18)*(1-ramp(t,46,53)),
            'phase':(t%60)/60}

def cache_state(t,selected):
    state=stage(t,selected)
    state['focusFile']=f"focus_{state['focus']}.png" if state['focus'] is not None else None
    return state

def validate_snapshot(data):
    period=data.get('period');totals=data.get('cityTotals',{})
    for metric in METRICS:
        total=totals.get(metric,{})
        if total.get('period')!=period:raise ValueError('Missing or mixed-year city total')
        share_pct(0,total.get('value'))
    seen=set()
    for row in data['regions']:
        if row['code'] in seen:raise ValueError('Duplicate region')
        seen.add(row['code'])
        if row.get('period')!=period:raise ValueError('Mixed-year district')
        for metric in METRICS:share_pct(row['values'][metric],totals[metric]['value'])
    selection=data.get('selection',{}).get('codes',[])
    if len(selection)!=3 or len(set(selection))!=3 or not set(selection)<=seen:raise ValueError('Invalid selected regions')
    return True
