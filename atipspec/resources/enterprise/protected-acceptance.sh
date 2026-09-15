#!/bin/sh
# Two separate invocations on protected workers, using an installed/pinned CLI.
# NEVER execute candidate code or install candidate packages on these workers.
# Before "attest", authenticate the producer workflow/repository/head/run and
# artifact provenance. Collect human QA approval AFTER attestation, then "check".
set -eu
: "${ATIPSPEC_TRUST_POLICY:?External administrator-controlled policy is required}"
: "${ATIPSPEC_POLICY_SHA256:?Protected policy pin is required}"
: "${ATIPSPEC_DELIVERY:?Delivery slug is required}"
case "${1:-}" in
  attest)
    : "${ATIPSPEC_CI_KEY:?External enrolled CI collector key is required}"
    : "${ATIPSPEC_CI_IDENTITY:?Enrolled CI signer identity is required}"
    : "${ATIPSPEC_CI_RUN_URL:?Authenticated producer run URL is required}"
    python -I -m atipspec attest "$ATIPSPEC_DELIVERY" \
      --identity "$ATIPSPEC_CI_IDENTITY" --key "$ATIPSPEC_CI_KEY" \
      --run-url "$ATIPSPEC_CI_RUN_URL"
    python -I -m atipspec approval-subject "$ATIPSPEC_DELIVERY" acceptance
    ;;
  check)
    # Restore the SAME signed artifacts; do not re-sign after QA approval.
    # Provider adapters use read-only API credentials here to check revocation.
    python -I -m atipspec check "$ATIPSPEC_DELIVERY" --json
    python -I -m atipspec report "$ATIPSPEC_DELIVERY" --format json \
      --out .atipspec/tmp/acceptance.json
    python -I -m atipspec report "$ATIPSPEC_DELIVERY" --format html \
      --out .atipspec/tmp/acceptance.html
    ;;
  *)
    echo "Usage: sh protected-acceptance.sh attest|check" >&2
    exit 2
    ;;
esac
