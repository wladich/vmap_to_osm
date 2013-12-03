DO $$
DECLARE
type varchar;
proh_tbl varchar;
proh_type varchar;
lines_tbl varchar;
road_types varchar[] = ARRAY['0x100004', '0x100006', '0x100007', '0x10000a', '0x100016', '0x10002b', '0x10002c', '0x10002d', '0x10002a'];
road record;
p record;
road_dense geometry;

BEGIN
  FOR proh in 2..5 LOOP
	proh_tbl = 'proh' || proh;
	proh_type = '0x10003' || proh;
	lines_tbl = 'proh' || proh || '_lines';

	EXECUTE format($x$
		DROP TABLE IF EXISTS %1$s;
		SELECT (ST_Dump(ST_Buffer(ST_Collect(geom)::geography, 30, 'endcap=flat join=round')::geometry)).geom
		AS geom INTO %1$s FROM lines WHERE type=%2$L;
		ALTER TABLE %1$s ADD COLUMN id SERIAL PRIMARY KEY;
		CREATE INDEX %1$s_geom_idx ON %1$s USING gist (geom);$x$, proh_tbl, proh_type);
  END LOOP;
  DROP TABLE IF EXISTS proh_all; CREATE TABLE proh_all (geom geometry);
  CREATE INDEX proh_all_geom_idx ON proh_all USING gist (geom);
  INSERT INTO proh_all (SELECT geom FROM proh2 UNION SELECT geom FROM proh3 UNION SELECT geom FROM proh4 UNION SELECT geom FROM proh5);

  DROP TABLE IF EXISTS lines_dense;
  CREATE TABLE lines_dense (LIKE map_podm);
  FOR road IN SELECT * FROM lines WHERE lines.type=ANY(road_types) LOOP
    road_dense = road.geom;
    for p in SELECT (st_dump(st_boundary(proh_all.geom))).geom as geom FROM proh_all WHERE proh_all.geom && road.geom LOOP
	road_dense = st_linemerge(st_split(road_dense, p.geom));
    END LOOP;
    INSERT INTO lines_dense (id, type, geom, label) values (road.id, road.type, road_dense, road.label);
  END LOOP;

  FOR proh in 2..5 LOOP
	proh_tbl = 'proh' || proh;
	lines_tbl = 'proh' || proh || '_lines';

	EXECUTE format($x$
		DROP TABLE IF EXISTS %2$s; 
		CREATE TABLE %2$s(
		    orig_id int4 NOT NULL,
		    geom geometry,
		    type character varying(12),
		    label character varying(64),
		    dir integer,
		    angle integer);
		INSERT INTO %2$s (orig_id, type, label, geom) 
		  SELECT * FROM (
		    SELECT lines.id, lines.type, lines.label, (ST_Dump(ST_Intersection(lines.geom, %1$s.geom))).geom AS geom
		    FROM lines_dense as lines INNER JOIN %1$s ON lines.geom && %1$s.geom) as cropped
		  WHERE ST_Length(cropped.geom::geography)>170;
		ALTER TABLE %2$s ADD COLUMN id SERIAL PRIMARY KEY;
		CREATE INDEX %2$s_geom_idx ON %2$s USING gist (geom);		
		$x$, proh_tbl, lines_tbl);
  END LOOP;
END;$$;

DROP TABLE IF EXISTS proh45_lines;
SELECT * INTO proh45_lines FROM proh5_lines UNION ALL SELECT * FROM proh4_lines;
CREATE INDEX proh45_lines_geom_idx ON proh45_lines USING gist (geom);
DROP TABLE IF EXISTS proh345_lines;
SELECT * INTO proh345_lines FROM proh3_lines UNION ALL SELECT * FROM proh45_lines;
CREATE INDEX proh345_lines_geom_idx ON proh345_lines USING gist (geom);
DROP TABLE IF EXISTS proh2345_lines;
SELECT * INTO proh2345_lines FROM proh2_lines UNION ALL SELECT * FROM proh345_lines;
CREATE INDEX proh2345_lines_geom_idx ON proh2345_lines USING gist (geom);

DROP TABLE IF EXISTS proh4_lines_cropped;
SELECT t1.orig_id, t1.label, t1.type, (st_dump(coalesce(st_difference(st_collect(t1.geom), st_collect(t2.geom)), st_collect(t1.geom)))).geom as geom 
INTO  proh4_lines_cropped
FROM proh4_lines as t1 left join proh5_lines as t2 using (orig_id) group by t1.orig_id, t1.label, t1.type;

DROP TABLE IF EXISTS proh3_lines_cropped;
SELECT t1.orig_id, t1.label, t1.type, (st_dump(coalesce(st_difference(st_collect(t1.geom), st_collect(t2.geom)), st_collect(t1.geom)))).geom as geom 
INTO  proh3_lines_cropped
FROM proh3_lines as t1 left join proh45_lines as t2 using (orig_id) group by t1.orig_id, t1.label, t1.type;

DROP TABLE IF EXISTS proh2_lines_cropped;
SELECT t1.orig_id, t1.label, t1.type, (st_dump(coalesce(st_difference(st_collect(t1.geom), st_collect(t2.geom)), st_collect(t1.geom)))).geom as geom 
INTO  proh2_lines_cropped
FROM proh2_lines as t1 left join proh345_lines as t2 using (orig_id) group by t1.orig_id, t1.label, t1.type;

DROP TABLE IF EXISTS proh0_lines;
SELECT t1.id, t1.label, t1.type, (st_dump(coalesce(st_difference(st_collect(t1.geom), st_collect(t2.geom)), st_collect(t1.geom)))).geom as geom 
INTO  proh0_lines
FROM lines_dense as t1 left join proh2345_lines as t2 on t1.id = t2.orig_id group by t1.id, t1.label, t1.type;


DROP TABLE proh4_lines;
DROP TABLE proh3_lines;
DROP TABLE proh2_lines;
ALTER TABLE proh4_lines_cropped RENAME TO proh4_lines;
ALTER TABLE proh3_lines_cropped RENAME TO proh3_lines;
ALTER TABLE proh2_lines_cropped RENAME TO proh2_lines;

DROP TABLE proh2345_lines;
DROP TABLE proh345_lines;
DROP TABLE proh45_lines;
DROP TABLE proh2;
DROP TABLE proh3;
DROP TABLE proh4;
DROP TABLE proh5;
  
