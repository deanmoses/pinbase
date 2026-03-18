-- 03_compare.sql — Cross-source comparison views and slug quality analysis.
-- Depends on: 01_raw.sql, 02_staging.sql

------------------------------------------------------------
-- Cross-source: models vs OPDB (by opdb_id)
------------------------------------------------------------

CREATE OR REPLACE VIEW compare_models_opdb AS
SELECT
  m.slug,
  m.name AS pinbase_name,
  o.name AS opdb_name,
  m.name <> o.name AS name_differs,
  m.corporate_entity_slug AS pinbase_corporate_entity,
  ce.manufacturer_slug AS pinbase_manufacturer,
  o.manufacturer_name AS opdb_manufacturer,
  m.year AS pinbase_year,
  year(o.manufacture_date) AS opdb_year,
  m.year <> year(o.manufacture_date) AS year_differs,
  m.technology_generation_slug AS pinbase_tech_gen,
  o.technology_generation_slug AS opdb_tech_gen,
  m.technology_generation_slug <> o.technology_generation_slug AS tech_gen_differs,
  m.display_type_slug AS pinbase_display,
  o.display_type_slug AS opdb_display,
  m.display_type_slug <> o.display_type_slug AS display_differs,
  m.player_count AS pinbase_players,
  o.player_count AS opdb_players,
  m.opdb_id
FROM models AS m
INNER JOIN opdb_machines_staged AS o ON m.opdb_id = o.opdb_id
LEFT JOIN corporate_entities AS ce ON ce.slug = m.corporate_entity_slug;

------------------------------------------------------------
-- Cross-source: models vs IPDB (by ipdb_id)
------------------------------------------------------------

CREATE OR REPLACE VIEW compare_models_ipdb AS
SELECT
  m.slug,
  m.name AS pinbase_name,
  i.Title AS ipdb_name,
  m.name <> i.Title AS name_differs,
  m.corporate_entity_slug AS pinbase_corporate_entity,
  ce.manufacturer_slug AS pinbase_manufacturer,
  i.ManufacturerShortName AS ipdb_manufacturer,
  m.year AS pinbase_year,
  TRY_CAST(i.DateOfManufacture AS INTEGER) AS ipdb_year,
  m.year <> TRY_CAST(i.DateOfManufacture AS INTEGER) AS year_differs,
  m.technology_generation_slug AS pinbase_tech_gen,
  i.technology_generation_slug AS ipdb_tech_gen,
  m.player_count AS pinbase_players,
  i.Players AS ipdb_players,
  i.AverageFunRating AS ipdb_rating,
  i.ProductionNumber AS ipdb_production,
  m.ipdb_id
FROM models AS m
INNER JOIN ipdb_machines_staged AS i ON m.ipdb_id = i.IpdbId
LEFT JOIN corporate_entities AS ce ON ce.slug = m.corporate_entity_slug;

------------------------------------------------------------
-- Cross-source: titles vs OPDB groups (by opdb_group_id)
------------------------------------------------------------

CREATE OR REPLACE VIEW compare_titles_opdb AS
SELECT
  t.slug,
  t.name AS pinbase_name,
  g.name AS opdb_name,
  t.name <> g.name AS name_differs,
  t.opdb_group_id
FROM titles AS t
INNER JOIN opdb_groups AS g ON t.opdb_group_id = g.opdb_id;

------------------------------------------------------------
-- Cross-source: IPDB credits missing from Pinbase
-- Maps IPDB credit fields to pinbase person slugs via name/alias lookup,
-- then finds credits that exist in IPDB but not in Pinbase.
------------------------------------------------------------

