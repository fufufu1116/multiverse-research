#!/usr/bin/env python3
"""Shadow250-v2 KEIRIN.JP identity locator v3 candidate.
Candidate-only, NOT ACTIVE. Operational semantics match live-proven locator v2;
v3 corrects only the bundled Japanese synthetic fixtures by declaring UTF-8.
"""
from __future__ import annotations
import hashlib,json,re,time,unicodedata
from datetime import datetime,timezone
from urllib.parse import parse_qs,urlencode,urljoin,urlparse
import requests
from bs4 import BeautifulSoup
ALLOWED_SCHEME='https';ALLOWED_HOST='keirin.jp';SEARCH_LANDING_PATH='/pc/search';SEARCH_RESULT_PATH='/pc/racersearchresult';PROFILE_PATH='/pc/racerprofile';SEARCH_URL=f'{ALLOWED_SCHEME}://{ALLOWED_HOST}{SEARCH_LANDING_PATH}'
INPUT_FORM_NAME='PJ0501_02InputForm';SUBMIT_FORM_NAME='PJ0501_02SubmitForm';PROFILE_FORM_NAME='PJ0504SensyuLinkForm';PREF_CONTROL_NAME='UNQ_select_21';TERM_CONTROL_NAME='UNQ_orexpandText_22';ACTIVE_CONTROL_NAME='UNQ_checkbox_34';SEARCH_BUTTON_NAME='btnSearchSensyu';SEARCH_BUTTON_ONCLICK='sensyuSearchExec()'
SEARCH_RESULT_QUERY_KEYS=('dppg','srmd','gGaiteiCD','tikuCD','nen','bKeirinCD','kSyuruiCD','girlsKBN','nameSeiKana','nameMeiKana','nameSei','nameMei','snum','hukenCD','sotugyouki','kuniCD','seibetuCD','kyuhanCD','tikuCDSensyu','age','bHomebankCD','homekyogiCD','kyakusituCD','ckbn','stgt')
FIXED_QUERY_VALUES={'dppg':'1','srmd':'01','stgt':'1'};SNUM_RE=re.compile(r'^\d{5,6}$');SENSYU_ONCLICK_RE=re.compile(r"^sensyuLink\('(\d{5,6})'\)$");MIN_SPACING_SECONDS=5.0;TIMEOUT_SECONDS=15;MAX_RESPONSE_BYTES=2_000_000;MAX_SEARCH_RESULTS=10;MAX_LOCATOR_ELAPSED_SECONDS=60.0
class FailClosed(RuntimeError):pass
class PersistentHalt(RuntimeError):pass
def norm(s):
    s=unicodedata.normalize('NFKC',str(s));s=unicodedata.normalize('NFC',s);return ''.join(ch for ch in s if not ch.isspace())
def canon_pref(s):
    s=norm(s)
    for suf in ('都','道','府','県'):
        if s.endswith(suf) and len(s)>1:return s[:-1]
    return s
def rider_key(name,pref,term):return hashlib.sha256(f'{norm(name)}|{canon_pref(pref)}|{int(term)}'.encode()).hexdigest()
class RuntimeLimiter:
    def __init__(self):self.last=None;self.halted=False
    def before(self,now=None):
        if self.halted:raise PersistentHalt('HALTED')
        now=time.monotonic() if now is None else float(now)
        if self.last is not None and now-self.last<MIN_SPACING_SECONDS:raise FailClosed('REJECT spacing <5s')
        self.last=now
    def status(self,code):
        code=int(code)
        if code in (403,429):self.halted=True;raise PersistentHalt(f'HALT_HTTP_{code}_NO_RETRY')
        if code!=200:raise FailClosed(f'FAIL_CLOSED HTTP {code}')
