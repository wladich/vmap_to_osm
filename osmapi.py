# -*- coding: utf-8 -*-

import psycopg2
import datetime

now = datetime.datetime.utcnow

class OSMDB(object):
    def __init__(self, **kwargs):
        self.conn = psycopg2.connect(**kwargs)
        self.user_id = None
        self.changeset_id = None
        self.nodes = {}
        
    def drop_node_cache(self):
        self.nodes = {}
        
    def execute(self, sql, args=None):
        cur = self.conn.cursor()                
        try:
            cur.execute(sql, args)
        except psycopg2.ProgrammingError as e:
            raise Exception(str(e) + '\n' + sql + '\n' + str(args))
        return cur

    def executemany(self, sql, args=None):
        cur = self.conn.cursor()                
        cur.executemany(sql, args)
        
    def get(self, sql, args=None):
        return self.execute(sql, args).fetchall()
        
    def vacuum(self):
        old_isolation_level = self.conn.isolation_level
        self.conn.set_isolation_level(0)
        self.execute("VACUUM")
        self.conn.set_isolation_level(old_isolation_level)
    
    def truncate(self):
        self.execute('''
            TRUNCATE TABLE current_relation_members,
            current_relation_tags,
            current_relations,
            current_way_nodes,
            current_way_tags,
            current_ways,
            current_node_tags,
            current_nodes,
            relation_members,
            relation_tags,
            relations,
            way_nodes,
            way_tags,
            ways,
            node_tags,
            nodes,
            changeset_tags,
            changesets
            RESTART IDENTITY;
            UPDATE users SET changesets_count=0;
        ''')
        self.conn.commit()
        self.vacuum()
        
    def set_current_user(self, user_name):
        self.user_id = self.get('SELECT id FROM users WHERE display_name=%s', (user_name,))[0][0]
        return self.user_id 
    
    def open_changeset(self, tags=None):
        self.changeset_id = self.get('INSERT INTO changesets (user_id, created_at, closed_at) VALUES (%s, %s, %s) RETURNING id', (self.user_id, now(), now()))[0][0]
        self.execute('UPDATE users SET changesets_count=changesets_count+1 WHERE id=%s' % self.user_id)
        if tags:
            args = ((self.changeset_id, k, v) for (k, v) in tags)
            self.executemany('INSERT INTO changeset_tags VALUES (%s, %s, %s)', args)
        self.num_changes = 0
        self.changeset_bounds= dict(min_x=2000000000, max_x=-2000000000, min_y=1000000000, max_y=-1000000000)
        return self.changeset_id 
     
    def close_changeset(self):
        self.execute('UPDATE changesets SET (closed_at, num_changes, min_lat, max_lat, min_lon, max_lon) = (%s,%s,%s,%s,%s,%s) WHERE id=%s', 
                     (now(), self.num_changes, 
                      self.changeset_bounds['min_y'], self.changeset_bounds['max_y'], 
                      self.changeset_bounds['min_x'], self.changeset_bounds['max_x'], 
                      self.changeset_id))
        self.changeset_id = None
        self.conn.commit()
        
    def close(self):
        if self.changeset_id is not None:
            self.close_changeset()
        
    def update_bounds(self, x, y):
        bounds = self.changeset_bounds
        if x <  bounds['min_x']:
            bounds['min_x'] = x
        if y < bounds['min_y']:
            bounds['min_y'] = y
        if x > bounds['max_x']:
            bounds['max_x'] = x
        if y > bounds['max_y']:
            bounds['max_y'] = y
    
#    def add_point(self, (x, y)):
#        node_id = self.get('INSERT INTO current_nodes (latitude, longitude, changeset_id, visible, "timestamp", tile, version) VALUES (%s, %s, %s, true, %s, tile_for_point(%s, %s), 1) RETURNING id',
#                 (y, x, self.changeset_id, now(), y, x))[0][0]
#        self.execute('INSERT INTO nodes (node_id, latitude, longitude, changeset_id, visible, "timestamp", tile, version) VALUES (%s, %s, %s, %s, true, %s, tile_for_point(%s, %s), 1)',
#                 (node_id, y, x, self.changeset_id, now(), y, x))
#        self.update_bounds(x, y)
#        self.num_changes += 1
#        return node_id

    def add_nodes(self, coords):
        now_ = now()
        substs_str = '(%s, %s, %s, true, %s, tile_for_point(%s, %s), 1)'
        substs_str = ','.join([substs_str] * len(coords))
        args = [[y, x, self.changeset_id, now_, y, x] for (x, y) in coords]
        args = sum(args, [])
        nodes_ids = self.get('''
          with rows as (
          INSERT INTO current_nodes (latitude, longitude, changeset_id, visible, "timestamp", tile, version) VALUES %s RETURNING id, latitude, longitude, changeset_id, visible, "timestamp", tile, version
          )
          INSERT into nodes (node_id, latitude, longitude, changeset_id, visible, "timestamp", tile, version) select id, latitude, longitude, changeset_id, visible, "timestamp", tile, version from rows returning node_id''' 
          % substs_str, args)
        nodes_ids = [n[0] for n in nodes_ids]
        for x, y in coords:
            self.update_bounds(x, y)
        self.num_changes += len(nodes_ids)
        return nodes_ids
        
        
    def get_nodes_ids(self, coords):
        new_nodes = set()
        for xy in coords:
            if not xy in self.nodes:
                new_nodes.add(xy)
        if new_nodes:
            new_ids = self.add_nodes(new_nodes)
            self.nodes.update(zip(new_nodes, new_ids))
        ids = [self.nodes[xy] for xy in coords]
        return ids
        
        
    def add_way(self, coords, tags=None):
