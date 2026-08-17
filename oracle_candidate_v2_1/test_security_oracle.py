import json
import os
import multiprocessing as mp
import subprocess
from pathlib import Path
import pytest


def api():
    from candidate.security_v3_3 import api as m
    return m


def test_wrong_key_decrypt_no_burn(tmp_path):
    m = api()
    p = tmp_path / "vault.json"
    good = b"g" * 32
    bad = b"b" * 32
    v1 = m.SyntheticHoldoutVault(p, good)
    v1.seal(b"synthetic-payload")
    before = v1.state()
    with pytest.raises(Exception):
        v1.open(bad)
    v2 = m.SyntheticHoldoutVault(p, good)
    after = v2.state()
    assert after["burn_count"] == before["burn_count"]
    assert after["nonce"] == before["nonce"]
    assert v2.open(good) == b"synthetic-payload"


def test_signature_auth_binding():
    m = api()
    secret = b"synthetic-secret"
    msg = b"race:synthetic-001|candidate:A"
    sig = m.Authenticator.sign(secret, msg)
    assert m.Authenticator.verify(secret, msg, sig) is True
    assert m.Authenticator.verify(secret, msg + b"|mutated", sig) is False
    assert m.Authenticator.verify(b"other-secret", msg, sig) is False


def test_file_backed_independent_restart_persistence(tmp_path):
    m = api()
    p = tmp_path / "counter.json"
    a = m.PersistentCounter(p)
    assert a.increment() == 1
    b = m.PersistentCounter(p)
    assert b.value() == 1
    assert b.increment() == 2
    c = m.PersistentCounter(p)
    assert c.value() == 2


def test_ledger_hash_linkage_anchor_immutable(tmp_path):
    m = api()
    p = tmp_path / "ledger.jsonl"
    l1 = m.AppendOnlyLedger(p)
    l1.append("synthetic-a")
    l1.append("synthetic-b")
    anchor = l1.anchor()
    assert l1.verify() is True
    l2 = m.AppendOnlyLedger(p)
    assert l2.anchor() == anchor
    assert l2.verify() is True
    rows = p.read_text(encoding="utf-8").splitlines()
    obj = json.loads(rows[0]); obj["data"] = "tampered"
    rows[0] = json.dumps(obj, sort_keys=True)
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    assert m.AppendOnlyLedger(p).verify() is False


def test_update_delete_denial(tmp_path):
    m = api()
    p = tmp_path / "ledger.jsonl"
    l1 = m.AppendOnlyLedger(p)
    l1.append("immutable")
    anchor = l1.anchor()
    with pytest.raises(PermissionError):
        l1.update(0, "mutated")
    with pytest.raises(PermissionError):
        l1.delete(0)
    l2 = m.AppendOnlyLedger(p)
    assert l2.anchor() == anchor and l2.verify() is True


def test_fold_version_binding(tmp_path):
    m = api()
    p = tmp_path / "folds.json"
    f1 = m.FoldRegistry(p)
    f1.bind("fold-1", "v1", train_end=100, valid_start=111, embargo=10)
    with pytest.raises(Exception):
        f1.bind("fold-1", "v2", train_end=100, valid_start=111, embargo=10)
    with pytest.raises(Exception):
        f1.bind("fold-overlap", "v1", train_end=100, valid_start=105, embargo=10)
    f2 = m.FoldRegistry(p)
    assert f2.get("fold-1")["version"] == "v1"


def test_phase_preregistration_candidate_identity(tmp_path):
    m = api()
    p = tmp_path / "phases.json"
    r1 = m.PhaseRegistry(p)
    r1.preregister("VALID", "candidate-A")
    assert r1.execute("VALID", "candidate-A") is True
    with pytest.raises(Exception):
        r1.execute("VALID", "candidate-B")
    r2 = m.PhaseRegistry(p)
    with pytest.raises(Exception):
        r2.preregister("VALID", "candidate-B")


def test_family_manifest_commit_once(tmp_path):
    m = api()
    p = tmp_path / "family.json"
    token = "synthetic-authority-token"
    fm1 = m.FamilyManifest(p, authority_token=token)
    with pytest.raises(Exception):
        fm1.commit("sha-a", authority_token="wrong")
    assert fm1.commit("sha-a", authority_token=token) == "sha-a"
    assert fm1.commit("sha-a", authority_token=token) == "sha-a"
    with pytest.raises(Exception):
        fm1.commit("sha-b", authority_token=token)
    fm2 = m.FamilyManifest(p, authority_token=token)
    with pytest.raises(Exception):
        fm2.commit("sha-b", authority_token=token)


