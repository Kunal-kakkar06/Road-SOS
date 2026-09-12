# RoadSOS Backward-Compatible Database Schema Migration Policy

**Effective Date**: September 11, 2026  

---

## Schema Migration Rules

To guarantee zero-downtime rolling upgrades, all database schema changes MUST follow the **Expand and Contract** pattern:

1. **Phase 1: Expand (Non-Breaking Addition)**:
   - Add new tables, nullable columns, or new non-unique indexes.
   - Old application versions ignore the new schema elements and continue operating without error.
2. **Phase 2: Transition (Dual-Write / Backfill)**:
   - Application write paths populate both legacy and new schema elements.
   - Run background data backfill scripts if necessary.
3. **Phase 3: Contract (Pruning Legacy Elements)**:
   - Once all application nodes are upgraded and verified, legacy columns/tables are removed in a subsequent release.

---

## Prohibited Schema Operations During Live Upgrades

- ❌ Renaming an existing column without a dual-write transition phase.
- ❌ Adding a `NOT NULL` constraint without a default value or backfill.
- ❌ Dropping an active table or column while previous application versions are running.
- ❌ Changing column data types in a non-castable manner.
