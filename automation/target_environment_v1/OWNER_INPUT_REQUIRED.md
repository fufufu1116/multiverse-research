# Owner Input Required — Target Binding

The generic target-environment evidence harness has passed construction CI. Further **bound Candidate** work requires infrastructure facts that must not be invented.

Required owner/target-authority input:

- target platform/provider name;
- target environment class: `PRE_PRODUCTION` or `PRODUCTION_SHADOW_NO_EFFECT`;
- target identifier/name;
- host model: `SINGLE_HOST` or `MULTI_HOST_EXPECTED`;
- approved credential path for no-effect drills: for example provider-native secret injection or equivalent ephemeral mechanism.

No production secret value should be pasted into Chat or committed to GitHub.

Until these facts are supplied, Runtime remains OFF and Candidate creation stays blocked by design.
