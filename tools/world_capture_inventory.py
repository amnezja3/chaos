"""Bounded offline inventory of saved geographic evidence, not source certification."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024
MAX_FILES = 128


def read(path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('file_size_limit')
    return raw, json.loads(raw)


def inspect_file(path):
    raw, body = read(path)
    result = dict(file=path.name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                  evidence='unclassified', certification=False)
    metadata_path = path.with_suffix('.metadata.json')
    if metadata_path.is_file():
        _, metadata = read(metadata_path)
        expected = metadata.get('fixture_sha256_lf')
        actual = hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()
        result['fixture_digest_matches'] = bool(expected and actual == expected)
        result['evidence'] = ('synthetic' if metadata.get('synthetic') is True else
                              'recorded_response' if metadata.get('synthetic') is False and expected == actual else
                              'verified_fixture_origin_unspecified' if expected == actual else
                              'unverified_metadata')
    elif 'synthetic' in path.name:
        result['evidence'] = 'synthetic_filename_only'
    if not isinstance(body, dict) or body.get('type') != 'FeatureCollection':
        result['format'] = 'other_json'
        return result
    features = body.get('features')
    if not isinstance(features, list) or len(features) > 10000:
        raise ValueError('feature_limit_or_format')
    from shapely.geometry import shape
    types = Counter(); tags = Counter(); valid = Counter(); holes = 0; invalid = 0
    for feature in features:
        if not isinstance(feature, dict):
            invalid += 1; continue
        geometry = feature.get('geometry')
        kind = geometry.get('type') if isinstance(geometry, dict) else None
        types[kind if kind in ('Point','LineString','Polygon','MultiPolygon','MultiLineString','MultiPoint','GeometryCollection') else 'missing_or_unknown'] += 1
        try:
            obj = shape(geometry)
            if obj.is_empty or not obj.is_valid:raise ValueError('invalid_geometry')
            valid[obj.geom_type] += 1
            polygons = list(obj.geoms) if obj.geom_type == 'MultiPolygon' else [obj] if obj.geom_type == 'Polygon' else []
            holes += sum(len(p.interiors) for p in polygons)
        except (ValueError,TypeError,AttributeError,IndexError,KeyError):
            invalid += 1
        props = feature.get('properties') or {}
        if isinstance(props,dict):
            props = props.get('tags',props)
            if isinstance(props,dict):
                for key in ('shop','amenity','office','healthcare','atm','man_made','highway','waterway','natural'):
                    if key in props:tags[key] += 1
    result.update(format='geojson',objects=len(features),geometry_types=dict(types),
                  valid_geometry_types=dict(valid),interior_rings=holes,invalid_geometries=invalid,
                  classification_keys=dict(tags))
    return result


def inventory(roots):
    items=[]; seen=set(); truncated=False; missing=[]
    for root in roots:
        root=Path(root)
        if not root.exists():
            missing.append(root.name);continue
        candidates=[root] if root.is_file() else root.rglob('*.json')
        for path in candidates:
            resolved=path.resolve()
            if resolved in seen:continue
            if len(seen)>=MAX_FILES:
                truncated=True;break
            seen.add(resolved)
            try:
                entry=inspect_file(path)
            except (OSError,ValueError,RecursionError,TypeError,AttributeError):
                entry=dict(file=path.name,status='unreadable_or_invalid',certification=False)
            entry['relative_path']=path.relative_to(root).as_posix() if root.is_dir() else path.name
            entry['root']=root.name
            items.append(entry)
        if truncated:break
    return dict(status='inventory',network_calls=0,production_writes=0,items=items,truncated=truncated,missing_roots=missing,
                note='Counts describe saved files only; duplicates are not independent evidence. No coverage, source version or provider approval is granted.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths',nargs='+',type=Path)
    args=parser.parse_args()
    print(json.dumps(inventory(args.paths),ensure_ascii=True,indent=2))


if __name__=='__main__':main()
