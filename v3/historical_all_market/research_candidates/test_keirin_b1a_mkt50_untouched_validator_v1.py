#!/usr/bin/env python3
import json, tempfile, pathlib, subprocess, sys

def run_case(rows):
    td=pathlib.Path(tempfile.mkdtemp()); ip=td/"in.jsonl"; op=td/"out.json"
    ip.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
    p=subprocess.run([sys.executable,"keirin_b1a_mkt50_untouched_validator_v1.py","--input",str(ip),"--output",str(op)],capture_output=True,text=True)
    assert p.returncode==0,(p.stdout,p.stderr)
    return json.loads(op.read_text())

def main():
    rows=[{"race_id":"R1","market":"3rentan","b1a_ticket_probability":{"a":0.8,"b":0.2},"decimal_odds":{"a":10.0,"b":1000.0},"winning_tickets":["a"]},{"race_id":"R2","market":"2shatan","b1a_ticket_probability":{"a":0.8,"b":0.2},"decimal_odds":{"a":10.0,"b":1000.0},"winning_tickets":["a"]}]
    out=run_case(rows)
    assert out["calibration"]["b1a_mkt50_ticket_log_loss"] < out["calibration"]["raw_b1a_ticket_log_loss"]
    assert out["economic_secondary"]["economic_gate"]=="INCONCLUSIVE"
    assert out["promotion_pass"] is False
    print("PASS 1/1")
if __name__=="__main__":main()
