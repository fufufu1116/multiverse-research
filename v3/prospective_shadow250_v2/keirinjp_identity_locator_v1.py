#!/usr/bin/env python3
"""
Shadow250-v2 deterministic KEIRIN.JP identity locator.

NEW-universe candidate. This component is identity/routing only:
- discovers candidate snum values only from the official KEIRIN.JP player-search form;
- queries by racecard PRE identity facts: prefecture + graduation term only;
- extracts only official /pc/racerprofile?snum=... links;
- verifies final identity by registration_number + normalized_name + prefecture + term;
- emits no predictive feature and persists no HTML.
Any form drift, pagination ambiguity, transport anomaly, or identity ambiguity => Fail-Closed.
"""
from __future__ import annotations
import hashlib, json, re, time, unicodedata
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup

SEARCH_URL="https://keirin.jp/pc/search"
ALLOWED_SCHEME="https"
ALLOWED_HOST="keirin.jp"
PROFILE_PATH="/pc/racerprofile"
MIN_SPACING_SECONDS=5.0
TIMEOUT_SECONDS=15
MAX_RESPONSE_BYTES=2_000_000
MAX_CANDIDATES=20
SNUM_RE=re.compile(r"^\d{5,6}$")

class FailClosed(RuntimeError): pass
class PersistentHalt(RuntimeError): pass

def norm(s):
    s=unicodedata.normalize("NFKC",str(s))
    s=unicodedata.normalize("NFC",s)
    return "".join(ch for ch in s if not ch.isspace())

def canon_pref(s):
    s=norm(s)
    for suf in ("都","道","府","県"):
        if s.endswith(suf) and len(s)>1:
            s=s[:-1]
            break
    return s

def rider_key(name,pref,term):
    return hashlib.sha256(f"{norm(name)}|{canon_pref(pref)}|{int(term)}".encode()).hexdigest()

class RuntimeLimiter:
    def __init__(self):
        self.last=None
        self.halted=False
    def before(self, now=None):
        if self.halted:
            raise PersistentHalt("HALTED")
        now=time.monotonic() if now is None else float(now)
        if self.last is not None and now-self.last<MIN_SPACING_SECONDS:
            raise FailClosed("REJECT spacing <5s")
        self.last=now
    def status(self, code):
        code=int(code)
        if code in (403,429):
            self.halted=True
            raise PersistentHalt(f"HALT_HTTP_{code}_NO_RETRY")
        if code!=200:
            raise FailClosed(f"FAIL_CLOSED HTTP {code}")

def _validate_same_keirin(url, allowed_paths=None):
    u=urlparse(url)
    if u.scheme!=ALLOWED_SCHEME or u.hostname!=ALLOWED_HOST or u.fragment:
        raise FailClosed("REJECT origin")
    if allowed_paths is not None and u.path not in set(allowed_paths):
        raise FailClosed(f"REJECT path {u.path}")
    return u

def _get(session,limiter,url):
    _validate_same_keirin(url)
    limiter.before()
    try:
        r=session.get(url,timeout=TIMEOUT_SECONDS,allow_redirects=False,
                      headers={"User-Agent":"MultiverseHybridV3-IdentityLocator/1.0","Accept":"text/html"})
    except requests.RequestException as e:
        raise FailClosed(f"FAIL_CLOSED transport {type(e).__name__}") from None
    if 300<=r.status_code<400:
        raise FailClosed("FAIL_CLOSED redirect")
    limiter.status(r.status_code)
    if len(r.content)>MAX_RESPONSE_BYTES:
        raise FailClosed("FAIL_CLOSED oversized")
    if "text/html" not in r.headers.get("Content-Type","").lower():
        raise FailClosed("FAIL_CLOSED content-type")
    return r

