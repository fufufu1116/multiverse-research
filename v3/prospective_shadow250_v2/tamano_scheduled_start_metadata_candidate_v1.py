#!/usr/bin/env python3
"""Candidate-only scheduled-start metadata extractor for Shadow250-v2.
NOT ACTIVE. MUST NOT be used for screening until independent governance adjudication.
Reads only the already-frozen Tamano PDF PRE clips and emits non-predictive selection-order metadata.
"""
from __future__ import annotations
import fitz,re,hashlib,importlib.util
from datetime import datetime,timezone,timedelta
from pathlib import Path

HERE=Path(__file__).resolve().parent
FROZEN_PARSER=HERE/'tamano_racecard_row_parser_v4.py'
EXPECTED_FROZEN_PARSER_GIT_BLOB='397ed3c8839b1ad4ffa4835924dd759397e2124c'
JST=timezone(timedelta(hours=9))
class FailClosed(RuntimeError):pass

def _git_blob(path:Path)->str:
    raw=path.read_bytes();return hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()

def _load_parser():
    if _git_blob(FROZEN_PARSER)!=EXPECTED_FROZEN_PARSER_GIT_BLOB:
        raise FailClosed('FAIL_CLOSED frozen parser blob mismatch')
    spec=importlib.util.spec_from_file_location('frozen_tamano_parser_v4',FROZEN_PARSER)
    if spec is None or spec.loader is None:raise FailClosed('FAIL_CLOSED parser import')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def extract_scheduled_starts(path,race_date,source_url,expected_raw_sha256):
    p=_load_parser()
    bound_date,raw_sha,basename=p._validate_transport_binding(path,race_date,source_url,expected_raw_sha256)
    doc=fitz.open(path);p._validate_template_and_pre_clips(doc)
    rows=[]
    for pi,ox,rno,ymin,ymax in p.RACE_SPECS:
        words=doc[pi].get_text('words',clip=p.PRE_CLIPS[pi])
        band=[w for w in words if ox<=w[0]<=ox+590 and ymax-8<=w[1]<=ymax+35]
        text=''.join(w[4] for w in sorted(band,key=lambda z:(z[1],z[0])))
        hits=re.findall(r'発走\s*([0-2]?\d):([0-5]\d)',text)
        if len(hits)!=1:raise FailClosed(f'PRE_INELIGIBLE_SOURCE_GAP scheduled_start race={rno} hits={hits}')
        hh,mm=map(int,hits[0])
        if hh>23:raise FailClosed(f'PRE_INELIGIBLE_SOURCE_GAP scheduled_start hour={hh}')
        dt=datetime.fromisoformat(bound_date).replace(hour=hh,minute=mm,second=0,microsecond=0,tzinfo=JST)
        rows.append({'race_id':f"{bound_date.replace('-','')}_61_tamano_{rno:02d}R",'race_no':rno,'scheduled_start_jst':dt.isoformat(),'metadata_role':'NON_PREDICTIVE_SELECTION_ORDER_ONLY','source_pdf_raw_sha256':raw_sha,'source_pdf_basename':basename})
    if len(rows)!=12 or [x['race_no'] for x in rows]!=list(range(1,13)):
        raise FailClosed('PRE_INELIGIBLE_SOURCE_GAP scheduled_start coverage')
    stamps=[datetime.fromisoformat(x['scheduled_start_jst']) for x in rows]
    if any(b<=a for a,b in zip(stamps,stamps[1:])):
        raise FailClosed('PRE_INELIGIBLE_SOURCE_GAP scheduled_start nonmonotonic')
    return rows

def synthetic_tests():
    samples=['締切10:50（７車立）発走10:53','締切15:38（７車立）発走15:41']
    got=[]
    for s in samples:
        h=re.findall(r'発走\s*([0-2]?\d):([0-5]\d)',s);assert len(h)==1;got.append('%02d:%s'%(int(h[0][0]),h[0][1]))
    assert got==['10:53','15:41']
    assert _git_blob(FROZEN_PARSER)==EXPECTED_FROZEN_PARSER_GIT_BLOB
    return {'status':'PASS','network_used':False,'frozen_parser_git_blob':EXPECTED_FROZEN_PARSER_GIT_BLOB,'predictive_fields_emitted':False}

if __name__=='__main__':
    import json,sys
    if len(sys.argv)==2 and sys.argv[1]=='--synthetic':print(json.dumps(synthetic_tests(),ensure_ascii=False,indent=2))
    else:raise SystemExit('Candidate-only: --synthetic only; prospective use is NOT AUTHORIZED')