def _validate_url(url,exact_path,allowed_query_keys=None):
    u=urlparse(url)
    if u.scheme!=ALLOWED_SCHEME or u.hostname!=ALLOWED_HOST or u.fragment:raise FailClosed('REJECT origin')
    if u.path!=exact_path:raise FailClosed(f'REJECT path {u.path}')
    q=parse_qs(u.query,keep_blank_values=True)
    if allowed_query_keys is None:
        if q:raise FailClosed('REJECT unexpected query')
    elif set(q)!=set(allowed_query_keys):raise FailClosed(f'REJECT query key set={sorted(q)}')
    return u
def _request(session,limiter,method,url,params=None):
    u=urlparse(url)
    if u.scheme!=ALLOWED_SCHEME or u.hostname!=ALLOWED_HOST or u.fragment:raise FailClosed('REJECT request origin')
    limiter.before();headers={'User-Agent':'MultiverseHybridV3-IdentityLocator/3.0','Accept':'text/html'}
    try:
        if method=='get':r=session.get(url,params=params,timeout=TIMEOUT_SECONDS,allow_redirects=False,headers=headers)
        else:raise FailClosed(f'REJECT method {method}')
    except requests.RequestException as e:raise FailClosed(f'FAIL_CLOSED transport {type(e).__name__}') from None
    if 300<=r.status_code<400:raise FailClosed('FAIL_CLOSED redirect')
    limiter.status(r.status_code)
    if len(r.content)>MAX_RESPONSE_BYTES:raise FailClosed('FAIL_CLOSED oversized')
    if 'text/html' not in r.headers.get('Content-Type','').lower():raise FailClosed('FAIL_CLOSED content-type')
    return r
def _find_exact_form(soup,name):
    xs=soup.find_all('form',attrs={'name':name})
    if len(xs)!=1:raise FailClosed(f'REJECT form {name} cardinality={len(xs)}')
    return xs[0]
def _find_named_control(form,name,tag=None):
    xs=form.find_all(attrs={'name':name});xs=[x for x in xs if tag is None or x.name==tag]
    if len(xs)!=1:raise FailClosed(f'REJECT control {name} cardinality={len(xs)}')
    return xs[0]
def _select_pref_value(select,pref):
    want=canon_pref(pref);vals=[]
    for opt in select.find_all('option'):
        if canon_pref(opt.get_text(' ',strip=True))==want and opt.get('value') not in (None,''):vals.append(str(opt.get('value')))
    if len(vals)!=1:raise FailClosed(f'REJECT prefecture option cardinality={len(vals)} pref={pref}')
    return vals[0]
