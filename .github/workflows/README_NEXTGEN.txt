NEXTGEN Multiverse v1 implementation starter

Purpose:
- freeze Data Constitution and Feature Registry
- build chronological universes
- stage PRE-only raw data with provenance and SHA
- FAIL-CLOSED on POST endpoints
- deliberately refuse TRAIN eligibility until historical available_at is proven

Important:
PRE_STAGING is NOT training data yet.
Historical retrieval time does not prove that a feature existed before the original race.
The collector marks eligible_for_model_training=false until an independent availability-proof layer is implemented.
