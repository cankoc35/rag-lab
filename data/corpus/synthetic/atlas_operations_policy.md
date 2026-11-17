# Atlas operations policy

- Source ID: LOCAL-POLICY
- Document version: 1.0
- Document state: atlas-docs-v1
- Reference date: 2026-11-17
- Data classification: Synthetic; all local rules and deployment details are invented.

## Scope and authority

This policy defines a local replica-lag rule and inspection practices for the
fictional Atlas PostgreSQL environment. It applies only to the reporting
replica identified by the Atlas environment inventory, **LOCAL-INVENTORY**,
with document state `atlas-docs-v1`. Both documents describe the same reference
state. The inventory supplies resource identities; this document supplies the
operational rule used for those resources.

The threshold is an Atlas policy choice, not a PostgreSQL default or a limit
imposed by the database engine. It does not apply automatically to another
environment or to an unidentified replica. This policy contains no current
replica observation and does not certify that a running deployment exists.

## Reporting replica lag criterion

The policy identifier is `ATLAS-REPORTING-LAG`. Its maximum permitted numeric
replay lag is **5 seconds**, inclusive. A valid observation must identify the
Atlas reporting replica, belong to the selected observation state and report
its replay lag in seconds. A usable numeric value is finite and nonnegative.
Values with unknown units or an unmatched resource identity cannot be compared
with this threshold.

| Available observation | Lag-criterion outcome |
| --- | --- |
| Valid numeric lag from 0 through 5 seconds, inclusive | Satisfied |
| Valid numeric lag greater than 5 seconds | Exceeded |
| NULL, absent, invalid or mismatched observation | Unknown |

Exactly 5 seconds satisfies the criterion. The rule evaluates only the
specified replica's reported lag. It does not establish overall system health,
application correctness, durability guarantees or whether promoting a standby
would be safe. Those decisions require additional evidence and procedures
outside this policy.

## Missing or unusable observations

A NULL replay-lag value must not be converted to zero for this decision. A
missing record must not be replaced with a value from another replica or an
earlier observation state. Negative values, nonnumeric text and values without
an established unit are unusable. In these cases, record the lag-criterion
outcome as unknown and identify the information that is missing.

An unavailable lag measurement does not, by itself, establish a replication
failure or its cause. PostgreSQL field semantics should be interpreted using
the relevant PostgreSQL documentation. A dashboard can display missing data
according to its presentation conventions, but that display cannot supply the
numeric observation required by this rule. No dashboard convention changes the
threshold or turns an unknown outcome into a satisfied one.

## Inspection and escalation

For a lag assessment, obtain the resource identity from the inventory, the
threshold from this policy and the matching observation from the selected
state. Record the observation's identity, its reported units and the policy
version alongside the conclusion. If a valid value exceeds the threshold,
request further investigation; the threshold crossing alone does not identify
a root cause.

For query inspection, use the catalog identifier from the inventory and a
matching record of the query's parameters, existing indexes and selected plan.
This policy authorizes no index creation, deletion, configuration change or
replica promotion. Plain plan inspection is distinct from executing a query
to collect runtime measurements. Estimates or a single plan cannot establish
an exact before-and-after performance gain without corresponding measurements.

## Evidence boundaries and revisions

Use only observations belonging to the state being assessed. A conclusion
about a documented inventory snapshot is not automatically a statement about
the current deployment. When the policy or inventory changes, identify the
replacement document version explicitly rather than combining facts from
different versions. The shared document state ties these two source documents
together; observation records still need their own identities.

If a requested fact is absent, state that the available evidence does not
provide it. Do not invent missing resource names, lag measurements, plan
results, failure diagnoses or limits for another environment. This policy and
its companion inventory contain no approved thresholds for other environments,
no live monitoring history and no measured index-performance comparison.
