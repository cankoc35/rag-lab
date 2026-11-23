# Atlas query and index catalog

- Source ID: LOCAL-QUERY-CATALOG
- Document version: 1.0
- Document state: atlas-expanded-v1
- Reference date: 2026-11-23
- Data classification: Synthetic; all deployment definitions are authored examples.

## Scope and authority

This catalog defines selected logical tables, three read-only query patterns
and four secondary indexes for the fictional Atlas PostgreSQL 18 environment.
Database and storage identities come from **LOCAL-INVENTORY** in the same
document state. The definitions below are corpus facts, not DDL applied to a
running database. They describe four of the 120 application tables; the other
tables are outside this selected schema fragment.

The schema `atlas_app` is assumed to exist. Primary-key and unique-constraint
backing indexes are separate from the four secondary indexes listed here.
The inventory's aggregate footprints remain unchanged; this catalog provides
no row counts, individual index sizes, cardinalities or measured plans.

## Selected table definitions

Customer identifiers are referenced by devices and orders. External customer
codes must be present and unique in this reference schema:

```sql
CREATE TABLE atlas_app.customers (
    customer_id bigint PRIMARY KEY,
    external_code text NOT NULL UNIQUE
);
```

Each device belongs to a customer. The foreign key uses the default deletion
behavior; no cascading deletion is declared:

```sql
CREATE TABLE atlas_app.devices (
    device_id bigint PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES atlas_app.customers (customer_id)
);
```

Orders require a customer and creation timestamp. `billed`, `order_reference`
and `total_amount` are nullable. There is no `NULLS NOT DISTINCT` modifier on
the unique order reference, and no separate `NOT NULL` constraint on amount:

```sql
CREATE TABLE atlas_app.orders (
    order_id bigint PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES atlas_app.customers (customer_id),
    created_at timestamptz NOT NULL,
    billed boolean,
    order_reference text UNIQUE,
    total_amount numeric(12, 2) CHECK (total_amount >= 0)
);
```

Device events require a device, timestamp, severity and JSON payload. Severity
is constrained to the inclusive range 0 through 5:

```sql
CREATE TABLE atlas_app.device_events (
    event_id bigint PRIMARY KEY,
    device_id bigint NOT NULL REFERENCES atlas_app.devices (device_id),
    recorded_at timestamptz NOT NULL,
    severity integer NOT NULL CHECK (severity BETWEEN 0 AND 5),
    payload jsonb NOT NULL
);
```

## Customer lookup: Q-ATLAS-CUSTOMER-LOOKUP

This query is identical to the SQL in **LOCAL-INVENTORY**:

```sql
SELECT order_id, customer_id, created_at, billed
FROM atlas_app.orders
WHERE customer_id = $1
  AND created_at >= $2;
```

Parameter `$1` is a customer identifier; `$2` is an inclusive creation-time
lower bound. No upper time bound or billing-status filter is present.

## Device event range: Q-ATLAS-DEVICE-RANGE

```sql
SELECT event_id, device_id, recorded_at, severity
FROM atlas_app.device_events
WHERE device_id = $1
  AND recorded_at >= $2
  AND recorded_at < $3
ORDER BY recorded_at;
```

Parameter `$1` identifies one device, `$2` is the inclusive start timestamp,
and `$3` is the exclusive end timestamp. The request must supply a start
earlier than its end. The result is ordered by event time; no secondary
tie-breaking order is specified for events sharing a timestamp.

## Unbilled order queue: Q-ATLAS-UNBILLED

```sql
SELECT order_id, customer_id, created_at, billed
FROM atlas_app.orders
WHERE billed IS NOT TRUE
  AND created_at >= $1
ORDER BY created_at;
```

Parameter `$1` is an inclusive creation-time lower bound. The queue includes
both false and NULL billing states. It is distinct from a query requiring
`billed = TRUE`, and has no customer-identifier filter.

## Declared secondary indexes

The customer lookup has a declared B-tree index with customer first and
creation time second:

```sql
CREATE INDEX idx_atlas_orders_customer_created
ON atlas_app.orders USING btree (customer_id, created_at);
```

The event-range query has a declared B-tree index with device first and
recording time second:

```sql
CREATE INDEX idx_atlas_events_device_recorded
ON atlas_app.device_events USING btree (device_id, recorded_at);
```

The unbilled queue has a partial B-tree index on creation time. Its predicate
must be interpreted exactly as written:

```sql
CREATE INDEX idx_atlas_orders_unbilled_created
ON atlas_app.orders USING btree (created_at)
WHERE billed IS NOT TRUE;
```

A separate GIN index is declared for JSON payload searches:

```sql
CREATE INDEX idx_atlas_events_payload_gin
ON atlas_app.device_events USING gin (payload);
```

None of the three catalog queries filters on `payload`. The existence of its
GIN index does not establish that any of those queries will use it. Interpret
the methods, column order and predicate compatibility using the PostgreSQL
documentation, then obtain an actual plan if the chosen execution path is
required. Declared eligibility does not guarantee planner selection or speed.

## Inspection boundaries

Use these exact query IDs for the inspection procedure in
**LOCAL-MAINTENANCE**. Record the selected state and supplied parameters with
any later observation. No parameter values, EXPLAIN output, timing samples or
before-and-after index comparison are supplied here. The SQL definitions do
not certify which indexes currently exist in any running deployment.
