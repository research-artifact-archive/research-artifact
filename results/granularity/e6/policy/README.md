# Policy(2): requirement-boundary interleaving

Preregistered in DAILY before execution. Operational motivation combines uninterrupted audit coverage with mutually exclusive access roles. This is a constructed transition contract, not a reproduction of CloudTrail or an enterprise migration.

Sources verified 2026-09-29:
- AWS CloudTrail `stop-logging`: https://docs.aws.amazon.com/cli/latest/reference/cloudtrail/stop-logging.html
- NIST, Mutual Exclusion of Roles as a Means of Implementing Separation of Duty in Role-Based Access Control Systems (1997): https://csrc.nist.gov/pubs/conference/1997/11/07/mutual-exclusion-of-roles-to-implement-separation/final

Fine boundaries allow start(new audit), stop(old audit), stop(old role), start(new role). Merged stops cause an audit gap; merged starts cause an exclusive-role overlap. Safety monitors, not cyclic precedence, encode this distinction. The single component's identity transfer isolates boundary granularity.

## Measured result

All six planned cells completed and matched expectations. Fine Lazy: WIN, 24 discovered states, certificate rank 6. Fine Direct-Full: WIN, 129 states, rank 5. Transfers: WIN, 24 states. Boundaries/both/generated global boundaries: LOSS, 16 discovered/certificate states. The generated and automatically merged games agree on all 98 reachable states and 637 enabled buckets, and on the measured Lazy state counts. Endpoint, certificate, Link (WIN), and mechanism audits passed.

The audit covers the actual certificate states and initial-root boundary buckets. Global start causes exclusive-role overlap; global stop causes an audit gap. Boundary and both are one witness, not independent examples. The rank is a returned certificate bound, not an optimality claim.

See `summary.csv`, `tables/comparison.csv`, `tables/merge_equality.csv`, `tables/policy_comparison.tex`, and `validation/certificate_mechanism_audit.json`. Raw trial directories are create-only under `raw/series/`.

Final current result directory: `v2/`. Earlier inputs and results are retained as a modeling/validation correction history; see DAILY and v2 validation files.
