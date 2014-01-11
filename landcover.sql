drop table if exists polygons2;
select (st_dump(clean_polygon(geom, 0.00005))).geom as geom, type, label into polygons2 from polygons;
ALTER TABLE polygons2 ADD COLUMN id SERIAL PRIMARY KEY;
CREATE INDEX polygons2_geom_idx ON polygons2 USING gist (geom);
CREATE INDEX polygons2_type_idx ON polygons2 (type);
CREATE INDEX polygons2_label_idx ON polygons2 (label);

-- clean, join and enlarge polygons
drop table if exists polygons2_labels;
create table polygons2_labels(geom geometry, type character varying(12), label character varying(64));
insert into polygons2_labels(
	select (st_dump(st_buffer(st_buffer(st_collect(geom), -0.00005, 'join=mitre'), 0.0001, 'join=mitre'))).geom as geom, type, label
	from polygons2 where type in ('0x200004', '0x20004e', '0x200029', '0x20003b', '0x20004c', '0x200051') GROUP BY type, label);
insert into polygons2_labels(
	select (st_dump(st_buffer(st_buffer(st_collect(geom), -0.00005, 'join=mitre'), 0.0001, 'join=mitre'))).geom as geom, type, null as label
	from polygons2 where type not in ('0x200004', '0x20004e', '0x200029', '0x20003b', '0x20004c', '0x200051') GROUP BY type);
CREATE INDEX polygons2_labels_label_idx ON polygons2_labels (label);
CREATE INDEX polygons2_labels_type_idx ON polygons2_labels (type);
CREATE INDEX polygons2_labels_geom_idx ON polygons2_labels USING gist (geom);
ALTER TABLE polygons2_labels ADD COLUMN id SERIAL PRIMARY KEY;

drop table if exists combined_polygons;
create table combined_polygons(geom geometry, type character varying(12), label character varying(64));
CREATE INDEX combined_polygons_type_idx ON combined_polygons (type);
CREATE INDEX combined_polygons_geom_idx ON combined_polygons USING gist (geom);


drop table if exists polygons3;
create table polygons3(geom geometry, type character varying(12), label character varying(64));

DO $$
obj_stack = ['0x200016', '0x200052', '0x20004f', '0x200050', '0x200014', '0x200015', '0x200004', '0x20000e', '0x200001', '0x20004e', '0x20001a', '0x200029', '0x20003b', '0x200053']
#obj_stack = ['0x200004', '0x20000e', '0x200001', '0x20004e', '0x20001a', '0x200029', '0x20003b', '0x200053']
#obj_stack = [ '0x200029', '0x20003b', '0x200053']
#obj_stack = [ '0x20003b', '0x200053']
#obj_stack = [ '0x20000e', '0x20004e', '0x200029']
prev_type = None
for type_ in obj_stack[::-1]:
	plpy.notice('Processing type %s' % type_)
	plpy.execute('drop table if exists temp_table;')
	plpy.execute('drop table if exists temp_table2;')
	plpy.execute('drop table if exists temp_table3;')
	# clean, join and enlarge polygons
	plpy.execute("select geom, label into temp_table from polygons2_labels where type='%s'" % type_)
	plpy.execute("ALTER TABLE temp_table ADD COLUMN id SERIAL PRIMARY KEY;")
	plpy.execute("CREATE INDEX temp_table_label_idx ON temp_table (label);")
	plpy.execute("CREATE INDEX temp_table_geom_idx ON temp_table USING gist (geom);")

	# save enlarged unioned polygons for future use
	if type_ != '0x200016':
		plpy.execute('drop table if exists temp_table2')
		plpy.execute('create table temp_table2 (geom geometry)')
		plpy.execute("insert into temp_table2 (SELECT geom from combined_polygons where combined_polygons.type='%s')" % (prev_type))
		plpy.execute("insert into temp_table2 (SELECT geom from temp_table)")
		plpy.execute("""insert into combined_polygons 
			(SELECT (st_dump(st_buffer(st_collect(geom), 0))).geom, '%s' as type 
			from temp_table2)""" % (type_))
		plpy.execute("CREATE INDEX temp_table2_geom_idx ON temp_table2 USING gist (geom);")
	# subtract overlaying polygons from previous iteration
	plpy.execute("""insert into polygons3 (
			select (st_dump(coalesce(st_difference(t1.geom, st_collect(t2.geom)), t1.geom))).geom as geom, '%s' as type, label
			from temp_table as t1 left outer join (select geom from combined_polygons where type='%s') as t2
			on t1.geom && t2.geom group by t1.id)""" % (type_, prev_type))
	prev_type = type_
$$ LANGUAGE plpythonu;

drop table temp_table;
drop table combined_polygons;
--drop table polygons2_labels;

ALTER TABLE polygons3 ADD COLUMN id SERIAL PRIMARY KEY;
CREATE INDEX polygons3_geom_idx ON polygons3 USING gist (geom);

DROP TABLE IF EXISTS forests;
SELECT limit_divide_polygon(geom) as geom INTO forests FROM polygons3 WHERE type in ('0x200016', '0x200015');

ALTER TABLE forests ADD COLUMN id SERIAL PRIMARY KEY;
CREATE INDEX forests_geom_idx ON forests USING gist (geom);
