"""Deterministic WGS84/ENU and 60-second scene state. No bpy dependency."""
import math
from math import sin,cos,sqrt,radians
A=6378137.0
E2=(1/298.257223563)*(2-1/298.257223563)
def geodetic_to_ecef(lon,lat,h=0):
    l,p=radians(lon),radians(lat); n=A/sqrt(1-E2*sin(p)**2)
    return ((n+h)*cos(p)*cos(l),(n+h)*cos(p)*sin(l),(n*(1-E2)+h)*sin(p))
def basis(lon,lat):
    l,p=radians(lon),radians(lat)
    return ((-sin(l),cos(l),0),(-sin(p)*cos(l),-sin(p)*sin(l),cos(p)),(cos(p)*cos(l),cos(p)*sin(l),sin(p)))
ORIGIN=geodetic_to_ecef(118.7969,32.0603)
BASIS=basis(118.7969,32.0603)
def ecef_vector(v):
    return tuple(sum(a*b for a,b in zip(v,row)) for row in BASIS)
def to_scene(lon,lat,h=0):
    p=geodetic_to_ecef(lon,lat,h)
    return tuple(x/1000 for x in ecef_vector(tuple(p[i]-ORIGIN[i] for i in range(3))))
def smooth(u):
    u=max(0,min(1,u));return u*u*u*(u*(u*6-15)+10)
def fade(t,a,b):return smooth((t-a)/(b-a))
def lerp(a,b,s):return a if s==0 else b if s==1 else a+(b-a)*s
def interval(t,a,b,v0,v1):return lerp(v0,v1,fade(t,a,b))
def evaluate(t, center=(118.8,31.95), fit_range=260000):
    if not 0<=t<=60:raise ValueError('t must be in [0,60]')
    keys=[(0,150,20,23000000,0,-90),(6,115,25,23000000,0,-90),
          (12,118.7969,32.0603,2000000,0,-90),(18,*center,fit_range,-15,-60),
          (46,*center,fit_range,-15,-60),(56,185,20,23000000,0,-90),(60,150,20,23000000,0,-90)]
    for k0,k1 in zip(keys,keys[1:]):
        if k0[0]<=t<=k1[0]:
            s=fade(t,k0[0],k1[0]);vals=[lerp(a,b,s) for a,b in zip(k0[1:],k1[1:])]
            vals[2]=k0[3] if s==0 or k0[3]==k1[3] else k1[3] if s==1 else math.exp(lerp(math.log(k0[3]),math.log(k1[3]),s));break
    region=fade(t,12,18)*(1-fade(t,46,53))
    metrics=fade(t,22,23.2)*(1-fade(t,45,46))
    focus=None
    if 28<=t<40:focus=['320115','320106','320117'][min(2,int((t-28)/4))]
    detail=0
    if focus:detail=fade(t%4,0,0.5) if t%4<0.5 else 1
    return dict(zip(['lon','lat','range_m','heading','pitch'],vals),region=region,
        boundaries=fade(t,18,18.8)*(1-fade(t,46,49)),water=fade(t,18.5,19.3)*(1-fade(t,46,49)),
        labels=fade(t,19,19.8)*(1-fade(t,45,46)),metrics=metrics,
        orbit=(1-fade(t,5,8))+fade(t,54,57),focus=focus,detail=detail,pulse=(t%3)/3)
def summarize(rows):
    seen=set();v=[]
    for r in rows:
        if r['code'] in seen:raise ValueError('duplicate region code')
        seen.add(r['code']);n=r['value']
        if n is None:continue
        if not isinstance(n,(int,float)) or not math.isfinite(n):raise ValueError('nonfinite value')
        v.append(n)
    return {'count':len(v),'mean':sum(v)/len(v) if v else None,'max':max(v) if v else None}
