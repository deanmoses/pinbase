# Catalog Data Model

This document describes the catalog data model.

## The Entities

- `Franchise` (optional): a group of titles related by IP, like all the Indiana Jones pins in existence regardless of manufacturer
- `Series` (optional): a series of games with the same design lineage by the same creative team, such as the Eight Ball Series
- `Title` (always): the same conceptual game, like the original Medieval Madness _and_ its remakes
  - `Platform` (always): the shared hardware platform, like the Chicago Gaming remake of Medieval Madness. They all share the same basic hardware, such as System and display_type
    - `Edition` (always): a gameplay tier of the platform, like Godzilla Pro vs Godzilla Premium
      - `Model` (always): the actual buyable SKU. Every Edition has at least one Model, with one marked as the default. All Models within an Edition share the same gameplay and differ only in cosmetics. For example, Godzilla LE is a model of Godzilla Premium, which gets different cabinet art, a numbered plaque, colored plastics, and an exclusive topper.

## Entity Reference

### Franchise

Groups items related by IP, like all the Indiana Jones pins in existence regardless of manufacturer.

- Most Titles do not belong to any Franchise.
- A Franchise can span multiple manufacturers (e.g., Star Trek has been produced by Bally, Data East, Williams, and Stern across different eras).

#### Franchise Fields

- Description: history of the franchise in pinball

### Series

Groups related Titles that share a design lineage — for
example, the _Eight Ball_ series spans _Eight Ball_ (1977), _Eight Ball Deluxe_ (1981), and _Eight Ball Champ_ (1985).

- Most Titles do not belong to any Series.
- A Series can span multiple manufacturers (e.g., _Black Knight_ spans Williams and Stern)
- The relationship is many-to-many: a Title could theoretically belong to more than one
  Series, though that is rare in practice.
- People can be credited on a Series, like Steve Ritchie → Black Knight Series

#### Series Fields

- `description`: history of the series

### Title

A distinct pinball game design — the canonical identity of a game regardless of how many editions or variants were produced. Examples: _Medieval Madness_, _Eight Ball Deluxe_, _The Addams Family_.

- A `Title` can span multiple manufacturers, like _Medieval Madness_ and its remakes.
- Every `Platform` belongs to exactly one `Title`.
- Most `Titles` contain only one `Platform` (the original production run). Some contain several — e.g., _Medieval Madness_ contains both the Williams original and the Chicago Gaming remakes.

#### Title Fields

- `description`: overall game design history

#### Mapping from 3rd party sources

Example: Medieval Madness (OPDB Group G5pe4)

| OPDB ID     | Name                              | Manufacturer   | Year |
| ----------- | --------------------------------- | -------------- | ---- |
| G5pe4-MePZv | Medieval Madness                  | Williams       | 1997 |
| G5pe4-MkPRV | Medieval Madness (Remake Royal)   | Chicago Gaming | 2015 |
| G5pe4-M5W7V | Medieval Madness (Remake Special) | Chicago Gaming | 2016 |

All of these are the same Title.

### Platform

A specific manufacturer's hardware platform for a parent `Title`. Examples: _Williams Medieval Madness (1997)_, _Chicago Gaming Medieval Madness Remake (2015)_, _Stern Black Knight: Sword of Rage (2019)_.

#### Platform Fields

- `description`: the description of this specific platform, such as what was interesting about the remakes of Medieval Madness by Chicago Gaming.
- `year` and `month` of the production's reveal date — anchored to the World Premiere (press release or trade show), not the ship date.
- `manufacturer` (FK)
- `system` (FK)
- `display_type` (FK)
- `machine_type` (FK)
- `player_count`
- `flipper_count`
- Credits mapping to People (such as Art credit to Pat Lawlor)
- `features`: text (for now) containing just the features that distinguish it from the parent `Title`

### Edition

A gameplay tier within a `Platform`. Pro vs Premium are different Editions because they have different rules, shots, and features. Every `Platform` has at least one `Edition`.

This is NOT a distinct production run. When we get around to modeling it in the future, Edition will have 0..n ProductionRun records.

#### Edition Fields

- `description`: the story of this specific edition — e.g., what was notable about _Eight Ball Deluxe (LE)_ as a release.

### Model

The actual buyable SKU — the concrete thing a collector owns. Every `Edition` has at least one `Model`, with one marked as the **default**. All Models within an Edition share the same gameplay and differ only in cosmetics (cabinet art, numbered plaques, toppers, colored plastics). The default Model represents the standard offering of that Edition.

For example, the Godzilla Premium Edition has three Models: Godzilla Premium _(default)_, Godzilla LE, and Godzilla 70th Anniversary.

#### Model Fields

- `description`: describes history or circumstances of the model
- `default`: boolean flag — true for the canonical model of the Edition
- `sku`: the SKU of this model
- `year` and `month` first produced
- `features`: text (for now) containing just the cosmetic features that distinguish it from the default Model

## Fields common to all entities

- `name`: Human-friendly title of item
- `slug`: URL-friendly identifier
- `description`: markdown. We will eventually be adding rich linking support so that markdown can contain links that survive slug renames, by storing the record's ID in the markdown rather than the actual URL.
- `created_at`: bookkeeping of when the record was initially created in the database
- `updated_at`: bookkeeping of when the record was last updated in the database

## Use Cases

Tournaments care about what, Edition?

## Mapping from OPDB

OPDB has no `Franchise`, `Series`, `Platform`, or `Edition` concept. Franchise and Series data is hand-curated in `data/series.json`. `Platform` and `Edition` are derived at ingest time using the logic below.

| OPDB record type                 | `physical_machine` | Maps to                |
| -------------------------------- | ------------------ | ---------------------- |
| Group ID (e.g. `G5pe4`)          | n/a                | `Title`                |
| Non-alias record                 | `0`                | `Platform` + `Edition` |
| Non-alias record                 | `1`                | `Edition`              |
| Alias record (`is_alias` is set) | n/a                | `Model`                |

### Deriving Platform at ingest

Each distinct `(group_id, manufacturer)` pair among non-alias rows becomes one `Platform`. The `physical_machine=0` row for that pair defines the `Platform` (the shared hardware). Its fields (year, system, display_type, etc.) populate the `Platform` record.

If no `physical_machine=0` row exists for a `(group_id, manufacturer)` pair, derive the `Platform` from the earliest `manufacture_date` among the `physical_machine=1` rows, then lowest `opdb_id` for stability.

### Deriving Edition at ingest

Every non-alias OPDB row produces one `Edition` under its `Platform`:

- A `physical_machine=0` row (e.g. "Godzilla (Premium/LE)") produces both the `Platform` and an `Edition` representing that gameplay tier.
- Each `physical_machine=1` row (e.g. "Godzilla (Pro)") produces an additional `Edition` under the same `Platform`.

For simple games with a single OPDB row and no aliases, that row produces a `Platform` with one `Edition` and one default `Model`.

### Mapping alias records at ingest

All OPDB alias records (`is_alias` is set) become `Models`. They are assigned to the `Edition` created by their parent record (the non-alias row whose `opdb_id` is the prefix of the alias ID). The first alias processed for an `Edition` is marked as the default `Model`.
