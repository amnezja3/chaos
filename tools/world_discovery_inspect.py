"""Inspect saved provider responses offline. Never calls an API or writes a DB."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.world_adapters import (
    GEOAPIFY_VERSION, MAPLARK_VERSION, normalize_geoapify, normalize_maplark)
from poi_infrastructure.world_contract import ContractError, Provenance


def read_json(path):
    with Path(path).open('rb') as f:
        raw = f.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ContractError('input_size_limit')
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def inspect(provider, body, headers=None, *, page_limit=100):
    provenance = Provenance(provider, MAPLARK_VERSION if provider == 'maplark' else GEOAPIFY_VERSION,
                            'offline-inspection', 0)
    if provider == 'maplark':
        batch = normalize_maplark(body, headers or {}, provenance)
    elif provider == 'geoapify':
        batch = normalize_geoapify(body, provenance, page_limit=page_limit)
    else:
        raise ContractError('provider_unknown')
    return {'ok': True, 'mode': 'offline', 'provider': provider, 'objects': len(batch.objects),
            'layers': dict(Counter(layer for obj in batch.objects for layer in obj.layers)),
            'geometries': dict(Counter(obj.geometry.kind for obj in batch.objects if obj.geometry)),
            'response_completeness': batch.completeness, 'reasons': batch.reasons,
            'selection': batch.selection, 'gameplay_approved': False, 'network_calls': 0,
            'production_changed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=('maplark', 'geoapify'), required=True)
    parser.add_argument('--body', required=True, help='Saved JSON response; no API key needed')
    parser.add_argument('--headers', help='JSON dictionary of response headers (not request headers)')
    parser.add_argument('--page-limit', type=int, default=100, help='Actual Geoapify page limit')
    args = parser.parse_args()
    try:
        body, digest = read_json(args.body)
        headers, headers_digest = read_json(args.headers) if args.headers else ({}, None)
        result = inspect(args.provider, body, headers, page_limit=args.page_limit)
        result.update(body_sha256=digest, headers_sha256=headers_digest)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        # Never print payloads, input paths, request headers or exception chains.
        print(json.dumps({'ok': False, 'error': str(exc) if isinstance(exc, ContractError) else 'input_invalid',
                          'network_calls': 0, 'production_changed': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
