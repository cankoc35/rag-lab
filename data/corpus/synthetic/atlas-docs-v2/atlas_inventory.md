# Atlas environment inventory

- Source ID: LOCAL-INVENTORY
- Document version: 2.0
- Document state: atlas-docs-v2
- Reference date: 2026-11-23
- Data classification: Synthetic; all names, quantities and deployment details are invented.

## Scope and purpose

Atlas is a fictional PostgreSQL 18 environment supporting a device telemetry
application. It stores incoming device events alongside the customers, devices
and orders used by that application. This inventory describes one fixed
reference state. It is not a connection to a running Atlas cluster, a production
asset register or a report of measurements collected from a database.

The inventory identifies application objects and their intended relationships.
It is deliberately selective: a table that is not listed individually can still
be included in the stated application table count. Names in this document refer
only to Atlas. They do not identify resources in any other environment.

## Database and application identity

The database is named `atlas_telemetry`, and its application schema is
`atlas_app`. The application table count is **120**, excluding PostgreSQL
system catalogs and views. Unqualified application table names in Atlas
operations notes refer to `atlas_app`; fully qualified names should be used
when recording an inspection result.

The primary server is identified as `atlas-primary-01`. The application writes
to the primary. Its named standby, `atlas-replica-01`, serves reporting reads.
These identifiers are logical names, not hostnames or connection strings. This
inventory provides no credentials or network addresses.

## Storage inventory and important tables

The synthetic database size is **10.0 GB**. Here, one GB means 1,000,000,000
bytes. The listed table footprints include each table's associated indexes and
auxiliary storage. They are invented reference allocations, not outputs from
PostgreSQL size functions. WAL files and external backups are outside this
database-size figure.

| Application table | Purpose | Total footprint |
| --- | --- | ---: |
| `atlas_app.device_events` | Timestamped events emitted by registered devices | 6.2 GB |
| `atlas_app.orders` | Customer orders and billing status | 1.1 GB |
| `atlas_app.devices` | Device registration and ownership | 0.4 GB |
| `atlas_app.customers` | Customer identities used by the application | 0.3 GB |
| `atlas_app.ingest_batches` | Metadata linking events to ingestion batches | 0.2 GB |

The five named tables account for 8.2 GB. The remaining 1.8 GB covers the other
115 application tables and database overhead. The largest table by total
footprint is `atlas_app.device_events`. No unlisted table is larger in this
reference state. Row counts, individual index sizes and physical layouts are
not specified; a storage total does not supply those details.

## Replica identity and policy relationship

`atlas-replica-01` follows `atlas-primary-01` and has the operational role
`reporting`. Its applicable local lag rule is defined in **LOCAL-POLICY**,
the Atlas operations policy with document state `atlas-docs-v2`. Use that
policy for the threshold, units and interpretation of missing observations.
The inventory itself records the replica's identity and role, not its current
lag or whether it satisfies the rule.

No observation timestamp, replication status or live replay-lag value is
included here. Replica lag must come from an observation associated with the
selected state. An inventory entry alone is insufficient to establish current
health, failover readiness or the cause of a replication problem.

## Customer lookup query catalog

The customer lookup query is identified as `Q-ATLAS-CUSTOMER-LOOKUP`:

```sql
SELECT order_id, customer_id, created_at, billed
FROM atlas_app.orders
WHERE customer_id = $1
  AND created_at >= $2;
```

The first parameter supplies a customer identifier; the second supplies an
inclusive creation-time lower bound. `billed` is a Boolean billing-status
field. The catalog fixes the query text for future inspection, but supplies no
parameter values, index definitions, execution plan or measured duration.
Those details must come from a matching database inspection or separately
identified observation. The existence of this query does not establish which
scan type a planner will select or how much a proposed index would improve it.