def test_market_evidence_completeness():
    m = api()
    good = {
        "race_id": "synthetic-race",
        "market": "exacta",
        "asof_ts": "2030-01-01T00:00:00Z",
        "source": "synthetic-source",
        "runner_ids": ["1", "2", "3"],
        "odds": {"1-2": 3.1, "1-3": 4.2},
        "parser_fingerprint": "synthetic-parser-v1"
    }
    assert m.MarketEvidence.validate(good) is True
    for key in list(good):
        bad = dict(good); bad.pop(key)
        with pytest.raises(Exception):
            m.MarketEvidence.validate(bad)
    bad = dict(good); bad["runner_ids"] = ["1", "1", "3"]
    with pytest.raises(Exception):
        m.MarketEvidence.validate(bad)


def test_deadheat_malformed_payout_handling():
    m = api()
    winners = [("1", "2"), ("2", "1")]
    assert m.PayoutEngine.settle_exacta(("1", "2"), winners) is True
    assert m.PayoutEngine.settle_exacta(("2", "1"), winners) is True
    assert m.PayoutEngine.settle_exacta(("1", "3"), winners) is False
    with pytest.raises(Exception):
        m.PayoutEngine.settle_exacta(("1", "1"), winners)
    with pytest.raises(Exception):
        m.PayoutEngine.settle_exacta(("1",), winners)
    with pytest.raises(Exception):
        m.PayoutEngine.settle_exacta(("1", "2"), [("1",)])


def test_source_schema_parser_fingerprint_quarantine(tmp_path):
    m = api()
    p = tmp_path / "source_guard.json"
    g1 = m.SourceGuard(p, expected_schema="schema-v1", expected_parser_fingerprint="parser-v1")
    assert g1.ingest({"synthetic": True}, schema="schema-v1", parser_fingerprint="parser-v1") is True
    with pytest.raises(Exception):
        g1.ingest({"synthetic": True}, schema="schema-v2", parser_fingerprint="parser-v1")
    g2 = m.SourceGuard(p, expected_schema="schema-v1", expected_parser_fingerprint="parser-v1")
    assert g2.is_quarantined() is True


def test_persistent_discrepancy_kill_switch(tmp_path):
    m = api()
    p = tmp_path / "killswitch.json"
    k1 = m.PersistentKillSwitch(p)
    assert k1.is_killed() is False
    k1.trigger("synthetic discrepancy")
    k2 = m.PersistentKillSwitch(p)
    assert k2.is_killed() is True
    with pytest.raises(Exception):
        k2.assert_open()


def test_withdrawal_cancel_refund_provenance(tmp_path):
    m = api()
    p = tmp_path / "provenance.jsonl"
    x1 = m.ProvenanceLedger(p)
    x1.record("w1", "withdrawal", 100, ref="synthetic-order-1")
    x1.record("c1", "cancel", 100, ref="synthetic-order-1")
    x1.record("r1", "refund", 100, ref="c1")
    with pytest.raises(Exception):
        x1.record("r2", "refund", 100, ref="missing-cancel")
    x2 = m.ProvenanceLedger(p)
    events = x2.events()
    assert [e["event_id"] for e in events] == ["w1", "c1", "r1"]
    assert x2.verify() is True


def test_key_provider_failure_no_burn(tmp_path):
    m=api(); p=tmp_path/'vault.json'; good=b'g'*32
    v=m.SyntheticHoldoutVault(p,good); v.seal(b'synthetic-payload'); before=v.state()
    provider=m.KeyProvider(lambda: (_ for _ in ()).throw(RuntimeError('provider fail')))
    with pytest.raises(Exception): v.open_with_provider(provider)
    assert m.SyntheticHoldoutVault(p,good).state()==before
    assert m.SyntheticHoldoutVault(p,good).open_with_provider(m.KeyProvider(lambda: good))==b'synthetic-payload'


def test_authenticated_malformed_request_non_bricking(tmp_path):
    m=api(); secret=b'synthetic-secret'; gate=m.AuthenticatedRequestGate(tmp_path/'auth.json',secret)
    msg=b'race:synthetic-001|candidate:A'; sig=m.Authenticator.sign(secret,msg)
    assert gate.accept(msg,sig) is True
    with pytest.raises(Exception): gate.accept(b'malformed','bad')
    assert gate.accept(msg,sig) is True


def _mv33_open_worker(path, key, audit_path, barrier, queue):
    from candidate.security_v3_3 import api as m
    gate = m.AuditedHoldoutGate(Path(path), key, Path(audit_path))
    try:
        barrier.wait(timeout=10)
        payload = gate.open_once(key)
        queue.put(("ok", payload))
    except Exception as e:
        queue.put(("err", type(e).__name__))