#        nodes_ids = self.add_nodes(coords)
        #uniq_nodes = len(set(coords))
        #assert  uniq_nodes > 1, uniq_nodes
        nodes_ids = self.get_nodes_ids(coords)
        assert nodes_ids
#        if not nodes_ids:
#            return None
        way_id = self.get('INSERT INTO current_ways (changeset_id, "timestamp", visible, version) VALUES (%s, %s, true, 1) RETURNING id', 
                          (self.changeset_id, now()))[0][0]
        self.execute('INSERT INTO ways (way_id, changeset_id, "timestamp", visible, version) VALUES (%s, %s, %s, true, 1)', 
                          (way_id, self.changeset_id, now()))
        substs_str = '(%s, %s, %s)'
        substs_str = ','.join([substs_str] * len(coords))
        args = [[way_id, node_id, n] for n, node_id in enumerate(nodes_ids, 1)]
        args = sum(args, [])
        self.execute('''
        with rows as
        (INSERT INTO current_way_nodes (way_id, node_id, sequence_id) VALUES %s returning way_id, node_id, sequence_id)
        INSERT INTO way_nodes (way_id, node_id, sequence_id, version) select way_id, node_id, sequence_id, 1 from rows 
        ''' % (substs_str, ), args)
        if tags:
            args = [(way_id, k, v) for (k, v) in tags]
            self.executemany('INSERT INTO current_way_tags (way_id, k, v) VALUES (%s, %s, %s)', args)
            self.executemany('INSERT INTO way_tags (way_id, k, v, version) VALUES (%s, %s, %s, 1)', args)
        self.num_changes += 1
        return way_id
    
    def add_ways_relation(self, ways_coords, tags):
        assert len(ways_coords) > 1, len(ways_coords)
        relation_id = self.get('INSERT INTO current_relations (changeset_id, "timestamp", visible, version) VALUES (%s, %s, true, 1) RETURNING id', 
                          (self.changeset_id, now()))[0][0]
        self.execute('INSERT INTO relations (relation_id, changeset_id, "timestamp", visible, version) VALUES (%s, %s, %s, true, 1)', 
                          (relation_id, self.changeset_id, now()))
        for n, linestring in enumerate(ways_coords):
            if n == 0:
                role = 'outer'
                way_tags = tags
            else:
                role = 'inner'
                way_tags = None
            way_id = self.add_way(linestring, way_tags)
            self.execute("INSERT INTO current_relation_members (relation_id, member_type, member_id, member_role, sequence_id) VALUES (%s, 'Way', %s, '%s', %s)"
                % (relation_id, way_id, role, n))
            self.execute("INSERT INTO relation_members (relation_id, member_type, member_id, member_role, sequence_id, version) VALUES (%s, 'Way', %s, '%s', %s, 1)"
                % (relation_id, way_id, role, n))
        relation_tags = [('type', 'multipolygon')]
#        if tags:
        args = [(relation_id, k, v) for (k, v) in relation_tags]
        self.executemany('INSERT INTO current_relation_tags (relation_id, k, v) VALUES (%s, %s, %s)', args)
        self.executemany('INSERT INTO relation_tags (relation_id, k, v, version) VALUES (%s, %s, %s, 1)', args)
        self.num_changes += 1
        return relation_id
        
    def add_poi(self, coords, tags):
        point_id = self.get_nodes_ids([coords])
        assert len(point_id) == 1
        point_id = point_id[0]
        args = [(point_id, k, v) for (k, v) in tags]
        self.executemany('INSERT INTO current_node_tags (node_id, k, v) VALUES (%s, %s, %s)', args)
        self.executemany('INSERT INTO node_tags (node_id, k, v, version) VALUES (%s, %s, %s, 1)', args)
        return point_id
        
if __name__ == '__main__':
    osm = OSMDB(database='osm', user='postgres', host='127.0.0.1', port='5434')
    osm.truncate()
#    osm.set_current_user('www')
#    osm.open_changeset([('created_by', 'me'), ('comment', 'Hi')])
#    print osm.add_way([[1,2], [3,4]], [('t1', 'v2')])
#    osm.close()
