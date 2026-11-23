# Atlas backup policy

- Source ID: LOCAL-BACKUP
- Document version: 1.0
- Document state: atlas-expanded-v1
- Reference date: 2026-11-23
- Data classification: Synthetic; schedules and recovery objectives are invented local policy.

## Coverage and ownership

Job `ATLAS-BACKUP-DAILY` covers database `atlas_telemetry`, identified by
**LOCAL-INVENTORY**. The declared source is `atlas-primary-01`; the reporting
replica is not the backup source. The job uses PostgreSQL 18 `pg_dump` custom
archive format (`-Fc`) for database object definitions and data. Restore work
uses `pg_restore`. These are intended procedures, not an installed job or
evidence that an archive exists.

The archive covers the database, not an entire PostgreSQL cluster. Cluster
role and tablespace definitions, WAL archives, host configuration and external
application files are outside this job. Required global object definitions
must come from a separately approved environment setup before a complete
rebuild. This policy defines no continuous WAL archiving or point-in-time
recovery service. A standby is not a substitute for the scheduled archive.

The intended operator is `atlas_backup_operator` under **LOCAL-ACCESS**.
The schema owner approves the procedure and any restore target. Policy
responsibility does not prove the operator's actual database privileges.

## Schedule, retention and archive records

| Policy field | Declared value |
| --- | --- |
| Start schedule | Every day at 01:00 UTC |
| Completion target | 02:00 UTC on the same day |
| Logical repository ID | ATLAS-ARCHIVE-DAILY |
| Retention | 14 successful daily archive generations |
| Audit-record retention | 90 days |
| Failure notification target | Within 15 minutes of detecting a failed or late run |

Retain fourteen successful generations, not an assumed fourteen calendar
days. A failed run must not replace a valid generation. Quarantine incomplete
archives, retain the last valid copies and open an incident for investigation.
The repository ID is a fictional inventory label, not an address or credential.

For each run, record its job/state, source database, archive ID, snapshot
reference time, completion time, exit status, byte size and SHA-256 checksum.
Record archive-integrity verification separately from a restore drill.
An archive filename or expected schedule alone does not prove success.

## Recovery objectives

The recovery point objective (**RPO**) is **24 hours**: at an incident time,
the recovery point of the usable archive should be no more than 24 hours old.
Use the archive's recorded snapshot reference time, not its filename or job
start schedule, to assess that objective. Delays or failures can violate it.

The recovery time objective (**RTO**) is **120 minutes**, measured from an
approved restore start to completion of the documented verification checks.
This is a target, not a measured restore duration or a guarantee. It does not
promise recovery to an arbitrary moment between daily archives.

Neither objective changes the 5-second reporting-replica lag rule in
**LOCAL-POLICY**. A lag assessment, archive integrity and restore readiness
are separate conclusions requiring their own evidence.

## Restore verification

Schedule a restore drill every Sunday at **03:30 UTC** using logical target
`atlas-restore-check`, an isolated disposable environment. The backup operator
selects a retained archive and verifies its checksum; the schema owner
authorizes the target and the identity that performs the restore. No restore
may overwrite the primary or reporting replica under this procedure.

After restoring, verify database/schema identities, selected object and
constraint definitions, and the three read-only queries in
**LOCAL-QUERY-CATALOG** with explicitly recorded parameters. Record the
archive ID, start/end times, checks performed and individual outcomes.
SQL execution success alone is not a complete application-correctness check.

The documents supply no archive records, checksums for actual backups, restore
drill results or observed durations. Use a matching observation before
claiming current backup success or compliance with an RPO/RTO target.