def _verify_search_landing(html_bytes,expected_pref,expected_term):
    soup=BeautifulSoup(html_bytes,'html.parser');input_form=_find_exact_form(soup,INPUT_FORM_NAME);pref_ctrl=_find_named_control(input_form,PREF_CONTROL_NAME,'select');term_ctrl=_find_named_control(input_form,TERM_CONTROL_NAME,'input');active_ctrl=_find_named_control(input_form,ACTIVE_CONTROL_NAME,'input');button=_find_named_control(input_form,SEARCH_BUTTON_NAME,'button')
    if (term_ctrl.get('type') or '').lower() not in {'tel','text'}:raise FailClosed('REJECT term control type')
    if (active_ctrl.get('type') or '').lower()!='checkbox':raise FailClosed('REJECT active control type')
    if (button.get('type') or '').lower()!='button':raise FailClosed('REJECT search button type')
    if norm(button.get_text(' ',strip=True))!='検索':raise FailClosed('REJECT search button label')
    if (button.get('onclick') or '').strip()!=SEARCH_BUTTON_ONCLICK:raise FailClosed('REJECT search button onclick')
    submit=_find_exact_form(soup,SUBMIT_FORM_NAME);action=urljoin(SEARCH_URL,submit.get('action') or '');_validate_url(action,SEARCH_RESULT_PATH)
    if (submit.get('method') or '').lower()!='get':raise FailClosed('REJECT submit form method')
    hidden={}
    for x in submit.find_all('input',attrs={'name':True}):
        if (x.get('type') or '').lower()!='hidden':raise FailClosed('REJECT non-hidden submit control')
        if x['name'] in hidden:raise FailClosed(f"REJECT duplicate submit key {x['name']}")
        hidden[x['name']]='' if x.get('value') is None else str(x.get('value'))
    if set(hidden)!=set(SEARCH_RESULT_QUERY_KEYS):raise FailClosed(f'REJECT submit key set={sorted(hidden)}')
    if hidden.get('dppg')!='1' or hidden.get('srmd')!='01':raise FailClosed('REJECT fixed submit defaults')
    page_text=html_bytes.decode('utf-8','replace');required_js=['function sensyuSearchExec()','document.PJ0501_02SubmitForm.hukenCD.value = document.getElementById("UNQ_select_21").value;','document.PJ0501_02SubmitForm.sotugyouki.value = document.getElementById("UNQ_orexpandText_22").value;','document.getElementById("UNQ_checkbox_34").checked','document.PJ0501_02SubmitForm.stgt.value = "1";','document.PJ0501_02SubmitForm.stgt.value = "2";']
    missing=[x for x in required_js if x not in page_text]
    if missing:raise FailClosed(f'REJECT search JS semantic drift count={len(missing)}')
    payload={k:'' for k in SEARCH_RESULT_QUERY_KEYS};payload.update({'dppg':'1','srmd':'01','hukenCD':_select_pref_value(pref_ctrl,expected_pref),'sotugyouki':str(int(expected_term)),'stgt':'1'});return action,payload
def _validate_profile_link_form(soup):
    f=_find_exact_form(soup,PROFILE_FORM_NAME);action=urljoin(f'{ALLOWED_SCHEME}://{ALLOWED_HOST}{SEARCH_RESULT_PATH}',f.get('action') or '');_validate_url(action,PROFILE_PATH)
    if (f.get('method') or '').lower()!='get':raise FailClosed('REJECT profile link form method')
    xs=f.find_all('input',attrs={'name':'snum'})
    if len(xs)!=1 or (xs[0].get('type') or '').lower()!='hidden':raise FailClosed('REJECT profile link snum control')
    return True
def extract_identity_candidates(search_result_bytes):
    soup=BeautifulSoup(search_result_bytes,'html.parser');_validate_profile_link_form(soup);page_text=' '.join(soup.stripped_strings);m=re.search(r'ページ\s*:\s*(\d+)\s*/\s*(\d+)',page_text)
    if not m:raise FailClosed('REJECT result pagination marker missing')
    if (int(m.group(1)),int(m.group(2)))!=(1,1):raise FailClosed(f'REJECT paginated result {m.group(1)}/{m.group(2)}')
    records=[]
    for a in soup.find_all('a',href=True):
        if (a.get('href') or '').strip()!='javascript:void(0)':continue
        mm=SENSYU_ONCLICK_RE.fullmatch((a.get('onclick') or '').strip())
        if not mm:continue
        name=norm(a.get_text(' ',strip=True))
        if not name:raise FailClosed('REJECT empty candidate name')
        records.append({'snum':mm.group(1),'name':name})
    dedup={}
    for rec in records:
        prev=dedup.get(rec['snum'])
        if prev is not None and prev!=rec['name']:raise FailClosed('REJECT duplicate snum with conflicting names')
        dedup[rec['snum']]=rec['name']
    records=[{'snum':k,'name':v} for k,v in sorted(dedup.items())]
    if not records:raise FailClosed('QUARANTINE_FAIL_CLOSED no identity candidates')
    if len(records)>MAX_SEARCH_RESULTS:raise FailClosed(f'QUARANTINE_FAIL_CLOSED too many search results={len(records)}')
    return records
