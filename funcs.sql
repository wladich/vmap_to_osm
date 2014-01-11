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



CREATE OR REPLACE FUNCTION divide_polygon(geom geometry) RETURNS SETOF geometry AS
$BODY$
DECLARE
	width float;
	height float;
	x0 float;
	y0 float;
	x1 float;
	y1 float;

	q float;
	blade geometry;
	center float;
	part record;
	subpart record;
	
	
BEGIN
	IF ST_NPoints(geom) < 200 THEN
		RETURN NEXT geom;
	ELSE
		x0 = ST_XMin(geom);
		y0 = ST_YMin(geom);
		x1 = ST_XMax(geom);
		y1 = ST_YMax(geom);

		q = cos(y0 / 180 * pi());
		width = x1 - x0;
		height = y1 - y0;
		IF width * q > height THEN
			center = x0 + width / 2;	
			blade = ST_MakeLine(ST_MakePoint(center, y0-0.0001),ST_MakePoint(center, y1+0.0001));
		ELSE
			center = y0 + height / 2;	
			blade = ST_MakeLine(ST_MakePoint(x0-0.0001, center), ST_MakePoint(x1+0.0001, center));
		END IF;
		blade = ST_SetSrid(blade, ST_Srid(geom));
		FOR part in SELECT ST_Dump(ST_Split(geom, blade)) as dump LOOP
			FOR subpart in SELECT divide_polygon((part.dump).geom) as geom LOOP
				RETURN NEXT subpart.geom;
			END LOOP;
		END LOOP;
	END IF;
	
END
$BODY$
LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION limit_divide_polygon(geom geometry) RETURNS SETOF geometry AS
$BODY$
	class Geom(str):
		_npoints = None
		@property
		def npoints(self):
			if self._npoints is None:
				self._npoints = plpy.execute("SELECT ST_NPoints('%s')" % self)[0].values()[0]
			return self._npoints
	
	def intersects(geom1, geom2):
		return plpy.execute("SELECT ST_Intersects('{0}', '{1}') AND ST_NPoints(ST_Intersection('{0}', '{1}'))>1".format(geom1, geom2))[0].values()[0]
	
	def get_first_neighbour(geom_, geoms):
		result = []
		for g in geoms:
			if g != geom_ and intersects(geom_, g):
				return g
	def join_geoms(geom1, geom2):
		return plpy.execute("SELECT ST_Buffer(ST_Collect('%s', '%s'), 0)" % (geom1, geom2))[0].values()[0]

	def combine(geoms):
		geoms = geoms[:]
		combine_applied = True
		while combine_applied:
			combine_applied = False
			geoms.sort(key=lambda x: x.npoints)
			for g in geoms:
				neighbour = get_first_neighbour(g, geoms)
				if neighbour is not None and g.npoints + neighbour.npoints < 200:
					geoms.remove(g)
					geoms.remove(neighbour)
					geoms.append(Geom(join_geoms(g, neighbour)))
					combine_applied = True
					break
		return geoms
			
	
	divided = [Geom(g.values()[0]) for g in plpy.execute("SELECT divide_polygon('%s')" % geom)]
	return combine(divided)
$BODY$
LANGUAGE 'plpythonu';

