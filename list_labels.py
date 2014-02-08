# -*- coding: utf-8 -*-
import unipath
from vmap_parser import vmap_iterator
from collections import Counter

src_dir = unipath.Path('./tmp/map_podm/vmap')
dest_dir = unipath.Path('./tmp/labels')
dest_dir.mkdir()
labels = {}

for fn in src_dir.listdir('*.vmap'):
    for obj in vmap_iterator(open(fn)):
        label = obj.get('label', '').strip()
        if label:
            code = obj['code']
            code_labels = labels.get(code, Counter())
            code_labels[label] += 1
            labels[code] = code_labels


for code, labels in labels.items():
    with open(dest_dir.child(hex(code)), 'w') as f:
        labels = labels.items()
        labels.sort(key=lambda x: x[1], reverse=True)
        for label, n in labels:
            print >> f, n, label

