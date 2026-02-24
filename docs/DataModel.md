# Data Model

This document describes the catalog data model for Pinbase.

## Hierarchy

```text
Series (optional, sparse)
  └── Title
        └── MachineModel
              └── MachineModel (alias/variant)
```

### Series

A **Series** groups related Titles that share a thematic or franchise lineage — for
example, the _Eight Ball_ series spans _Eight Ball_ (1977), _Eight Ball Deluxe_ (1981),
and _Eight Ball Champ_ (1985).

- Series are **manually curated**. No data ingest creates them automatically.
- Most Titles do not belong to any Series.
- A Series can span multiple manufacturers (e.g., Star Trek has been produced by Bally,
  Data East, Williams, and Stern across different eras).
- The relationship is many-to-many: a Title could theoretically belong to more than one
  Series, though that is rare in practice.

### Title

A **Title** represents a distinct pinball game design — the canonical identity of a game
regardless of how many editions or variants were produced. Examples: _Medieval Madness_,
_Eight Ball Deluxe_, _The Addams Family_.

- Every MachineModel belongs to exactly one Title.
- Most Titles contain only one MachineModel (the original production run). Some contain
  several (e.g., Eight Ball Deluxe, Eight Ball Deluxe LE, and Eight Ball Deluxe 1984
  edition all belong to the _Eight Ball Deluxe_ Title).

### MachineModel

A **MachineModel** represents a specific physical edition of a game — a distinct
production run with its own manufacturer, year, and feature set. Examples: _Eight Ball
Deluxe (LE)_, _Black Knight: Sword of Rage (Premium)_.

- MachineModels that are cosmetic or limited-edition variants of a parent machine carry
  an `alias_of` foreign key pointing to the primary MachineModel.
- Fields like manufacturer, year, machine type, and display type are resolved from the
  provenance claims system rather than being stored directly.