def _submit(session,limiter,method,url,payload):
    _validate_same_keirin(url)
    limiter.before()
    headers={"User-Agent":"MultiverseHybridV3-IdentityLocator/1.0","Accept":"text/html"}
    try:
        if method=="get":
            r=session.get(url,params=payload,timeout=TIMEOUT_SECONDS,allow_redirects=False,headers=headers)
        elif method=="post":
            r=session.post(url,data=payload,timeout=TIMEOUT_SECONDS,allow_redirects=False,headers=headers)
        else:
            raise FailClosed(f"REJECT form method {method}")
    except requests.RequestException as e:
        raise FailClosed(f"FAIL_CLOSED transport {type(e).__name__}") from None
    if 300<=r.status_code<400:
        raise FailClosed("FAIL_CLOSED redirect")
    limiter.status(r.status_code)
    if len(r.content)>MAX_RESPONSE_BYTES:
        raise FailClosed("FAIL_CLOSED oversized")
    if "text/html" not in r.headers.get("Content-Type","").lower():
        raise FailClosed("FAIL_CLOSED content-type")
    return r

def _candidate_forms(html_bytes):
    soup=BeautifulSoup(html_bytes,"html.parser")
    required=("名字","名前","登録番号","府県","卒業期","級班","脚質")
    out=[]
    for f in soup.find_all("form"):
        txt=norm(f.get_text(" ",strip=True))
        if all(x in txt for x in required):
            out.append(f)
    if len(out)!=1:
        raise FailClosed(f"REJECT search form cardinality={len(out)}")
    return out[0]

def _control_after_label(form,label):
    label=norm(label)
    hits=[]
    for tr in form.find_all("tr"):
        cells=tr.find_all(["th","td"],recursive=False)
        for i,cell in enumerate(cells):
            if label not in norm(cell.get_text(" ",strip=True)):
                continue
            search_cells=cells[i+1:]+[cell]
            for c in search_cells:
                ctrl=c.find(["input","select","textarea"],attrs={"name":True})
                if ctrl is not None:
                    hits.append(ctrl)
                    break
    by_name={h.get("name"):h for h in hits if h.get("name")}
    if len(by_name)!=1:
        raise FailClosed(f"REJECT field mapping label={label} names={sorted(by_name)}")
    return next(iter(by_name.values()))

def _select_pref_value(select,pref):
    want=canon_pref(pref)
    vals=[]
    for opt in select.find_all("option"):
        if canon_pref(opt.get_text(" ",strip=True))==want and opt.get("value") not in (None,""):
            vals.append(opt.get("value"))
    if len(vals)!=1:
        raise FailClosed(f"REJECT prefecture option cardinality={len(vals)} pref={pref}")
    return vals[0]

def build_search_request(html_bytes,pref,term,base_url=SEARCH_URL):
    form=_candidate_forms(html_bytes)
    pref_ctrl=_control_after_label(form,"府県")
    term_ctrl=_control_after_label(form,"卒業期")
    if pref_ctrl.name!="select" or term_ctrl.name!="input":
        raise FailClosed("REJECT unexpected control types")

    payload={}
    for inp in form.find_all("input",attrs={"name":True}):
        typ=(inp.get("type") or "text").lower()
        if typ=="hidden":
            payload[inp["name"]]=inp.get("value","")
    payload[pref_ctrl["name"]]=_select_pref_value(pref_ctrl,pref)
    payload[term_ctrl["name"]]=str(int(term))

    submits=[]
    for inp in form.find_all(["input","button"],attrs={"name":True}):
        typ=(inp.get("type") or "").lower()
        text=norm(inp.get("value","") or inp.get_text(" ",strip=True))
        if typ=="submit" and ("検索" in text or text==""):
            submits.append(inp)
    if len(submits)>1:
        raise FailClosed("REJECT ambiguous submit controls")
    if len(submits)==1:
        payload[submits[0]["name"]]=submits[0].get("value","")

    method=(form.get("method") or "get").lower()
    action=urljoin(base_url,form.get("action") or base_url)
    u=_validate_same_keirin(action)
    if not (u.path=="/pc/search" or u.path.startswith("/pc/search/")):
        raise FailClosed(f"REJECT search action path={u.path}")
    if method not in {"get","post"}:
        raise FailClosed(f"REJECT form method={method}")
    return method,action,payload

