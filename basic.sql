UPDATE map_podm SET label = NULL WHERE label = ' ';
CREATE VIEW points AS SELECT * FROM map_podm WHERE GeometryType(geom)='POINT';
CREATE VIEW lines AS SELECT * FROM map_podm WHERE GeometryType(geom)='LINESTRING';
CREATE VIEW polygons AS SELECT * FROM map_podm WHERE GeometryType(geom)='POLYGON';
CREATE LANGUAGE plpythonu;