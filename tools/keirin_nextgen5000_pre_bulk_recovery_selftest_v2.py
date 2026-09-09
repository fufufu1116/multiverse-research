#!/usr/bin/env python3
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
import tempfile

spec=spec_from_file_location("p","tools/keirin_nextgen5000_pre_bulk_recovery_v2.py")
m=module_from_spec(spec); spec.loader.exec_module(m)

html="""<!doctype html><html><head><title>久留米競輪 2026年03月27日 1R 詳細</title></head><body>
<table>
<tr><th>枠番</th><th>車番</th><th>選手名 府県/年齢/期別</th><th>級班</th><th>脚質</th><th>ギヤ倍数</th><th colspan="14">直近4ヶ月の成績 競走得点 S B 逃 捲 差 マ 1着 2着 3着 着外 勝率 2連対率 3連対率</th></tr>
<tr><td>1</td><td>1</td><td>山口 龍也 長崎/31/111</td><td>A1</td><td>追</td><td>3.92</td><td>88.20</td><td>2</td><td>0</td><td>0</td><td>1</td><td>2</td><td>0</td><td>3</td><td>0</td><td>1</td><td>16</td><td>15.0</td><td>15.0</td><td>20.0</td></tr>
<tr><td>2</td><td>2</td><td>成清 謙二郎 千葉/42/90</td><td>A2</td><td>追</td><td>3.92</td><td>83.88</td><td>0</td><td>0</td><td>0</td><td>0</td><td>1</td><td>2</td><td>0</td><td>3</td><td>1</td><td>15</td><td>0.0</td><td>15.7</td><td>21.0</td></tr>
<tr><td>3</td><td>3</td><td>細川 貴史 広島/45/87</td><td>A2</td><td>追</td><td>3.92</td><td>85.12</td><td>5</td><td>0</td><td>0</td><td>0</td><td>1</td><td>3</td><td>1</td><td>3</td><td>6</td><td>14</td><td>4.1</td><td>16.6</td><td>41.6</td></tr>
<tr><td>4</td><td>4</td><td>田代 匠 福岡/25/121</td><td>A2</td><td>逃</td><td>3.92</td><td>86.29</td><td>4</td><td>16</td><td>6</td><td>3</td><td>1</td><td>0</td><td>6</td><td>4</td><td>3</td><td>11</td><td>25.0</td><td>41.6</td><td>54.1</td></tr>
<tr><td>5</td><td>5</td><td>谷元 奎心 山口/25/117</td><td>A1</td><td>逃</td><td>3.92</td><td>86.04</td><td>0</td><td>1</td><td>0</td><td>4</td><td>1</td><td>0</td><td>4</td><td>1</td><td>3</td><td>13</td><td>19.0</td><td>23.8</td><td>38.0</td></tr>
</table></body></html>"""
rows=m.parse_pre(html.encode(),"https://keirin.kdreams.jp/kurume/racedetail/8320260327010001/")
assert len(rows)==5
r=rows[0]
assert r["gear_ratio"]==3.92
assert r["competition_score"]==88.20
assert (r["S"],r["B"],r["nige"],r["makuri"],r["sashi"],r["mark"])==(2,0,0,1,2,0)
assert (r["win_rate"],r["quinella_rate"],r["trio_rate"])==(15.0,15.0,20.0)
assert r["competition_score"]!=r["gear_ratio"]
assert m.FIELDS[8:19]==['gear_ratio','competition_score','S','B','nige','makuri','sashi','mark','win_rate','quinella_rate','trio_rate']
print("PASS")
