from reality_ontrack_tactical_annotation_v0 import (
    AnnotationRecord,
    OpportunityRecord,
    TacticalAnnotationError,
    agreement_report,
    estimate_pilot_rate,
    truth_rate_admitted,
)


def expect_error(fn):
    try:
        fn()
    except TacticalAnnotationError:
        return
    raise AssertionError("expected TacticalAnnotationError")


def main():
    valid = AnnotationRecord(
        annotation_id="a1",
        race_id="r1",
        annotator_id="ann1",
        source_url="https://example.invalid/replay.mp4",
        event_type="LINE_FRAGMENT",
        phase="FINAL_LAP_HOME_TO_BACK",
        event_time_seconds=92.5,
        actor_car=3,
        counterparty_car=None,
        before_line_state="3-7-1 | 5-2 | 4-6",
        after_line_state="3-7 | 1 | 5-2 | 4-6",
        visibility="CLEAR",
        label="PRESENT",
        provenance_sha256="0" * 64,
        candidate_outputs_hidden=True,
        finish_order_recorded=False,
        payout_recorded=False,
    )
    assert valid.label == "PRESENT"

    unknown = AnnotationRecord(
        annotation_id="a2",
        race_id="r1",
        annotator_id="ann1",
        source_url="https://example.invalid/replay.mp4",
        event_type="SWITCH",
        phase="FINAL_LAP_HOME_TO_BACK",
        event_time_seconds=None,
        actor_car=None,
        counterparty_car=None,
        before_line_state="UNKNOWN",
        after_line_state="UNKNOWN",
        visibility="UNOBSERVABLE",
        label="UNKNOWN",
        provenance_sha256="1" * 64,
        candidate_outputs_hidden=True,
        finish_order_recorded=False,
        payout_recorded=False,
    )
    assert unknown.label == "UNKNOWN"

    expect_error(lambda: AnnotationRecord(
        annotation_id="bad",
        race_id="r1",
        annotator_id="ann1",
        source_url="https://example.invalid/replay.mp4",
        event_type="SWITCH",
        phase="FINAL_LAP_HOME_TO_BACK",
        event_time_seconds=10,
        actor_car=2,
        counterparty_car=None,
        before_line_state="2-4",
        after_line_state="2 | 4",
        visibility="UNOBSERVABLE",
        label="ABSENT",
        provenance_sha256="2" * 64,
        candidate_outputs_hidden=True,
        finish_order_recorded=False,
        payout_recorded=False,
    ))

    expect_error(lambda: AnnotationRecord(
        annotation_id="bad2",
        race_id="r1",
        annotator_id="ann1",
        source_url="https://example.invalid/replay.mp4",
        event_type="SWITCH",
        phase="FINAL_LAP_HOME_TO_BACK",
        event_time_seconds=10,
        actor_car=2,
        counterparty_car=None,
        before_line_state="2-4",
        after_line_state="2 | 4",
        visibility="CLEAR",
        label="PRESENT",
        provenance_sha256="3" * 64,
        candidate_outputs_hidden=True,
        finish_order_recorded=True,
        payout_recorded=False,
    ))

    rows = [
        OpportunityRecord("o1", "r1", "LINE_FRAGMENT", "FINAL_LAP_HOME_TO_BACK", 1, None, True, True, "PRESENT"),
        OpportunityRecord("o2", "r1", "LINE_FRAGMENT", "FINAL_LAP_HOME_TO_BACK", 2, None, True, True, "ABSENT"),
        OpportunityRecord("o3", "r2", "LINE_FRAGMENT", "FINAL_LAP_HOME_TO_BACK", 3, None, True, True, "PRESENT"),
        OpportunityRecord("o4", "r2", "LINE_FRAGMENT", "FINAL_LAP_HOME_TO_BACK", 4, None, True, True, "ABSENT"),
        OpportunityRecord("o5", "r3", "LINE_FRAGMENT", "FINAL_LAP_HOME_TO_BACK", 5, None, True, True, "ABSENT"),
        OpportunityRecord("o6", "r3", "LINE_FRAGMENT", "FINAL_LAP_HOME_TO_BACK", 6, None, True, False, "UNKNOWN"),
    ]
    rate = estimate_pilot_rate("LINE_FRAGMENT", rows)
    assert rate.positives == 2 and rate.denominator == 5
    assert abs(rate.point - 0.4) < 1e-12
    assert 0.0 <= rate.wilson95_low < rate.point < rate.wilson95_high <= 1.0
    assert rate.status == "PILOT_DIAGNOSTIC_ONLY_NOT_TRUTH_ADMITTED"

    agreement = agreement_report(
        {"o1": "PRESENT", "o2": "ABSENT", "o3": "UNKNOWN"},
        {"o1": "PRESENT", "o2": "PRESENT", "o3": "ABSENT"},
    )
    assert agreement.comparable == 2
    assert agreement.agreements == 1
    assert agreement.raw_agreement == 0.5
    assert truth_rate_admitted() is False
    print("PASS_ONTRACK_TACTICAL_ANNOTATION_FOUNDATION")


if __name__ == "__main__":
    main()
