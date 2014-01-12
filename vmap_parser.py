# -*- coding: utf-8 -*-
import re

class ParsingError(Exception):
    pass

def parse_geom_str(lines):
    pairs = sum([line.split() for line in lines], [])
    pairs = [pair.split(',') for pair in pairs]
    pairs = [('%s.%s' % (x[:-6], x[-6:]), '%s.%s' % (y[:-6], y[-6:])) for x, y in pairs]
    for x, y in pairs:
        assert 30 < float(x) < 42, x
        assert 52 < float(y) < 59, y
    return pairs

def vmap_iterator(fd):
    header = next(fd)
    if not re.match('^VMAP 3\.\d$', header):
        raise ParsingError('Invalid header')
    state = 'header'
    obj_data = None
    for line_n, line in enumerate(fd, 2):
        tag, value = line.split('\t', 1)
        tag = tag.strip()
        if state == 'header':
            if tag in ('NAME', 'RSCALE', 'STYLE', 'MP_ID', 'BRD'):
                continue
            elif tag == 'OBJECT':
                state = 'object'
            else:
                raise ParsingError('Unknon tag %s at line %d' % (tag, line_n))
        if state == 'data':
            if tag == '':
                obj_geom_str.append(value)
            elif tag == 'DATA':
                geom = parse_geom_str(obj_geom_str)
                obj_data['geom'] = obj_data.get('geom', []) + [geom]
                obj_geom_str = [value]
            elif tag == 'OBJECT':
                geom = parse_geom_str(obj_geom_str)
                obj_data['geom'] = obj_data.get('geom', []) + [geom]
                state = 'object'
            else:
                raise ParsingError('Unknon tag %s at line %d' % (tag, line_n))
        if state == 'object':
            if tag == 'OBJECT':
                if obj_data is not None:
                    if 'geom' in obj_data:
                        yield obj_data
                obj_data = {}
                value = value.split(' ', 1)
                obj_data['code'] = int(value[0], 16)
                if len(value) == 2:
                    obj_data['label'] = value[1].strip()
            elif tag == 'LABEL':
                pass
            elif tag == 'OPT':
                key, value = value.split('\t')
                if key == 'Angle':
                    obj_data['angle'] = int(value)
                else:
                    raise ParsingError('Unknon option %s at line %d' % (key, line_n))
            elif tag == 'DIR':
                obj_data['dir'] = int(value)                
            elif tag == 'COMM':
                value = value.strip()
                obj_data['comm'] = value
            elif tag == 'DATA':
                obj_geom_str = [value]
                state = 'data'
                continue
            else:
                raise ParsingError('Unknon tag %s at line %d' % (tag, line_n))
    if state == 'data':
        geom = parse_geom_str(obj_geom_str)
        obj_data['geom'] = obj_data.get('geom', []) + [geom]
    if 'geom' in obj_data:
        yield obj_data
            
                
                
        
if __name__ == '__main__':
    print len(list(vmap_iterator(open('/home/w/projects/osm-slazav/map_podm/vmap/n37-041.vmap'))))