# MULTIVERSE Remote PostgreSQL Adapter PRE_PRODUCTION Execution Preparation v1

Issue #142 prepares a bounded remote validation workload for the exact Owner-adopted
repository PostgreSQL adapter from PR #140.

This directory is preparation only. It does not authorize or perform a remote connection,
provider mutation, deploy, or schema mutation.

## Planned bounded execution

After a separate exact Owner execution-authority gate, the workload may be deployed as one
dedicated free PRE_PRODUCTION Render web service in Singapore against the existing free
PostgreSQL instance `dpg-dadou0on74is73b09570-a`.

The service validates all non-secret authority gates before reading the database connection
secret or importing psycopg. The connection secret remains a runtime-only provider secret
and is never printed or included in evidence.

The bounded drill uses only synthetic no-effect state:

- initialize the reviewed `mv_runtime_*_v1` schema;
- worker A lease/fence;
- inert checkpoint write/read;
- inert idempotency operation;
- duplicate suppression;
- payload-conflict rejection;
- lease expiry;
- worker B ownership transfer with increased fence;
- stale worker A rejection;
- resume checkpoint visibility;
- cross-owner duplicate suppression;
- readiness remains false.

HTTP is read-only for `/health`, `/ready`, and `/evidence`; state-changing methods are
denied.

## Preparation ceiling

`REMOTE_POSTGRES_ADAPTER_PREPRODUCTION_EXECUTION_PREPARATION_ONLY`

Execution state:

`REMOTE_EXECUTION_NOT_AUTHORIZED`

- remote_postgres_execution: false
- activation_ready: false
- Runtime: OFF

A later separate Owner authority gate is mandatory before service creation, environment
binding, deploy, remote PostgreSQL connection, or schema mutation.

No protected Keirin data, production credentials, live business effect, additional paid
spend, provider-effect enablement, activation-bridge enablement, merge, main mutation, or
Runtime activation is authorized.
