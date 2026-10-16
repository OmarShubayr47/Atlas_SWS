"""Check downloaded rack meshes and centre each separate part for an A1 plate.

Only translates coordinates; retains Onshape's checked print rotations and scale.
Mesh closure/bounds are geometric checks, not print or load verification.
"""
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path

JOB = Path(__file__).resolve().parents[1] / 'print_jobs/20261013'


def main():
    outputs = []
    source = sorted((JOB / 'stl').glob('*.stl'))
    if len(source) != 13:
        raise ValueError(f'Expected 13 structural meshes, found {len(source)}')
    target = JOB / 'centred_stl'
    target.mkdir(exist_ok=True)
    for path in source:
        raw = path.read_bytes()
        count = struct.unpack_from('<I', raw, 80)[0]
        if len(raw) != 84 + count * 50:
            raise ValueError(f'Invalid binary STL length: {path.name}')
        faces = [struct.unpack_from('<12fH', raw, 84 + i * 50) for i in range(count)]
        vertices = [tuple(f[j:j+3]) for f in faces for j in (3, 6, 9)]
        if any(not math.isfinite(c) for v in vertices for c in v):
            raise ValueError(f'Nonfinite vertex: {path.name}')
        lo = [min(v[i] for v in vertices) for i in range(3)]
        hi = [max(v[i] for v in vertices) for i in range(3)]
        dims = [hi[i] - lo[i] for i in range(3)]
        if max(dims) > 240.01 or abs(lo[2]) > .01:
            raise ValueError(f'Unexpected oriented print bounds: {path.name} {lo} {dims}')
        edges = Counter()
        # Native binary vertices share exact float coordinates. Count topology.
        for f in faces:
            tri = [tuple(f[j:j+3]) for j in (3, 6, 9)]
            for a, b in zip(tri, tri[1:] + tri[:1]):
                edges[tuple(sorted((a, b)))] += 1
        bad = sum(n != 2 for n in edges.values())
        if bad:
            raise ValueError(f'{bad} nonmanifold/boundary edges: {path.name}')
        shift = [128 - (hi[0]+lo[0])/2, 128 - (hi[1]+lo[1])/2, -lo[2]]
        payload = bytearray(raw)
        for i, f in enumerate(faces):
            values = list(f)
            for j in (3, 6, 9):
                for axis in range(3):
                    values[j+axis] += shift[axis]
            struct.pack_into('<12fH', payload, 84+i*50, *values)
        number = path.name.split(' - ')[2].split()[0]
        output = target / f'rack_{number}.stl'
        output.write_bytes(payload)
        outputs.append({'part': number, 'source': path.name, 'centred': output.name,
                        'triangles': count, 'dimensions_mm': dims,
                        'boundary_or_nonmanifold_edges': bad,
                        'translation_mm': shift,
                        'source_sha256': hashlib.sha256(raw).hexdigest(),
                        'centred_sha256': hashlib.sha256(payload).hexdigest()})
        print(f'{number}: {count} triangles, {dims}, closed edge topology')
    (JOB / 'mesh_checks.json').write_text(json.dumps({'date': '2026-10-13',
        'status': 'Geometric mesh check passed; physical print/load not tested',
        'parts': outputs}, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
