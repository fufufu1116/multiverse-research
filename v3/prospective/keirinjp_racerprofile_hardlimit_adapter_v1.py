#!/usr/bin/env python3
import hashlib, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

ALLOWED_SCHEME = 'https'
ALLOWED_HOST = 'keirin.jp'
ALLOWED_PATH = '/pc/racerprofile'
ALLOWED_QUERY_KEYS = {'snum'}
SNUM_RE = re.compile(r'^\d{5,6}$')
MIN_SPACING_SECONDS = 5.0
MAX_RESPONSE_BYTES = 2_000_000
TIMEOUT_SECONDS = 15
STATE_FILE = Path('/tmp/multiverse_keirinjp_racerprofile_last_request_v1.txt')
USER_AGENT = 'MultiverseHybridV3-Research/1.0'

class Halt(RuntimeError):
    pass

def build_url(snum: str) -> str:
    snum = str(snum)
    if not SNUM_RE.fullmatch(snum):
        raise Halt('FAIL_CLOSED invalid snum')
    return f'{ALLOWED_SCHEME}://{ALLOWED_HOST}{ALLOWED_PATH}?' + urlencode({'snum': snum})

def validate_url(url: str) -> None:
    u = urlparse(url)
    if u.scheme != ALLOWED_SCHEME:
        raise Halt('FAIL_CLOSED scheme')
    if u.hostname != ALLOWED_HOST:
        raise Halt('FAIL_CLOSED host')
    if u.path != ALLOWED_PATH:
        raise Halt('FAIL_CLOSED path')
    q = parse_qs(u.query, keep_blank_values=True)
    if set(q) != ALLOWED_QUERY_KEYS or len(q.get('snum', [])) != 1:
        raise Halt('FAIL_CLOSED query keys')
    if not SNUM_RE.fullmatch(q['snum'][0]):
        raise Halt('FAIL_CLOSED snum')
    if u.fragment:
        raise Halt('FAIL_CLOSED fragment')

def enforce_spacing() -> None:
    now = time.time()
    if STATE_FILE.exists():
        try:
            prev = float(STATE_FILE.read_text().strip())
            remaining = MIN_SPACING_SECONDS - (now - prev)
            if remaining > 0:
                time.sleep(remaining)
        except Exception:
            raise Halt('FAIL_CLOSED invalid rate state')
    STATE_FILE.write_text(str(time.time()))

def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s.replace('\u3000', ' ')).strip()

def _table_map(soup: BeautifulSoup, required_headers):
    req = list(required_headers)
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for idx, row in enumerate(rows[:-1]):
            cells = [_clean(c.get_text(' ', strip=True)) for c in row.find_all(['th','td'])]
            if all(h in cells for h in req):
                vals = [_clean(c.get_text(' ', strip=True)) for c in rows[idx+1].find_all(['th','td'])]
                if len(vals) >= len(cells):
                    return {cells[i]: vals[i] for i in range(len(cells))}
    return None

def parse_profile(content: bytes, capture_utc: str, source_url: str, content_sha256: str):
    soup = BeautifulSoup(content, 'html.parser')
    full_text = _clean(soup.get_text(' ', strip=True))
    timestamps = []
    for m in re.findall(r'20\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}', full_text):
        if m not in timestamps:
            timestamps.append(m)

    basic = _table_map(soup, ['氏名','府県','登録番号'])
    profile = _table_map(soup, ['期別','級班','脚質'])
    recent = _table_map(soup, ['勝率','2連対率','3連対率','競走得点'])
    if not basic or not profile or not recent:
        raise Halt('QUARANTINE_FAIL_CLOSED required table not found')

    result = {
        'source_url': source_url,
        'capture_timestamp_utc': capture_utc,
        'content_hash': content_sha256,
        'registration_number': _clean(basic['登録番号']),
        'name': _clean(basic['氏名']),
        'prefecture': _clean(basic['府県']),
        'term': _clean(profile['期別']),
        'class': _clean(profile['級班']),
        'style': _clean(profile['脚質']),
        'profile_updated_at': timestamps[0] if len(timestamps) >= 1 else None,
        'recent4m_updated_at': timestamps[1] if len(timestamps) >= 2 else None,
        'win_rate': _clean(recent['勝率']),
        'quinella_rate': _clean(recent['2連対率']),
        'trio_rate': _clean(recent['3連対率']),
        'score': _clean(recent['競走得点']),
        'network_used': True,
        'raw_html_persisted': False,
    }
    if result['registration_number'] != parse_qs(urlparse(source_url).query)['snum'][0]:
        raise Halt('QUARANTINE_FAIL_CLOSED registration mismatch')
    if result['style'] not in {'逃','追','両'}:
        raise Halt('QUARANTINE_FAIL_CLOSED style')
    for k in ['win_rate','quinella_rate','trio_rate']:
        if not re.fullmatch(r'\d+(?:\.\d+)?%', result[k]):
            raise Halt(f'QUARANTINE_FAIL_CLOSED {k}')
    if not re.fullmatch(r'\d+(?:\.\d+)?', result['score']):
        raise Halt('QUARANTINE_FAIL_CLOSED score')
    if result['profile_updated_at'] is None or result['recent4m_updated_at'] is None:
        raise Halt('QUARANTINE_FAIL_CLOSED update timestamp')
    return result

def fetch_one(snum: str):
    url = build_url(snum)
    validate_url(url)
    enforce_spacing()
    headers = {'User-Agent': USER_AGENT, 'Accept': 'text/html'}
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, allow_redirects=False)
    except requests.RequestException as e:
        raise Halt(f'FAIL_CLOSED transport error: {type(e).__name__}') from None
    if r.status_code in (403, 429):
        raise Halt(f'HALT_HTTP_{r.status_code}_NO_RETRY')
    if 300 <= r.status_code < 400:
        raise Halt('FAIL_CLOSED redirect')
    if r.status_code != 200:
        raise Halt(f'FAIL_CLOSED HTTP {r.status_code}')
    if len(r.content) > MAX_RESPONSE_BYTES:
        raise Halt('FAIL_CLOSED oversized response')
    ctype = r.headers.get('Content-Type','').lower()
    if 'text/html' not in ctype:
        raise Halt('FAIL_CLOSED content-type')
    capture = datetime.now(timezone.utc).isoformat()
    raw_hash = hashlib.sha256(r.content).hexdigest()
    return parse_profile(r.content, capture, url, raw_hash)

def synthetic_tests():
    out = {}
    valid = build_url('015977')
    validate_url(valid)
    out['valid_url'] = 'PASS'
    bads = [
        'http://keirin.jp/pc/racerprofile?snum=015977',
        'https://www.keirin.jp/pc/racerprofile?snum=015977',
        'https://keirin.jp/pc/race/entry?snum=015977',
        'https://keirin.jp/pc/racerprofile?snum=015977&x=1',
    ]
    for i, u in enumerate(bads):
        try:
            validate_url(u)
            out[f'bad_{i}'] = 'FAIL_NOT_REJECTED'
        except Halt:
            out[f'bad_{i}'] = 'PASS_REJECTED'
    return out

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--synthetic':
        print(json.dumps(synthetic_tests(), ensure_ascii=False, indent=2))
    elif len(sys.argv) == 3 and sys.argv[1] == '--smoke':
        print(json.dumps(fetch_one(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        raise SystemExit('usage: --synthetic | --smoke <snum>')