def _clean(s):return re.sub(r'\s+',' ',str(s).replace('\u3000',' ')).strip()
def _table_map(soup,required_headers):
    req=list(required_headers)
    for table in soup.find_all('table'):
        rows=table.find_all('tr')
        for idx,row in enumerate(rows[:-1]):
            cells=[_clean(c.get_text(' ',strip=True)) for c in row.find_all(['th','td'])]
            if all(h in cells for h in req):
                vals=[_clean(c.get_text(' ',strip=True)) for c in rows[idx+1].find_all(['th','td'])]
                if len(vals)>=len(cells):return {cells[i]:vals[i] for i in range(len(cells))}
    return None
def parse_identity_profile(content,source_url):
    u=_validate_url(source_url,PROFILE_PATH,{'snum'});q=parse_qs(u.query,keep_blank_values=True)
    if len(q.get('snum',[]))!=1 or not SNUM_RE.fullmatch(q['snum'][0]):raise FailClosed('REJECT profile snum query')
    soup=BeautifulSoup(content,'html.parser');basic=_table_map(soup,['氏名','府県','登録番号']);prof=_table_map(soup,['期別'])
    if not basic or not prof:raise FailClosed('QUARANTINE_FAIL_CLOSED identity tables')
    term=re.sub(r'\D','',_clean(prof['期別']))
    if not term:raise FailClosed('QUARANTINE_FAIL_CLOSED identity term')
    got={'registration_number':_clean(basic['登録番号']),'name':_clean(basic['氏名']),'prefecture':_clean(basic['府県']),'term':int(term)}
    if got['registration_number']!=q['snum'][0]:raise FailClosed('QUARANTINE_FAIL_CLOSED registration mismatch')
    return got
def verify_identity(got,expected_name,expected_pref,expected_term,expected_snum):
    if str(got['registration_number'])!=str(expected_snum):raise FailClosed('QUARANTINE_FAIL_CLOSED registration mismatch')
    if norm(got['name'])!=norm(expected_name):raise FailClosed('QUARANTINE_FAIL_CLOSED name mismatch')
    if canon_pref(got['prefecture'])!=canon_pref(expected_pref):raise FailClosed('QUARANTINE_FAIL_CLOSED prefecture mismatch')
    if int(got['term'])!=int(expected_term):raise FailClosed('QUARANTINE_FAIL_CLOSED term mismatch')
    return True
def _elapsed_guard(started):
    elapsed=time.monotonic()-started
    if elapsed>MAX_LOCATOR_ELAPSED_SECONDS:raise FailClosed('QUARANTINE_FAIL_CLOSED locator elapsed budget exceeded')
    return elapsed
def resolve_snum(expected_name,expected_pref,expected_term):
    started=time.monotonic();s=requests.Session();lim=RuntimeLimiter();landing=_request(s,lim,'get',SEARCH_URL);_elapsed_guard(started);action,payload=_verify_search_landing(landing.content,expected_pref,expected_term);time.sleep(MIN_SPACING_SECONDS);result=_request(s,lim,'get',action,params=payload);_elapsed_guard(started);candidates=extract_identity_candidates(result.content);matches=[r for r in candidates if norm(r['name'])==norm(expected_name)]
    if len(matches)!=1:raise FailClosed(f'QUARANTINE_FAIL_CLOSED search name match cardinality={len(matches)}')
    chosen=matches[0];time.sleep(MIN_SPACING_SECONDS);url=f'{ALLOWED_SCHEME}://{ALLOWED_HOST}{PROFILE_PATH}?'+urlencode({'snum':chosen['snum']});profile=_request(s,lim,'get',url);ident=parse_identity_profile(profile.content,url);verify_identity(ident,expected_name,expected_pref,expected_term,chosen['snum']);elapsed=_elapsed_guard(started)
    return {'status':'PASS_VERIFIED_IDENTITY_LOCATOR_ONLY','snum':chosen['snum'],'rider_key':rider_key(expected_name,expected_pref,expected_term),'query_basis':['prefecture','term','active_only'],'search_result_identity_fields_used':['name','snum'],'final_identity_checks':['registration_number','normalized_name','prefecture','term'],'search_result_count':len(candidates),'name_match_count':1,'search_landing_sha256':hashlib.sha256(landing.content).hexdigest(),'search_result_sha256':hashlib.sha256(result.content).hexdigest(),'profile_raw_sha256':hashlib.sha256(profile.content).hexdigest(),'search_path':SEARCH_RESULT_PATH,'search_payload_sha256':hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'locator_elapsed_seconds':round(elapsed,3),'predictive_features_emitted':False,'raw_html_persisted':False,'capture_timestamp_utc':datetime.now(timezone.utc).isoformat()}
