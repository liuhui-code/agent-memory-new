# Actual evidence order

Initial protocol.json and supported-protocol.json were each written before their
respective CLI diagnostic observations, but neither was committed at that moment.
They must NOT be described as Git-frozen before those diagnostic runs.

The first source included an unsupported regex that reduced its class semantic
range to1..1 and left methods without semantic identities. before/preflight retain
that outcome; no marker expectation can be validated on those missing method rows.

The supplemental supported-source protocol removes that regex method and keeps
the other source/query expectations. supported-before.json is a diagnostic public
observation: actual method identities/ranges exist, and text-only methods contain
synthesized guardreturn/statewrite markers. No production change was made.

This commit freezes both protocols, source/query hash manifest, diagnostic history
and the public acceptance test BEFORE the subsequent formal red run. The formal
run reuses exactly the supported protocol; it is not retroactive evidence that
the earlier diagnostic was Git-frozen. The original unknown-regex defect is not
fixed or counted as a successful unknown control.
