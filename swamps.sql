DROP TABLE IF EXISTS swamps;
CREATE TABLE swamps (geom geometry, label character varying(64), kind character(10));
ALTER TABLE swamps ADD COLUMN id SERIAL PRIMARY KEY;
CREATE INDEX swamps_geom_idx ON swamps USING gist (geom);



INSERT INTO swamps 
SELECT st_simplifypreservetopology(
            (st_dump(
                st_buffer(
                    st_buffer(
                        st_buffer(
                            st_collect(geom), 0.0003, 'endcap=flat'), 
                        0.00030), 
                    -0.00030)
            )).geom, 0.0005)
       AS geom, 'lines' AS kind FROM lines WHERE type='0x100024';


INSERT INTO swamps
SELECT geom, label, 'deep' as kind FROM polygons2_labels WHERE type = '0x20004c';

WITH 
    deep AS (SELECT geom FROM polygons2_labels WHERE type = '0x20004c'),
    swamp AS (SELECT geom, label FROM polygons2_labels WHERE type = '0x200051')
    INSERT INTO swamps
    SELECT (ST_Dump(coalesce(ST_Difference(swamp.geom, ST_Collect(deep.geom)), swamp.geom))).geom AS geom, swamp.label, 'swamp' AS kind
        FROM swamp LEFT JOIN deep ON swamp.geom && deep.geom GROUP BY swamp.geom, swamp.label;


DROP TABLE IF EXISTS swamps2;
CREATE TABLE swamps2 (geom geometry, label character varying(64), kind character(10));
ALTER TABLE swamps2 ADD COLUMN id SERIAL PRIMARY KEY;
CREATE INDEX swamps2_geom_idx ON swamps2 USING gist (geom);

WITH 
    lakes AS (SELECT geom FROM polygons3 WHERE type in ('0x20003b', '0x200029'))
INSERT INTO swamps2 
SELECT (ST_Dump(coalesce(ST_Difference(swamps.geom, ST_Collect(lakes.geom)), swamps.geom))).geom, swamps.label, swamps.kind 
    FROM swamps LEFT JOIN lakes ON swamps.geom && lakes.geom 
    GROUP BY swamps.geom, swamps.label, swamps.kind;

DELETE FROM swamps2 WHERE ST_Area(geom::geography) < 20*20;