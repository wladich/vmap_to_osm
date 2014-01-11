UPDATE map_podm SET geom=ST_SimplifyPreserveTopology(geom, 1e-6) WHERE GeometryType(geom) = 'LINESTRING';
UPDATE proh0_lines SET geom=ST_SimplifyPreserveTopology(geom, 1e-6);
UPDATE proh2_lines SET geom=ST_SimplifyPreserveTopology(geom, 1e-6);
UPDATE proh3_lines SET geom=ST_SimplifyPreserveTopology(geom, 1e-6);
UPDATE proh4_lines SET geom=ST_SimplifyPreserveTopology(geom, 1e-6);
UPDATE proh5_lines SET geom=ST_SimplifyPreserveTopology(geom, 1e-6);