CREATE OR REPLACE VIEW compare_credits_ipdb AS
WITH
-- Build a name→slug lookup from people + aliases
person_lookup AS (
  SELECT slug, LOWER(name) AS lookup_name FROM people
  UNION ALL
  SELECT slug, LOWER(UNNEST(aliases)) FROM people WHERE aliases IS NOT NULL
),
-- Flatten IPDB credit fields into (IpdbId, role, person_name) rows
ipdb_credits_raw AS (
  SELECT IpdbId, 'Design' AS role, TRIM(UNNEST(string_split(DesignBy, ','))) AS person_name FROM ipdb_machines WHERE DesignBy <> ''
  UNION ALL
  SELECT IpdbId, 'Art', TRIM(UNNEST(string_split(ArtBy, ','))) FROM ipdb_machines WHERE ArtBy <> ''
  UNION ALL
  SELECT IpdbId, 'Dots/Animation', TRIM(UNNEST(string_split(DotsAnimationBy, ','))) FROM ipdb_machines WHERE DotsAnimationBy <> ''
  UNION ALL
  SELECT IpdbId, 'Mechanics', TRIM(UNNEST(string_split(MechanicsBy, ','))) FROM ipdb_machines WHERE MechanicsBy <> ''
  UNION ALL
  SELECT IpdbId, 'Music', TRIM(UNNEST(string_split(MusicBy, ','))) FROM ipdb_machines WHERE MusicBy <> ''
  UNION ALL
  SELECT IpdbId, 'Sound', TRIM(UNNEST(string_split(SoundBy, ','))) FROM ipdb_machines WHERE SoundBy <> ''
  UNION ALL
  SELECT IpdbId, 'Software', TRIM(UNNEST(string_split(SoftwareBy, ','))) FROM ipdb_machines WHERE SoftwareBy <> ''
),
-- Filter out placeholder/sentinel names
ipdb_credits_filtered AS (
  SELECT * FROM ipdb_credits_raw
  WHERE LOWER(person_name) NOT IN (
    '(undisclosed)', 'undisclosed', 'unknown', 'missing', 'null', 'undefined',
    'n/a', 'none', 'tbd', 'tba', '?', ''
  )
    AND person_name NOT ILIKE '%(undisclosed)%'
    AND person_name NOT ILIKE '%unknown%'
),
-- Resolve person names to slugs
ipdb_credits AS (
  SELECT
    ic.IpdbId,
    ic.role,
    ic.person_name AS ipdb_person_name,
    pl.slug AS person_slug
  FROM ipdb_credits_filtered ic
  LEFT JOIN person_lookup pl ON LOWER(ic.person_name) = pl.lookup_name
)
SELECT
  m.slug AS model_slug,
  ic.role,
  ic.person_slug,
  ic.ipdb_person_name,
  ic.IpdbId
FROM ipdb_credits ic
JOIN models m ON m.ipdb_id = ic.IpdbId
WHERE ic.person_slug IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM pinbase_credits pc
    WHERE pc.model_slug = m.slug
      AND pc.person_slug = ic.person_slug
      AND pc.role = ic.role
  );

------------------------------------------------------------
-- Slug quality: name faithfulness
-- Compares each model's slug to a mechanical slugification of its name.
-- Large edit distance or missing words signal a slug that doesn't
-- represent the name well.
------------------------------------------------------------

CREATE OR REPLACE VIEW slug_name_faithfulness AS
WITH slugified AS (
  SELECT
    slug,
    name,
    title_slug,
    -- Mechanical slug: lowercase, spaces to hyphens, strip non-alphanumeric
    regexp_replace(
      lower(replace(name, ' ', '-')),
      '[^a-z0-9\-]', '', 'g'
    ) AS name_as_slug
  FROM models
)
SELECT
  *,
  slug <> name_as_slug AS slug_differs_from_name,
  length(slug) - length(name_as_slug) AS slug_length_delta
FROM slugified
WHERE slug <> name_as_slug;

------------------------------------------------------------
-- Slug quality: prime slug conflicts
-- Finds cases where a model's slug matches another title's slug,
-- suggesting the "obvious" slug was taken by a different title group.
-- Ranks by IPDB production count and rating so you can see when
-- an obscure model holds the prime slug over a popular one.
------------------------------------------------------------

CREATE OR REPLACE VIEW slug_prime_conflicts AS
WITH
  -- Models whose slug differs from their title_slug: they didn't get the "home" slug
  displaced AS (
    SELECT
      m.slug AS model_slug,
      m.name AS model_name,
      m.title_slug,
      m.ipdb_id,
      m.corporate_entity_slug,
      m.year
    FROM models AS m
    WHERE m.slug <> m.title_slug
      AND m.title_slug IS NOT NULL
  ),
  -- The model that holds the title's "prime" slug (slug = title_slug)
  prime_holders AS (
    SELECT
      m.slug AS model_slug,
      m.name AS model_name,
      m.title_slug,
      m.ipdb_id,
      m.corporate_entity_slug,
      m.year
    FROM models AS m
    WHERE m.slug = m.title_slug
  )
SELECT
  d.title_slug,
  -- The displaced (potentially popular) model
  d.model_slug AS displaced_slug,
  d.model_name AS displaced_name,
  d.corporate_entity_slug AS displaced_corporate_entity,
  d.year AS displaced_year,
  di.ProductionNumber AS displaced_production,
  di.AverageFunRating AS displaced_rating,
  -- The model holding the prime slug
  p.model_slug AS prime_slug,
  p.model_name AS prime_name,
  p.corporate_entity_slug AS prime_corporate_entity,
  p.year AS prime_year,
  pi.ProductionNumber AS prime_production,
  pi.AverageFunRating AS prime_rating
FROM displaced AS d
LEFT JOIN prime_holders AS p ON d.title_slug = p.title_slug
LEFT JOIN ipdb_machines AS di ON d.ipdb_id = di.IpdbId
LEFT JOIN ipdb_machines AS pi ON p.ipdb_id = pi.IpdbId
WHERE p.model_slug IS NOT NULL
ORDER BY COALESCE(di.ProductionNumber, 0) DESC;