def test_holdout_open_exactly_once_concurrent_restart(tmp_path):
    m = api()
    p = tmp_path / "open.json"
    audit = tmp_path / "audit.jsonl"
    key = b"k" * 32

    initializer = m.AuditedHoldoutGate(p, key, audit)
    initializer.initialize(b"synthetic-payload")

    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(3)
    queue = ctx.Queue()

    procs = [
        ctx.Process(
            target=_mv33_open_worker,
            args=(str(p), key, str(audit), barrier, queue),
        )
        for _ in range(2)
    ]

    for proc in procs:
        proc.start()

    barrier.wait(timeout=10)

    for proc in procs:
        proc.join(15)
        assert not proc.is_alive()
        assert proc.exitcode == 0

    results = [queue.get(timeout=3) for _ in range(2)]
    assert sum(1 for kind, _ in results if kind == "ok") == 1
    assert sum(1 for kind, _ in results if kind == "err") == 1
    assert [payload for kind, payload in results if kind == "ok"] == [b"synthetic-payload"]

    restarted = m.AuditedHoldoutGate(p, key, audit)
    state = restarted.state()
    assert state["open_count"] == 1
    assert state["nonce"] == 2

    rows = [
        json.loads(line)
        for line in audit.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["event"] == "OPEN"

    with pytest.raises(Exception):
        restarted.open_once(key)
def test_ledger_tail_truncation_detected(tmp_path):
    m=api(); p=tmp_path/'ledger.jsonl'; a=tmp_path/'anchor.txt'
    l=m.AppendOnlyLedger(p,anchor_path=a); l.append('a'); l.append('b'); assert l.verify() is True
    rows=p.read_text().splitlines(); p.write_text(rows[0]+'\n')
    assert m.AppendOnlyLedger(p,anchor_path=a).verify() is False


def test_authoritative_holdout_membership_and_overlap(tmp_path):
    m=api(); p=tmp_path/'membership.json'; sec=b'authority'
    r=m.HoldoutMembershipRegistry(p,sec); r.commit(['R100','R101'],sec)
    assert r.members()==['R100','R101']
    with pytest.raises(Exception): r.commit(['R200'],sec)
    with pytest.raises(Exception): r.replace(['R200'])
    with pytest.raises(Exception): r.assert_disjoint(['R099','R100'])
    assert r.assert_disjoint(['R001']) is True
    with pytest.raises(Exception): m.HoldoutMembershipRegistry(tmp_path/'x.json',None)


def test_fold_strict_chronology_min_sizes(tmp_path):
    m=api(); p=tmp_path/'folds2.json'; f=m.FoldRegistry(p,min_train=100,min_valid=20)
    f.bind('f1','v1',train_start=0,train_end=99,valid_start=110,valid_end=129,embargo=10)
    with pytest.raises(Exception): f.bind('small','v1',train_start=0,train_end=50,valid_start=61,valid_end=80,embargo=10)
    with pytest.raises(Exception): f.bind('reverse','v1',train_start=50,train_end=10,valid_start=21,valid_end=40,embargo=10)
    with pytest.raises(Exception): f.bind('overlap','v1',train_start=0,train_end=99,valid_start=105,valid_end=124,embargo=10)


def test_governance_relabel_protection_restart(tmp_path):
    m=api(); p=tmp_path/'phase2.json'; r=m.PhaseRegistry(p); r.preregister('VALID','candidate-A')
    with pytest.raises(Exception): r.relabel('VALID','candidate-B')
    assert m.PhaseRegistry(p).execute('VALID','candidate-A') is True


def test_family_floors_and_masking_prevention(tmp_path):
    m=api(); p=tmp_path/'family2.json'; tok='authority'
    f=m.FamilyManifest(p,authority_token=tok,floors={'min_races':500,'min_markets':3}); f.commit('sha-a',authority_token=tok)
    assert f.assert_meets({'races':500,'markets':3}) is True
    with pytest.raises(Exception): f.assert_meets({'races':499,'markets':3})
    with pytest.raises(Exception): f.mask_floor('min_races',100)


def test_payout_quinella_trio_unordered_semantics():
    m=api()
    assert m.PayoutEngine.settle_quinella(('1','2'),[('2','1')]) is True
    assert m.PayoutEngine.settle_trio(('1','2','3'),[('3','1','2')]) is True
    with pytest.raises(Exception): m.PayoutEngine.settle_trio(('1','2','3'),[('1','2')])

def test_runtime_isolation_blocks_oracle_mutation_and_sudo():
    assert os.environ.get("MV33_REQUIRE_ISOLATION") == "1"

    repo = Path(os.environ["MV33_REPO_ROOT"]).resolve()
    protected = repo / "oracle_candidate_v2_1" / "immutable_validator.py"
    assert protected.is_file()

    original = protected.read_bytes()

    with pytest.raises((PermissionError, OSError)):
        protected.write_bytes(original + b"\n# mutation-attempt\n")

    assert protected.read_bytes() == original

    chmod = subprocess.run(
        ["chmod", "u+w", str(protected)],
        text=True,
        capture_output=True,
    )
    assert chmod.returncode != 0

    sudo = subprocess.run(
        ["sudo", "-n", "true"],
        text=True,
        capture_output=True,
    )
    assert sudo.returncode != 0
