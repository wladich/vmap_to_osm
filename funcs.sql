CREATE OR REPLACE FUNCTION st_buffer(geography, double precision, text)
  RETURNS geography AS
  'SELECT geography(ST_Transform(ST_Buffer(ST_Transform(geometry($1), _ST_BestSRID($1)), $2, $3), 4326))'
  LANGUAGE sql IMMUTABLE STRICT
  COST 100;


CREATE OR REPLACE FUNCTION _clean_polygon(geom_wkt text, precision_ float) RETURNS text AS $$
    import gdal
    import ogr
    
    gdal_mem_driver = gdal.GetDriverByName('MEM')
    ogr_mem_driver = ogr.GetDriverByName('Memory')
    
    
    def create_ogr_datasource(geom_str=None):
        ogr_ds = ogr_mem_driver.CreateDataSource('')
        layer = ogr_ds.CreateLayer('')
        if geom_str is not None:
            feature = ogr.Feature(layer.GetLayerDefn())
            geometry = ogr.CreateGeometryFromWkt(geom_str)
            assert geometry
            feature.SetGeometry(geometry)
            layer.CreateFeature(feature)
        return ogr_ds
    
    def create_raster((xmin, xmax, ymin, ymax), resolution):
        width = int((xmax - xmin) / resolution) + 5
        height = int((ymax - ymin) / resolution) + 5
        x0 = xmin - 2 * resolution
        y0 = ymax + 2 * resolution
        if width * height > 1e9:
		raise ValueError('Raster size for geometry would exceed 1Gb')
        ds = gdal_mem_driver.Create('', width, height, 1, gdal.gdalconst.GDT_Byte)
        ds.SetGeoTransform((
                x0, resolution, 0,
                y0, 0, -resolution,
            ))    
        return ds
            
    def clean(geometry_str, resolution):
        in_ds = create_ogr_datasource(geometry_str)
        in_layer = in_ds.GetLayer(0)
        extent = in_layer.GetExtent()
        xmin, xmax, ymin, ymax = extent 
        raster = create_raster(extent, resolution)
        assert gdal.RasterizeLayer(raster, (1,), in_layer, burn_values=(255,)) == 0
        out_ds = create_ogr_datasource()
        out_layer = out_ds.GetLayer(0)    
        band = raster.GetRasterBand(1)
        assert gdal.Polygonize(band, band, out_layer, -1) == 0
        collection = []
        while True:
            feature = out_layer.GetNextFeature()
            if not feature:
                break
            geometry = feature.GetGeometryRef()
            geometry = geometry.SimplifyPreserveTopology(1.5 * resolution)
            if not geometry.IsEmpty():
                collection.append(geometry)
        if collection:
  	    collection = 'GEOMETRYCOLLECTION(%s)' % ','.join(geometry.ExportToWkt() for geometry in collection)
  	else:
  	    collection = 'GEOMETRYCOLLECTION EMPTY'
		
        return collection
    return clean(geom_wkt, precision_)
$$ LANGUAGE plpythonu;

CREATE OR REPLACE FUNCTION clean_polygon(geom geometry, precision_ float) RETURNS geometry AS $$
DECLARE
	srid integer;
	new_geom geometry;
BEGIN
	IF GeometryType(geom) != 'POLYGON' THEN
		RETURN geom;
	END IF;
	IF ST_IsValid(geom) THEN
		RETURN geom;
	END IF;
	srid = st_srid(geom);
	new_geom = ST_GeomFromText(_clean_polygon(ST_AsText(geom), precision_));
	RETURN st_setsrid(new_geom, srid);
END;
$$ LANGUAGE plpgsql;



CREATE OR REPLACE FUNCTION limit_divide_polygon(geom geometry) RETURNS SETOF geometry AS
$BODY$

max_points = 200

import shapely
import shapely.wkb
import shapely.prepared
import binascii

def geometry_type(geom):
    if not hasattr(geom, '_geomtype'):
        geom._geomtype = geom.type
    return geom._geomtype
    
def dump(geom):
    if geometry_type(geom).startswith('Multi'):
        geoms = list(geom)
        geoms = sum(map(dump, geoms), [])
    else:
        geoms = [geom]
    return geoms

def npoints(geom):
    if not hasattr(geom, '_npoints'):
        boundary = dump(geom.boundary)    
        geom._npoints = sum([len(ls.coords) for ls in boundary])
    return geom._npoints

def divide(geom):
    if npoints(geom) < max_points:
        return [geom]
    else:
        x1, y1, x2, y2 = geom.bounds
        w = x2 - x2
        h = y2 - y1
        if w > h:
            xc = (x1 + x2)  / 2
            blade1 = shapely.geometry.box(x1 - 0.0001, y1 - 0.0001, xc, y2 + 0.0001) 
            blade2 = shapely.geometry.box(xc, y1-0.0001, x2+0.0001, y2+0.0001) 
        else:
            yc = (y1 + y2)  / 2
            blade1 = shapely.geometry.box(x1-0.0001, y1-0.0001, x2+0.0001, yc) 
            blade2 = shapely.geometry.box(x1-0.0001, yc, x2+0.0001, y2+0.0001) 
        geom1 = geom.intersection(blade1)
        geom2 = geom.intersection(blade2)
        geoms = map(divide, dump(geom1) + dump(geom2))
        geoms = sum(geoms, [])
        return geoms
            

def get_first_neighbour(geom, geoms):
    prep_geom = shapely.prepared.prep(geom)
    for g in geoms:
#        if g is not geom and g.intersects(geom):
        if g is not geom and prep_geom.intersects(g):
            return g


def combine(geoms):
    geoms = geoms[:]
    combine_applied = True
    while combine_applied:
        combine_applied = False
        geoms.sort(key=npoints)
        for g in geoms:
            neighbour = get_first_neighbour(g, geoms)
            if neighbour is not None and npoints(g) + npoints(neighbour) < max_points:
                geoms.remove(g)
                geoms.remove(neighbour)
                geoms.append(g.union(neighbour))
                combine_applied = True
                break
    return geoms

def _limit_divide_polygon(wkb):
    wkb = binascii.unhexlify(wkb)
    geom  = shapely.wkb.loads(wkb)
    geoms = divide(geom)
    return combine(geoms)

return _limit_divide_polygon(geom)

$BODY$
LANGUAGE 'plpythonu';