def extract_candidate_snums(search_result_bytes):
    soup=BeautifulSoup(search_result_bytes,"html.parser")
    snums=set()
    for a in soup.find_all("a",href=True):
        absu=urljoin(SEARCH_URL,a["href"])
        try:
            u=_validate_same_keirin(absu,[PROFILE_PATH])
        except FailClosed:
            continue
        q=parse_qs(u.query,keep_blank_values=True)
        if set(q)!={"snum"} or len(q["snum"])!=1 or not SNUM_RE.fullmatch(q["snum"][0]):
            continue
        snums.add(q["snum"][0])

    for a in soup.find_all("a",href=True):
        t=norm(a.get_text(" ",strip=True))
        if t in {"次へ","次","NEXT","Next",">",">>"}:
            raise FailClosed("REJECT paginated search result")
    out=sorted(snums)
    if not out:
        raise FailClosed("QUARANTINE_FAIL_CLOSED no candidate snum")
    if len(out)>MAX_CANDIDATES:
        raise FailClosed(f"QUARANTINE_FAIL_CLOSED too many candidates={len(out)}")
    return out

def _clean(s):
    return re.sub(r"\s+"," ",str(s).replace("\u3000"," ")).strip()

def _table_map(soup,required_headers):
    req=list(required_headers)
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        for idx,row in enumerate(rows[:-1]):
            cells=[_clean(c.get_text(" ",strip=True)) for c in row.find_all(["th","td"])]
            if all(h in cells for h in req):
                vals=[_clean(c.get_text(" ",strip=True)) for c in rows[idx+1].find_all(["th","td"])]
                if len(vals)>=len(cells):
                    return {cells[i]:vals[i] for i in range(len(cells))}
    return None

def parse_identity_profile(content,source_url):
    u=_validate_same_keirin(source_url,[PROFILE_PATH])
    q=parse_qs(u.query,keep_blank_values=True)
    if set(q)!={"snum"} or len(q["snum"])!=1 or not SNUM_RE.fullmatch(q["snum"][0]):
        raise FailClosed("REJECT profile snum query")
    soup=BeautifulSoup(content,"html.parser")
    basic=_table_map(soup,["氏名","府県","登録番号"])
    prof=_table_map(soup,["期別"])
    if not basic or not prof:
        raise FailClosed("QUARANTINE_FAIL_CLOSED identity tables")
    term=re.sub(r"\D","",_clean(prof["期別"]))
    if not term:
        raise FailClosed("QUARANTINE_FAIL_CLOSED identity term")
    got={
        "registration_number":_clean(basic["登録番号"]),
        "name":_clean(basic["氏名"]),
        "prefecture":_clean(basic["府県"]),
        "term":int(term),
    }
    if got["registration_number"]!=q["snum"][0]:
        raise FailClosed("QUARANTINE_FAIL_CLOSED registration mismatch")
    return got

def _fetch_identity(session,limiter,snum):
    url=f"https://{ALLOWED_HOST}{PROFILE_PATH}?"+urlencode({"snum":str(snum)})
    r=_get(session,limiter,url)
    return parse_identity_profile(r.content,url),hashlib.sha256(r.content).hexdigest()

def verify_identity(got,expected_name,expected_pref,expected_term):
    return (
        norm(got["name"])==norm(expected_name)
        and canon_pref(got["prefecture"])==canon_pref(expected_pref)
        and int(got["term"])==int(expected_term)
        and SNUM_RE.fullmatch(str(got["registration_number"])) is not None
    )