def synthetic_tests():
    landing='''<html><head><meta charset="utf-8"></head><body><form name="PJ0501_02InputForm" id="PJ0501_02InputForm"><table><tr><td>府県</td><td><select name="UNQ_select_21"><option value="">指定しない</option><option value="63">岡山県</option></select></td></tr><tr><td>卒業期</td><td><input type="tel" name="UNQ_orexpandText_22"></td></tr><tr><td><input type="checkbox" name="UNQ_checkbox_34"></td><td>現役選手のみ</td></tr></table><button type="button" name="btnSearchSensyu" onclick="sensyuSearchExec()">検索</button></form><form name="PJ0501_02SubmitForm" id="PJ0501_02SubmitForm" action="/pc/racersearchresult" method="get">'''
    landing+=''.join(f'<input type="hidden" name="{k}" value="{FIXED_QUERY_VALUES.get(k,"")}">' for k in SEARCH_RESULT_QUERY_KEYS)
    landing+='''</form><script>function sensyuSearchExec() { document.PJ0501_02SubmitForm.hukenCD.value = document.getElementById("UNQ_select_21").value; document.PJ0501_02SubmitForm.sotugyouki.value = document.getElementById("UNQ_orexpandText_22").value; var check = document.getElementById("UNQ_checkbox_34").checked; document.PJ0501_02SubmitForm.stgt.value = "1"; document.PJ0501_02SubmitForm.stgt.value = "2"; }</script></body></html>'''
    action,payload=_verify_search_landing(landing.encode('utf-8'),'岡山',127);assert action=='https://keirin.jp/pc/racersearchresult' and payload['hukenCD']=='63' and payload['sotugyouki']=='127' and payload['stgt']=='1'
    result='''<html><head><meta charset="utf-8"></head><body><div>ページ:1/1</div><a href="javascript:void(0)" onclick="sensyuLink('015915')">柏野 健吾</a><a href="javascript:void(0)" onclick="sensyuLink('015918')">土井 慎二</a><form name="PJ0504SensyuLinkForm" id="PJ0504SensyuLinkForm" action="/pc/racerprofile" method="get"><input type="hidden" name="snum" /></form></body></html>'''.encode('utf-8')
    recs=extract_identity_candidates(result);assert recs==[{'snum':'015915','name':'柏野健吾'},{'snum':'015918','name':'土井慎二'}]
    bad=result.replace(b'1/1',b'1/2')
    try:extract_identity_candidates(bad);raise AssertionError('pagination not rejected')
    except FailClosed:pass
    return {'status':'PASS','network_used':False,'fixture_encoding':'UTF-8_DECLARED'}
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--synthetic',action='store_true');ap.add_argument('--smoke',nargs=3,metavar=('NAME','PREF','TERM'));args=ap.parse_args()
    if args.synthetic:print(json.dumps(synthetic_tests(),ensure_ascii=False,indent=2))
    elif args.smoke:
        name,pref,term=args.smoke;print(json.dumps(resolve_snum(name,pref,int(term)),ensure_ascii=False,indent=2))
    else:raise SystemExit('usage: --synthetic | --smoke <name> <pref> <term>')
