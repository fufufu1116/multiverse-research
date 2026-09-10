"""Static PostgreSQL contract for a future distributed Runtime control-store adapter.

No database client is imported and no connection is attempted.  The SQL is reviewable
architecture evidence only.  A later exact-lineage Candidate must implement and remotely
validate an adapter before activation can be considered.
"""

POSTGRES_CONTRACT_SCHEMA = "MULTIVERSE_POSTGRES_RUNTIME_CONTROL_CONTRACT_v1"
DATABASE_TIME_AUTHORITY = "clock_timestamp()"
TRANSACTION_ISOLATION_REQUIREMENT = "ROW_LOCKED_SERIALIZED_CONTROL_MUTATIONS"
NO_CONNECTION_IN_THIS_CANDIDATE = True

SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS mv_runtime_control_v1 (
    runtime_id text PRIMARY KEY,
    owner_worker_id text,
    owner_instance_id text,
    fence_token bigint NOT NULL DEFAULT 0,
    lease_expires_at timestamptz,
    kill_switch_engaged boolean NOT NULL DEFAULT true,
    activation_bridge_enabled boolean NOT NULL DEFAULT false,
    provider_effect_adapter_enabled boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS mv_runtime_checkpoints_v1 (
    runtime_id text NOT NULL,
    checkpoint_key text NOT NULL,
    value_json jsonb NOT NULL,
    worker_id text NOT NULL,
    instance_id text NOT NULL,
    fence_token bigint NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (runtime_id, checkpoint_key)
);
CREATE TABLE IF NOT EXISTS mv_runtime_operations_v1 (
    runtime_id text NOT NULL,
    request_key text NOT NULL,
    payload_sha256 text NOT NULL,
    applied_by text NOT NULL,
    fence_token bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (runtime_id, request_key)
);
""".strip()

LEASE_READ_FOR_UPDATE_SQL = r"""
SELECT owner_worker_id, owner_instance_id, fence_token, lease_expires_at,
       kill_switch_engaged, activation_bridge_enabled, provider_effect_adapter_enabled,
       clock_timestamp()
FROM mv_runtime_control_v1
WHERE runtime_id = %s
FOR UPDATE
""".strip()

CHECKPOINT_PRECONDITION = (
    "same owner worker + same owner instance + exact current fence + unexpired lease; "
    "otherwise fail closed before write"
)

IDEMPOTENCY_PRECONDITION = (
    "same current owner/fence/unexpired lease; request_key is unique per runtime; "
    "same digest returns duplicate without effect; different digest is conflict"
)