def resolve_snum(expected_name,expected_pref,expected_term):
    s=requests.Session()
    lim=RuntimeLimiter()
    landing=_get(s,lim,SEARCH_URL)
    method,action,payload=build_search_request(landing.content,expected_pref,expected_term,SEARCH_URL)
    time.sleep(MIN_SPACING_SECONDS)
    result=_submit(s,lim,method,action,payload)
    candidates=extract_candidate_snums(result.content)

    matches=[]
    identity_receipts=[]
    for snum in candidates:
        time.sleep(MIN_SPACING_SECONDS)
        try:
            ident,raw_hash=_fetch_identity(s,lim,snum)
        except FailClosed as e:
            identity_receipts.append({"snum":snum,"status":"NONMATCH_OR_QUARANTINE","reason":str(e)})
            continue
        ok=verify_identity(ident,expected_name,expected_pref,expected_term)
        identity_receipts.append({
            "snum":snum,"status":"MATCH" if ok else "NONMATCH",
            "identity_hash":hashlib.sha256(
                f"{norm(ident['name'])}|{canon_pref(ident['prefecture'])}|{int(ident['term'])}|{ident['registration_number']}".encode()
            ).hexdigest(),
            "profile_raw_sha256":raw_hash,
        })
        if ok:
            matches.append(snum)

    if len(matches)!=1:
        raise FailClosed(f"QUARANTINE_FAIL_CLOSED verified match cardinality={len(matches)}")

    return {
        "status":"PASS_VERIFIED_IDENTITY_LOCATOR_ONLY",
        "snum":matches[0],
        "rider_key":rider_key(expected_name,expected_pref,expected_term),
        "query_basis":["prefecture","term"],
        "final_identity_checks":["registration_number","normalized_name","prefecture","term"],
        "candidate_snums":candidates,
        "search_landing_sha256":hashlib.sha256(landing.content).hexdigest(),
        "search_result_sha256":hashlib.sha256(result.content).hexdigest(),
        "search_method":method,
        "search_action":action,
        "search_payload_sha256":hashlib.sha256(
            json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
        ).hexdigest(),
        "identity_receipts":identity_receipts,
        "predictive_features_emitted":False,
        "raw_html_persisted":False,
        "capture_timestamp_utc":datetime.now(timezone.utc).isoformat(),
    }

def synthetic_tests():
    html="""
    <html><body><form method="get" action="/pc/search">
    <table>
      <tr><td>名字（全角カナ）</td><td><input name="f_kana"></td><td>名前（全角カナ）</td><td><input name="g_kana"></td></tr>
      <tr><td>名字（漢字）</td><td><input name="f_kanji"></td><td>名前（漢字）</td><td><input name="g_kanji"></td></tr>
      <tr><td>登録番号</td><td><input name="reg"></td><td>府県</td><td><select name="pref"><option value="">-</option><option value="33">岡山県</option></select></td></tr>
      <tr><td>卒業期</td><td><input name="term"></td><td>級班</td><td><select name="cls"></select></td></tr>
      <tr><td>脚質</td><td><select name="style"></select></td></tr>
    </table><input type="hidden" name="stgt" value="1"><input type="submit" name="go" value="検索">
    </form></body></html>
    """.encode("utf-8")
    method,action,payload=build_search_request(html,"岡山",127)
    assert method=="get" and action=="https://keirin.jp/pc/search"
    assert payload["pref"]=="33" and payload["term"]=="127" and payload["stgt"]=="1" and payload["go"]=="検索"

    result='<a href="/pc/racerprofile?snum=015918">x</a><a href="/pc/racerprofile?snum=015917">y</a>'.encode('utf-8')
    assert extract_candidate_snums(result)==["015917","015918"]
    return {"status":"PASS","network_used":False}

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--synthetic",action="store_true")
    ap.add_argument("--resolve",nargs=3,metavar=("NAME","PREF","TERM"))
    args=ap.parse_args()
    if args.synthetic:
        print(json.dumps(synthetic_tests(),ensure_ascii=False))
    elif args.resolve:
        name,pref,term=args.resolve
        print(json.dumps(resolve_snum(name,pref,int(term)),ensure_ascii=False,indent=2))
    else:
        raise SystemExit("FAIL_CLOSED use --synthetic or --resolve NAME PREF TERM")
