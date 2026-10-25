"""Fetch repository-declared connection classes; never infer from API/name."""
import concurrent.futures as cf
import datetime
import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.connection-cache.jsonl'
VALID = {'local_push', 'local_polling', 'cloud_push', 'cloud_polling', 'calculated', 'assumed_state'}

def verified_class(evidence):
    manifest = evidence.get('manifest', {})
    value = manifest.get('iot_class')
    if evidence.get('status') == 'ok' and manifest.get('domain') == evidence.get('domain') and value in VALID:
        return value
    return None

def apply_evidence(records, evidence_rows):
    lookup = {(row['repository'].lower(), row['domain']): row for row in evidence_rows if verified_class(row)}
    changed = 0
    for record in records:
        for method in record['methods']:
            if method.get('iot_class'):
                continue
            repo = method.get('url', '').rstrip('/').removeprefix('https://github.com/').lower()
            evidence = lookup.get((repo, record.get('domain')))
            if evidence is None:
                continue
            method['iot_class'] = verified_class(evidence)
            method['connection_evidence'] = {key: evidence[key] for key in ('url', 'sha256', 'checked_at')}
            changed += 1
        classes = [method.get('iot_class') or '' for method in record['methods']]
        record['local_option'] = bool(record.get('local_option')) or any(value.startswith('local_') for value in classes)
        record['cloud_option'] = bool(record.get('cloud_option')) or any(value.startswith('cloud_') for value in classes)
    return changed

def apply_reviewed_docs(records, evidence_rows):
    changed = 0
    for record in records:
        for method in record['methods']:
            if method.get('connection_scope') or (method.get('iot_class') or '').startswith(('local_', 'cloud_')):
                continue
            url = method.get('url', '').rstrip('/')
            repository = url.removeprefix('https://github.com/').lower()
            for evidence in evidence_rows:
                exact_record = evidence.get('record_id') == record.get('id') and evidence.get('method_url', '').rstrip('/') == url
                exact_repo = evidence.get('repository', '').lower() == repository and evidence.get('domain') == record.get('domain')
                scope = evidence.get('connection_scope')
                if not (exact_record or exact_repo) or scope not in ('local', 'cloud', 'virtual') or not evidence.get('source_url') or not evidence.get('evidence'):
                    continue
                method['connection_scope'] = scope
                method['connection_evidence'] = {key: evidence[key] for key in ('source_url', 'evidence', 'caveat', 'checked_at') if key in evidence}
                if scope in ('local', 'cloud'):
                    record[scope + '_option'] = True
                changed += 1
                break
    return changed

def apply_platform_evidence(records, evidence_rows):
    lookup = {row['id']: row for row in evidence_rows if row.get('manifest', {}).get('integration_type') == 'entity'}
    changed = 0
    for record in records:
        evidence = lookup.get(record.get('id'))
        if evidence and evidence['manifest'].get('domain') == record.get('domain') and not record.get('connection_scope') and not record.get('local_option') and not record.get('cloud_option'):
            record['connection_scope'] = 'platform'
            record['connection_evidence'] = {'source_url': evidence['source_url'], 'evidence': 'Pinned manifest integration_type=entity: basic entity platform; connection depends on the implementing integration.'}
            changed += 1
    return changed

def serialize_catalogue(data):
    """Encode JSON without HTML script parser state-changing characters."""
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', r'\u003c')


def read_catalog():
    text = (ROOT / 'index.html').read_text()
    match = re.search(r'(<script[^>]*id="catalogue-data"[^>]*>)(.*?)(</script>)', text, re.S)
    if match is None:
        raise ValueError('catalogue-data script missing')
    return text, match, json.loads(match[2])

def fetch(item):
    key, url, domain = item
    source = url.replace('https://github.com/', 'https://raw.githubusercontent.com/').rstrip('/') + '/HEAD/custom_components/' + domain + '/manifest.json'
    result = {'repository': key, 'domain': domain, 'url': source, 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        req = urllib.request.Request(source, headers={'User-Agent': 'smart-home-catalog-connection-audit'})
        with urllib.request.urlopen(req, timeout=18) as response:
            raw = response.read(500000)
        manifest = json.loads(raw)
        result.update(status='ok', sha256=hashlib.sha256(raw).hexdigest(), manifest=manifest)
    except Exception as exc:
        result.update(status='unavailable', error=str(exc))
    return result

def collect():
    _, _, data = read_catalog()
    existing = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            row = json.loads(line)
            existing[(row['repository'], row['domain'])] = row
    todo = {}
    for record in data['records']:
        for method in record['methods']:
            url = method.get('url', '').rstrip('/')
            domain = record.get('domain', '')
            if re.fullmatch(r'https://github.com/[^/]+/[^/]+', url) and re.fullmatch(r'[a-z0-9_]+', domain or '') and not method.get('iot_class'):
                key = url.removeprefix('https://github.com/').lower()
                if (key, domain) not in existing:
                    todo[(key, domain)] = (key, url, domain)
    print('Previously checked:', len(existing), 'Pending:', len(todo), flush=True)
    with CACHE.open('a') as out, cf.ThreadPoolExecutor(max_workers=28) as pool:
        for i, result in enumerate(pool.map(fetch, todo.values()), 1):
            out.write(json.dumps(result) + '\n'); out.flush()
            if i % 100 == 0:
                print('Checked', i, 'of', len(todo), flush=True)
    rows = [json.loads(line) for line in CACHE.read_text().splitlines()]
    from collections import Counter
    print('Results:', Counter(row['status'] for row in rows), flush=True)
    print('Declared classes:', Counter(row.get('manifest', {}).get('iot_class') for row in rows), flush=True)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply checked-in evidence offline, without network calls')
    args = parser.parse_args()
    if not args.apply:
        collect()
    else:
        text, match, data = read_catalog()
        manifest_rows = json.loads((ROOT / 'data/connection-manifests.json').read_text())
        reviewed_rows = json.loads((ROOT / 'data/reviewed-connections.json').read_text())
        core_rows = json.loads((ROOT / 'data/core-platform-manifests.json').read_text())
        counts = {
            'manifest_methods': apply_evidence(data['records'], manifest_rows),
            'reviewed_methods': apply_reviewed_docs(data['records'], reviewed_rows),
            'abstract_platforms': apply_platform_evidence(data['records'], core_rows),
        }
        data['metadata']['connection_audit'] = {
            'manifest_evidence': 'data/connection-manifests.json',
            'reviewed_evidence': 'data/reviewed-connections.json',
            'platform_evidence': 'data/core-platform-manifests.json',
            'note': 'Repository-declared connection location plus individually reviewed documentation/code; not installation tests. Raw HEAD URLs identify checked sources; per-source timestamps and SHA-256 identify downloaded manifest content.',
        }
        encoded = serialize_catalogue(data)
        updated = text[:match.start(2)] + encoded + text[match.end(2):]
        if updated != text:
            (ROOT / 'index.html').write_text(updated)
        print(json.dumps(counts, indent=2))
