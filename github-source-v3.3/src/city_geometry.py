"""City-independent WGS84 coordinates, constrained meshes and the existing 60s camera rhythm."""
import math
import core


class LocalFrame:
    def __init__(self,lon,lat):
        self.origin=core.geodetic_to_ecef(lon,lat)
        self.rows=core.basis(lon,lat)

    def rotate(self,vector):
        return tuple(sum(a*b for a,b in zip(vector,row)) for row in self.rows)

    def to_scene(self,lon,lat,height=0):
        p=core.geodetic_to_ecef(lon,lat,height)
        return tuple(v/1000 for v in self.rotate(tuple(p[i]-self.origin[i] for i in range(3))))


def camera_state(t,center,fit):
    if not 0<=t<=60:raise ValueError('Camera time must be within 0..60')
    lon,lat=center
    keys=[(0,lon+31.2,20,23000000,0,-90),(6,lon-3.8,25,23000000,0,-90),
          (12,lon,lat,2000000,0,-90),(18,lon,lat,fit,-15,-60),
          (46,lon,lat,fit,-15,-60),(56,lon+66.2,20,23000000,0,-90),(60,lon+31.2,20,23000000,0,-90)]
    for a,b in zip(keys,keys[1:]):
        if a[0]<=t<=b[0]:
            u=core.fade(t,a[0],b[0]);v=[core.lerp(x,y,u) for x,y in zip(a[1:],b[1:])]
            v[2]=a[3] if u==0 else b[3] if u==1 else math.exp(core.lerp(math.log(a[3]),math.log(b[3]),u))
            return dict(zip(['lon','lat','range_m','heading','pitch'],v))


def prepare_geometry(collection,origin,year):
    # Heavy optional libraries are imported only by external Python preprocessing.
    from shapely.geometry import shape,mapping
    from shapely.ops import transform,unary_union
    from shapely import constrained_delaunay_triangles,force_2d,segmentize
    from pyproj import Transformer,CRS
    crs=collection.get('crs',{}).get('properties',{}).get('name','EPSG:4326')
    if crs not in ('EPSG:4326','urn:ogc:def:crs:OGC:1.3:CRS84','urn:ogc:def:crs:EPSG::4326'):
        raise ValueError('Supply WGS84 longitude/latitude GeoJSON (EPSG:4326), not projected or GCJ-02 coordinates')
    if collection.get('type')!='FeatureCollection' or not collection.get('features'):
        raise ValueError('District input must be a non-empty FeatureCollection')
    lon,lat=origin
    if not -180<=lon<=180 or not -75<=lat<=75:
        raise ValueError('Generic city adapter supports origins within 75 degrees of equator')
    projection=CRS.from_proj4(f'+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m')
    forward=Transformer.from_crs(4326,projection,always_xy=True).transform
    inverse=Transformer.from_crs(projection,4326,always_xy=True).transform
    local=LocalFrame(lon,lat);seen=set();districts=[];geometries=[];projected=[]
    for feature in collection['features']:
        props=feature['properties'];code=str(props['regionCode']);name=props['name']
        if not code or code in seen:raise ValueError('Duplicate or empty district code')
        if not isinstance(name,str) or not name:raise ValueError('District name is required')
        seen.add(code);g=force_2d(shape(feature['geometry']))
        if g.geom_type not in ('Polygon','MultiPolygon') or g.is_empty or not g.is_valid:
            raise ValueError('District geometry must be a valid Polygon or MultiPolygon: '+code)
        west,south,east,north=g.bounds
        if not -180<=west<=east<=180 or not -75<=south<=north<=75 or east-west>8 or north-south>8:
            raise ValueError('City adapter requires compact WGS84 polygons, without antimeridian crossing')
        if max(abs(west-lon),abs(east-lon),abs(south-lat),abs(north-lat))>8:
            raise ValueError('Geometry is too far from configured origin; verify CRS and city')
        if any(not g.intersection(other).is_empty and transform(forward,g.intersection(other)).area>.1 for other in geometries):
            raise ValueError('Administrative district geometries overlap; separate statistical scopes before mapping')
        # Densify longitude/latitude borders before projection. Z is deliberately ignored.
        metric=transform(forward,segmentize(g,.02))
        projected.append(metric);geometries.append(g)
        triangles=constrained_delaunay_triangles(metric)
        mismatch=unary_union(triangles.geoms).symmetric_difference(metric).area
        if mismatch>.1:raise ValueError('Triangulation coverage error: '+code)
        vertices=[];faces=[];lookup={}
        pending=[list(triangle.exterior.coords)[:3] for triangle in triangles.geoms]
        refined=[]
        while pending:
            tri=pending.pop()
            lengths=[math.dist(tri[i],tri[(i+1)%3]) for i in range(3)]
            edge=max(range(3),key=lambda i:lengths[i])
            if lengths[edge]>5000:
                a,b,c=tri[edge],tri[(edge+1)%3],tri[(edge+2)%3]
                middle=((a[0]+b[0])/2,(a[1]+b[1])/2)
                pending.extend([[a,middle,c],[middle,b,c]])
            else:refined.append(tri)
        for triangle in refined:
            face=[]
            for x,y in triangle:
                key=(x,y)
                if key not in lookup:
                    lookup[key]=len(vertices);lo,la=inverse(x,y);vertices.append(local.to_scene(lo,la,20))
                face.append(lookup[key])
            # Blender front face must face local +Z, regardless of triangulator winding.
            a,b,c=[vertices[i] for i in face]
            if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:face.reverse()
            faces.append(face)
        border=segmentize(g,.02)
        polygons=list(border.geoms) if border.geom_type=='MultiPolygon' else [border]
        lines=[[local.to_scene(*p[:2],30) for p in ring.coords] for poly in polygons for ring in [poly.exterior,*poly.interiors]]
        anchor=g.representative_point()
        districts.append({'code':code,'name':name,'vertices':vertices,'faces':faces,'lines':lines,
                          'anchor':local.to_scene(anchor.x,anchor.y,30),'anchorLonLat':[anchor.x,anchor.y],
                          'triangulationErrorM2':mismatch})
    city=unary_union(geometries);center=city.centroid
    polygons=list(city.geoms) if city.geom_type=='MultiPolygon' else [city]
    result={'districts':districts,'center':[center.x,center.y],'bounds':list(city.bounds),
            'city_lines':[[local.to_scene(*p[:2],35) for p in poly.exterior.coords] for poly in polygons],
            'river_lines':[],'project':{'originLonLat':origin,'sceneUnit':'km','boundaryYear':year}}
    return result,mapping(city)
