#!/usr/bin/env python3
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location("m","tools/keirin_nextgen5000_candidate_ab_preoutcome_materializer_v1.py")
m=module_from_spec(spec); spec.loader.exec_module(m)

raw=[
(1,'山口 龍也','A1','追',88.20,2,0,15.0,15.0,20.0),
(2,'成清 謙二郎','A2','追',83.88,0,0,0.0,15.7,21.0),
(3,'細川 貴史','A2','追',85.12,5,0,4.1,16.6,41.6),
(4,'田代 匠','A2','逃',86.29,4,16,25.0,41.6,54.1),
(5,'谷元 奎心','A1','逃',86.04,0,1,19.0,23.8,38.0),
(6,'山崎 岳志','A2','追',82.96,2,0,7.4,22.2,33.3),
(7,'金野 俊秋','A2','両',86.85,9,5,11.1,29.6,51.8),
]
rows=[]
for car,name,cls,style,score,S,B,w,q,t in raw:
    rows.append({
      'race_id':'8320260327010001','race_date':'2026-03-27','venue':'久留米','race_no':'1',
      'car_no':str(car),'rider_name_raw':name,'class':cls,'style':style,'gear_ratio':'3.92',
      'competition_score':str(score),'S':str(S),'B':str(B),'nige':'0','makuri':'0','sashi':'0','mark':'0',
      'win_rate':str(w),'quinella_rate':str(q),'trio_rate':str(t),
      'source_url':'https://keirin.kdreams.jp/kurume/racedetail/8320260327010001/',
      'source_file_sha256':'a'*64,'evidence_role':'RETROSPECTIVE_PRE_DEVELOPMENT_ONLY_UNPROVEN_PIT_V2'
    })
x=m.materialize_race(rows)
r={q['car_no']:q for q in x['riders']}
expected_a={
1:0.20794503391268912,2:0.04438214123021343,3:0.08150203809149957,
4:0.2708663650191277,5:0.14592103348862553,6:0.04622110615656725,7:0.2031622821012774}
expected_b={
1:0.1591385962411628,2:0.027332832636471464,3:0.05019319719459076,
4:0.3183964796161109,5:0.21314819203343413,6:0.028465362955268983,7:0.20332533932296082}
for car in expected_a:
    assert abs(r[car]['candidate_a_win_probability']-expected_a[car])<1e-12
    assert abs(r[car]['b1a_win_probability']-expected_b[car])<1e-12
assert x['candidate_a_top1_car']==4 and x['b1a_top1_car']==4 and x['top1_agree']
assert x['conservative_rank']==[4,7,1,5,3,6,2]
assert x['conservative_top3_cars']==[4,7,1]
assert x['ticket_3renhuku']=='1=4=7'
assert abs(x['candidate_a_ticket_probability']-0.16389363361581)<1e-12
assert abs(x['b1a_ticket_probability']-0.15052271713734244)<1e-12
assert abs(x['top_score_gap']-1.35)<1e-12
assert x['selected_by_frozen_rule'] is False
print('PASS')
