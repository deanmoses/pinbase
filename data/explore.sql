-- View definitions for data/explore.duckdb
-- Recreate: rm data/explore.duckdb && duckdb data/explore.duckdb < data/explore.sql

-- fandom_games
CREATE OR REPLACE VIEW fandom_games AS SELECT d.* FROM (SELECT unnest(games) AS d FROM read_json_auto('data/dump1/fandom_games.json'));

-- fandom_manufacturers
CREATE OR REPLACE VIEW fandom_manufacturers AS SELECT d.* FROM (SELECT unnest(manufacturers) AS d FROM read_json_auto('data/dump1/fandom_manufacturers.json'));

-- fandom_persons
CREATE OR REPLACE VIEW fandom_persons AS SELECT d.* FROM (SELECT unnest(persons) AS d FROM read_json_auto('data/dump1/fandom_persons.json'));

-- pinballmap_machines
CREATE OR REPLACE VIEW pinballmap_machines AS SELECT d.id, d."name", d.is_active, d.created_at, d.updated_at, d.ipdb_link, d."year", d.manufacturer, d.machine_group_id, d.ipdb_id, d.opdb_id, d.opdb_img, d.opdb_img_height, d.opdb_img_width, d.machine_type, d.machine_display, d.ic_eligible, d.kineticist_url FROM (SELECT unnest(machines) AS d FROM read_json_auto('data/dump1/pinballmap_machines.json'));

-- pinballmap_machine_groups
CREATE OR REPLACE VIEW pinballmap_machine_groups AS SELECT d.id, d."name", d.created_at, d.updated_at FROM (SELECT unnest(machine_groups) AS d FROM read_json_auto('data/dump1/pinballmap_machine_groups.json'));

-- opdb_groups
CREATE OR REPLACE VIEW opdb_groups AS SELECT * FROM read_json_auto('data/dump1/opdb_export_groups.json');

-- opdb_machines
CREATE OR REPLACE VIEW opdb_machines AS SELECT opdb_id, split_part(opdb_id, '-', 1) AS group_id, split_part(opdb_id, '-', 2) AS machine_id, CASE  WHEN ((split_part(opdb_id, '-', 3) = '')) THEN (NULL) ELSE split_part(opdb_id, '-', 3) END AS alias_id, is_machine, is_alias, "name", common_name, shortname, physical_machine, ipdb_id, manufacture_date, manufacturer, "type", display, player_count, features, keywords, description, created_at, updated_at, images, CASE  WHEN (("type" = 'em')) THEN ('electromechanical') WHEN (("type" = 'ss')) THEN ('solid-state') WHEN (("type" = 'me')) THEN ('pure-mechanical') ELSE NULL END AS technology_generation_slug, CASE  WHEN ((display = 'reels')) THEN ('score-reels') WHEN ((display = 'lights')) THEN ('backglass-lights') WHEN ((display = 'alphanumeric')) THEN ('alphanumeric') WHEN ((display = 'cga')) THEN ('cga') WHEN ((display = 'dmd')) THEN ('dot-matrix') WHEN ((display = 'lcd')) THEN ('lcd') ELSE NULL END AS display_type_slug, CAST(NULL AS VARCHAR) AS system_slug FROM read_json_auto('data/dump1/opdb_export_machines.json');

-- opdb_manufacturers
CREATE OR REPLACE VIEW opdb_manufacturers AS SELECT DISTINCT manufacturer.manufacturer_id AS opdb_manufacturer_id, manufacturer."name" AS "name", manufacturer.full_name AS full_name FROM opdb_machines WHERE (manufacturer IS NOT NULL) ORDER BY "name";

-- opdb_tiers
CREATE OR REPLACE VIEW opdb_tiers AS SELECT opdb_id, group_id AS opdb_group_id, machine_id, (manufacturer ->> 'name') AS manufacturer, "name", common_name, shortname, manufacture_date, ipdb_id, images, ((regexp_matches("name", '\([^)]+/[^)]+\)') OR ("name" ~~ '% / %')) AND EXISTS(SELECT 1 FROM opdb_machines AS a WHERE ((a.group_id = opdb_machines.group_id) AND (a.machine_id = opdb_machines.machine_id) AND (a.is_alias = 't')))) AS is_combo_label, technology_generation_slug, display_type_slug, system_slug FROM opdb_machines WHERE (is_machine = 't');

-- pinbase_cabinets
CREATE OR REPLACE VIEW pinbase_cabinets AS SELECT * FROM read_json_auto('data/cabinets.json');

-- pinbase_conversions
CREATE OR REPLACE VIEW pinbase_conversions AS SELECT * FROM read_json_auto('data/conversions.json');

-- pinbase_corporate_entities
CREATE OR REPLACE VIEW pinbase_corporate_entities AS SELECT * FROM read_json_auto('data/corporate_entities.json');

-- pinbase_credits
CREATE OR REPLACE VIEW pinbase_credits AS SELECT * FROM read_json_auto('data/credits.json', (union_by_name = CAST('t' AS BOOLEAN)));

-- pinbase_display_subtypes
CREATE OR REPLACE VIEW pinbase_display_subtypes AS SELECT * FROM read_json_auto('data/display_subtypes.json');

-- pinbase_display_types
CREATE OR REPLACE VIEW pinbase_display_types AS SELECT * FROM read_json_auto('data/display_types.json');

-- pinbase_franchises
CREATE OR REPLACE VIEW pinbase_franchises AS SELECT * FROM read_json_auto('data/franchises.json');

-- pinbase_game_formats
CREATE OR REPLACE VIEW pinbase_game_formats AS SELECT * FROM read_json_auto('data/game_formats.json');

-- pinbase_gameplay_features
CREATE OR REPLACE VIEW pinbase_gameplay_features AS SELECT * FROM read_json_auto('data/gameplay_features.json');

-- pinbase_manufacturers
CREATE OR REPLACE VIEW pinbase_manufacturers AS SELECT * FROM read_json_auto('data/manufacturers.json');

-- pinbase_models
CREATE OR REPLACE VIEW pinbase_models AS SELECT * FROM read_json_auto('data/models.json', (union_by_name = CAST('t' AS BOOLEAN)));

-- pinbase_people
CREATE OR REPLACE VIEW pinbase_people AS SELECT * FROM read_json_auto('data/people.json', (union_by_name = CAST('t' AS BOOLEAN)));

-- pinbase_productions
CREATE OR REPLACE VIEW pinbase_productions AS SELECT * FROM read_json_auto('data/productions.json', (union_by_name = CAST('t' AS BOOLEAN)));

-- pinbase_series
CREATE OR REPLACE VIEW pinbase_series AS SELECT * FROM read_json_auto('data/series.json');

-- pinbase_systems
CREATE OR REPLACE VIEW pinbase_systems AS SELECT * FROM read_json_auto('data/systems.json');

-- pinbase_tags
CREATE OR REPLACE VIEW pinbase_tags AS SELECT * FROM read_json_auto('data/tags.json');

-- pinbase_technology_generations
CREATE OR REPLACE VIEW pinbase_technology_generations AS SELECT * FROM read_json_auto('data/technology_generations.json');

-- pinbase_technology_subgenerations
CREATE OR REPLACE VIEW pinbase_technology_subgenerations AS SELECT * FROM read_json_auto('data/technology_subgenerations.json');

-- pinbase_tiers
CREATE OR REPLACE VIEW pinbase_tiers AS SELECT * FROM read_json_auto('data/tiers.json', (union_by_name = CAST('t' AS BOOLEAN)));

-- pinbase_titles
CREATE OR REPLACE VIEW pinbase_titles AS SELECT * FROM read_json_auto('data/titles.json', (union_by_name = CAST('t' AS BOOLEAN)));

-- catalog_cabinets
CREATE OR REPLACE VIEW catalog_cabinets AS SELECT slug, "name", display_order, description FROM pinbase_cabinets ORDER BY display_order;

-- catalog_corporate_entities
CREATE OR REPLACE VIEW catalog_corporate_entities AS SELECT ce."name", ce.manufacturer_slug, ce.year_start, ce.year_end FROM pinbase_corporate_entities AS ce;

-- catalog_credits
CREATE OR REPLACE VIEW catalog_credits AS SELECT pc.series_slug, ps."name" AS series_name, pc.person_slug, pp."name" AS person_name, pc."role" FROM pinbase_credits AS pc LEFT JOIN pinbase_series AS ps ON ((pc.series_slug = ps.slug)) LEFT JOIN pinbase_people AS pp ON ((pc.person_slug = pp.slug));

-- catalog_display_subtypes
CREATE OR REPLACE VIEW catalog_display_subtypes AS SELECT ds.slug, ds."name", ds.display_order, ds.description, ds.display_type_slug, dt.title AS display_type_name FROM pinbase_display_subtypes AS ds LEFT JOIN pinbase_display_types AS dt ON ((ds.display_type_slug = dt.slug)) ORDER BY ds.display_order;

-- catalog_game_formats
CREATE OR REPLACE VIEW catalog_game_formats AS SELECT slug, "name", display_order, description FROM pinbase_game_formats ORDER BY display_order;

-- catalog_gameplay_features
CREATE OR REPLACE VIEW catalog_gameplay_features AS SELECT slug, "name", display_order, description FROM pinbase_gameplay_features ORDER BY display_order;

-- catalog_manufacturers
CREATE OR REPLACE VIEW catalog_manufacturers AS SELECT p."name", p.slug, p.description, f.page_id AS fandom_page_id, f.wikitext AS fandom_wikitext FROM pinbase_manufacturers AS p LEFT JOIN fandom_manufacturers AS f ON ((p."name" = f.title));

-- catalog_model_tags
CREATE OR REPLACE VIEW catalog_model_tags AS SELECT om.opdb_id, CASE  WHEN ((f = 'Home model')) THEN ('home-use') WHEN ((f = 'Widebody')) THEN ('widebody') WHEN ((f = 'Remake')) THEN ('remake') WHEN ((f = 'Conversion kit')) THEN ('conversion-kit') WHEN ((f = 'Export edition')) THEN ('export') ELSE NULL END AS tag_slug FROM opdb_machines AS om , unnest(om.features) AS t(f) WHERE CASE  WHEN ((f = 'Home model')) THEN (CAST('t' AS BOOLEAN)) WHEN ((f = 'Widebody')) THEN (CAST('t' AS BOOLEAN)) WHEN ((f = 'Remake')) THEN (CAST('t' AS BOOLEAN)) WHEN ((f = 'Conversion kit')) THEN (CAST('t' AS BOOLEAN)) WHEN ((f = 'Export edition')) THEN (CAST('t' AS BOOLEAN)) ELSE CAST('f' AS BOOLEAN) END;

-- catalog_platforms
CREATE OR REPLACE VIEW catalog_platforms AS WITH non_alias AS (SELECT *, manufacturer."name" AS mfr_name, manufacturer.full_name AS mfr_full_name FROM opdb_machines WHERE (is_machine = CAST('t' AS BOOLEAN))), ranked AS (SELECT *, row_number() OVER (PARTITION BY group_id, mfr_name ORDER BY physical_machine ASC, manufacture_date ASC, opdb_id ASC) AS rn FROM non_alias)SELECT group_id AS opdb_group_id, mfr_name AS manufacturer, mfr_full_name AS manufacturer_full_name, ((group_id || '-') || machine_id) AS platform_opdb_id, "name", manufacture_date, "type", display, player_count, description FROM ranked WHERE (rn = 1);

-- catalog_productions
CREATE OR REPLACE VIEW catalog_productions AS WITH overridden_tiers AS (SELECT pt.opdb_id AS tier_opdb_id, pt.production_slug, pp.title_slug, pp.slug AS production_slug, pp."name" AS production_name, pp.description AS production_description FROM pinbase_tiers AS pt INNER JOIN pinbase_productions AS pp ON ((pt.production_slug = pp.slug)) WHERE (pt.production_slug IS NOT NULL)), override_productions AS (SELECT ot.production_slug AS slug, ot.production_name AS "name", ot.production_description AS description, oe.opdb_group_id, oe.manufacturer, oe.technology_generation_slug, oe.manufacture_date, oe.opdb_id AS representative_opdb_id, CAST('t' AS BOOLEAN) AS is_override FROM overridden_tiers AS ot INNER JOIN opdb_tiers AS oe ON ((ot.tier_opdb_id = oe.opdb_id))), adjusted_base AS (SELECT t.opdb_group_id, t.manufacturer, t.technology_generation_slug, min(t.manufacture_date) AS manufacture_date, min(t.opdb_id) AS representative_opdb_id FROM opdb_tiers AS t LEFT JOIN overridden_tiers AS ot ON ((t.opdb_id = ot.tier_opdb_id)) WHERE (ot.tier_opdb_id IS NULL) GROUP BY t.opdb_group_id, t.manufacturer, t.technology_generation_slug), auto_productions AS (SELECT CAST(NULL AS VARCHAR) AS slug, CAST(NULL AS VARCHAR) AS "name", CAST(NULL AS VARCHAR) AS description, ab.opdb_group_id, ab.manufacturer, ab.technology_generation_slug, ab.manufacture_date, ab.representative_opdb_id, CAST('f' AS BOOLEAN) AS is_override FROM adjusted_base AS ab)(SELECT * FROM auto_productions) UNION ALL (SELECT * FROM override_productions);

-- catalog_tags
CREATE OR REPLACE VIEW catalog_tags AS SELECT t.slug, t."name", t.display_order, t.description, count(DISTINCT mt.opdb_id) AS model_count FROM pinbase_tags AS t LEFT JOIN catalog_model_tags AS mt ON ((t.slug = mt.tag_slug)) GROUP BY t.slug, t."name", t.display_order, t.description ORDER BY t.display_order;

-- catalog_technology_subgenerations
CREATE OR REPLACE VIEW catalog_technology_subgenerations AS SELECT tsg.slug, tsg."name", tsg.display_order, tsg.description, tsg.technology_generation_slug, tg.title AS technology_generation_name FROM pinbase_technology_subgenerations AS tsg LEFT JOIN pinbase_technology_generations AS tg ON ((tsg.technology_generation_slug = tg.slug)) ORDER BY tsg.display_order;

-- catalog_tier_productions
CREATE OR REPLACE VIEW catalog_tier_productions AS WITH overridden_tiers AS (SELECT pt.opdb_id AS tier_opdb_id, pt.production_slug FROM pinbase_tiers AS pt WHERE (pt.production_slug IS NOT NULL))(SELECT t.opdb_id AS tier_opdb_id, p.slug AS production_slug, p.opdb_group_id, p.manufacturer, p.technology_generation_slug, p.is_override FROM opdb_tiers AS t INNER JOIN overridden_tiers AS ot ON ((t.opdb_id = ot.tier_opdb_id)) INNER JOIN catalog_productions AS p ON (((ot.production_slug = p.slug) AND (p.is_override = CAST('t' AS BOOLEAN))))) UNION ALL (SELECT t.opdb_id AS tier_opdb_id, p.slug AS production_slug, p.opdb_group_id, p.manufacturer, p.technology_generation_slug, p.is_override FROM opdb_tiers AS t LEFT JOIN overridden_tiers AS ot ON ((t.opdb_id = ot.tier_opdb_id)) INNER JOIN catalog_productions AS p ON (((t.opdb_group_id = p.opdb_group_id) AND (t.manufacturer = p.manufacturer) AND (t.technology_generation_slug IS NOT DISTINCT FROM p.technology_generation_slug) AND (p.is_override = CAST('f' AS BOOLEAN)))) WHERE (ot.tier_opdb_id IS NULL));

-- catalog_titles
CREATE OR REPLACE VIEW catalog_titles AS SELECT g.opdb_id AS opdb_group_id, g."name", g.shortname, g.description, t.slug AS title_slug, t.franchise_slug, t.series_slug FROM opdb_groups AS g LEFT JOIN pinbase_titles AS t ON ((g.opdb_id = t.opdb_group_id));

-- ipdb_machines
CREATE OR REPLACE VIEW ipdb_machines AS SELECT d.*, CASE  WHEN ((d.TypeShortName = 'EM')) THEN ('electromechanical') WHEN ((d.TypeShortName = 'SS')) THEN ('solid-state') ELSE CASE  WHEN ((d."Type" = 'Pure Mechanical (PM)')) THEN ('pure-mechanical') ELSE NULL END END AS technology_generation_slug, CAST(NULL AS VARCHAR) AS display_type_slug, ps.slug AS system_slug FROM (SELECT unnest("Data") AS d FROM read_json_auto('data/dump1/ipdbdatabase.json', (maximum_object_size = 67108864))) LEFT JOIN pinbase_systems AS ps ON (list_contains(ps.mpu_strings, d.MPU));

-- ipdb_manufacturers
CREATE OR REPLACE VIEW ipdb_manufacturers AS SELECT DISTINCT ManufacturerId AS ipdb_manufacturer_id, Manufacturer AS "name", ManufacturerShortName AS short_name FROM ipdb_machines WHERE (Manufacturer IS NOT NULL) ORDER BY "name";

-- ipdb_people
CREATE OR REPLACE VIEW ipdb_people AS WITH credits_unpivoted AS (SELECT IpdbId, Title, credit_role, credit_names FROM ipdb_machines UNPIVOT (credit_names FOR credit_role IN ('DesignBy', 'ArtBy', 'MusicBy', 'SoundBy', 'SoftwareBy', 'MechanicsBy', 'DotsAnimationBy')) WHERE (credit_names IS NOT NULL)), split_names AS (SELECT IpdbId, Title, credit_role, main."trim"(unnest(string_split(credit_names, ','))) AS "name" FROM credits_unpivoted)SELECT "name", CASE  WHEN ((credit_role = 'DesignBy')) THEN ('Design') WHEN ((credit_role = 'ArtBy')) THEN ('Art') WHEN ((credit_role = 'MusicBy')) THEN ('Music') WHEN ((credit_role = 'SoundBy')) THEN ('Sound') WHEN ((credit_role = 'SoftwareBy')) THEN ('Software') WHEN ((credit_role = 'MechanicsBy')) THEN ('Mechanics') WHEN ((credit_role = 'DotsAnimationBy')) THEN ('Dots/Animation') ELSE NULL END AS "role", IpdbId, Title AS machine_title FROM split_names WHERE ("name" != '');

-- ipdb_machine_files
CREATE OR REPLACE VIEW ipdb_machine_files AS SELECT IpdbId AS ipdb_id, Title AS machine_name, f.Url AS file_url, f."Name" AS file_name, category FROM ipdb_machines, (SELECT unnest(ImageFiles) AS f, 'image' AS category UNION ALL SELECT unnest(Documentation), 'documentation' UNION ALL SELECT unnest(Files), 'file' UNION ALL SELECT unnest(RuleSheetUrls), 'rule_sheet' UNION ALL SELECT unnest(ROMs), 'rom' UNION ALL SELECT unnest(ServiceBulletins), 'service_bulletin' UNION ALL SELECT unnest(MultimediaFiles), 'multimedia');

-- opdb_keywords
CREATE OR REPLACE VIEW opdb_keywords AS SELECT opdb_id, "name", unnest(keywords) AS keyword FROM opdb_machines WHERE (len(keywords) > 0);

-- opdb_machine_images
CREATE OR REPLACE VIEW opdb_machine_images AS SELECT opdb_id, "name", img.title AS image_title, img."primary" AS is_primary, img."type" AS image_type, img.urls.small AS url_small, img.urls.medium AS url_medium, img.urls."large" AS url_large, img.sizes.small.width AS small_width, img.sizes.small.height AS small_height, img.sizes.medium.width AS medium_width, img.sizes.medium.height AS medium_height, img.sizes."large".width AS large_width, img.sizes."large".height AS large_height FROM opdb_machines, unnest(images) AS t(img) WHERE (len(images) > 0);

-- opdb_models
CREATE OR REPLACE VIEW opdb_models AS WITH combo_labels AS (SELECT opdb_group_id, machine_id FROM opdb_tiers WHERE is_combo_label), alias_models AS (SELECT a.opdb_id, a.group_id AS opdb_group_id, a.machine_id, a.alias_id, ((a.group_id || '-') || a.machine_id) AS tier_opdb_id, (a.manufacturer ->> 'name') AS manufacturer, a."name", a.common_name, a.shortname, a.manufacture_date, a.ipdb_id, a.images, CASE  WHEN ((cl.machine_id IS NOT NULL)) THEN ((row_number() OVER (PARTITION BY a.group_id, a.machine_id ORDER BY a.opdb_id) = 1)) ELSE CAST('f' AS BOOLEAN) END AS is_default, CAST('f' AS BOOLEAN) AS is_synthetic FROM opdb_machines AS a LEFT JOIN combo_labels AS cl ON (((cl.opdb_group_id = a.group_id) AND (cl.machine_id = a.machine_id))) WHERE (a.is_alias = 't')), tier_default_models AS (SELECT opdb_id, group_id AS opdb_group_id, machine_id, CAST(NULL AS VARCHAR) AS alias_id, opdb_id AS tier_opdb_id, (manufacturer ->> 'name') AS manufacturer, "name", common_name, shortname, manufacture_date, ipdb_id, images, CAST('t' AS BOOLEAN) AS is_default, CAST('f' AS BOOLEAN) AS is_synthetic FROM opdb_machines AS m WHERE ((m.is_machine = 't') AND (NOT EXISTS(SELECT 1 FROM combo_labels AS cl WHERE ((cl.opdb_group_id = m.group_id) AND (cl.machine_id = m.machine_id)))) AND EXISTS(SELECT 1 FROM opdb_machines AS a WHERE ((a.group_id = m.group_id) AND (a.machine_id = m.machine_id) AND (a.is_alias = 't'))))), synthetic_models AS (SELECT opdb_id, group_id AS opdb_group_id, machine_id, CAST(NULL AS VARCHAR) AS alias_id, opdb_id AS tier_opdb_id, (manufacturer ->> 'name') AS manufacturer, "name", common_name, shortname, manufacture_date, ipdb_id, images, CAST('t' AS BOOLEAN) AS is_default, CAST('t' AS BOOLEAN) AS is_synthetic FROM opdb_machines AS m WHERE ((m.is_machine = 't') AND (NOT EXISTS(SELECT 1 FROM opdb_machines AS a WHERE ((a.group_id = m.group_id) AND (a.machine_id = m.machine_id) AND (a.is_alias = 't'))))))((SELECT * FROM alias_models) UNION ALL (SELECT * FROM tier_default_models)) UNION ALL (SELECT * FROM synthetic_models);

-- catalog_franchises
CREATE OR REPLACE VIEW catalog_franchises AS SELECT f.slug, f."name", f.description, count(ct.opdb_group_id) AS title_count FROM pinbase_franchises AS f LEFT JOIN catalog_titles AS ct ON ((f.slug = ct.franchise_slug)) GROUP BY f.slug, f."name", f.description ORDER BY title_count DESC;

-- ipdb_manufacturer_resolution
-- Maps each distinct IPDB Manufacturer string to a resolved manufacturer slug.
-- Priority: 1) corporate entity lookup on parsed company name,
--           2) manufacturer name match on trade name,
--           3) manufacturer name match on company name.
-- Also parses headquarters location into city/state/country.
CREATE OR REPLACE VIEW ipdb_manufacturer_resolution AS
WITH
  parsed AS (
    SELECT DISTINCT
      Manufacturer AS raw_manufacturer,
      regexp_extract(Manufacturer, '\[Trade Name:\s*(.+?)\]', 1) AS trade_name,
      regexp_replace(
        regexp_replace(
          regexp_replace(
            regexp_replace(Manufacturer, '\s*\[Trade Name:.*?\]', ''),
            '\s*\(\d{4}.*?\)', ''),
          ',\s*of\s+.*$', ''),
        ',\s*$', '') AS company_name,
      regexp_extract(Manufacturer, ',\s*of\s+(.+?)(?:\s*\(\d{4}|\s*\[Trade|\s*$)', 1) AS location_raw
    FROM ipdb_machines
    WHERE Manufacturer IS NOT NULL
  ),
  ce_match AS (
    SELECT DISTINCT ON (p.raw_manufacturer)
      p.raw_manufacturer, p.company_name, p.trade_name, p.location_raw,
      ce.manufacturer_slug, 'corporate_entity' AS resolution_method,
      ce.headquarters_city AS ce_hq_city,
      ce.headquarters_state AS ce_hq_state,
      ce.headquarters_country AS ce_hq_country
    FROM parsed p
    INNER JOIN pinbase_corporate_entities ce ON lower(p.company_name) = lower(ce.name)
  ),
  unresolved_after_ce AS (
    SELECT * FROM parsed
    WHERE raw_manufacturer NOT IN (SELECT raw_manufacturer FROM ce_match)
  ),
  trade_match AS (
    SELECT DISTINCT ON (p.raw_manufacturer)
      p.raw_manufacturer, p.company_name, p.trade_name, p.location_raw,
      m.slug AS manufacturer_slug, 'trade_name' AS resolution_method
    FROM unresolved_after_ce p
    INNER JOIN pinbase_manufacturers m ON lower(p.trade_name) = lower(m.name)
    WHERE p.trade_name <> ''
  ),
  unresolved_after_trade AS (
    SELECT * FROM unresolved_after_ce
    WHERE raw_manufacturer NOT IN (SELECT raw_manufacturer FROM trade_match)
  ),
  name_match AS (
    SELECT DISTINCT ON (p.raw_manufacturer)
      p.raw_manufacturer, p.company_name, p.trade_name, p.location_raw,
      m.slug AS manufacturer_slug, 'name_match' AS resolution_method
    FROM unresolved_after_trade p
    INNER JOIN pinbase_manufacturers m ON lower(p.company_name) = lower(m.name)
  ),
  resolved AS (
    (SELECT raw_manufacturer, company_name, trade_name, location_raw, manufacturer_slug, resolution_method, ce_hq_city, ce_hq_state, ce_hq_country FROM ce_match)
    UNION ALL
    (SELECT raw_manufacturer, company_name, trade_name, location_raw, manufacturer_slug, resolution_method, NULL, NULL, NULL FROM trade_match)
    UNION ALL
    (SELECT raw_manufacturer, company_name, trade_name, location_raw, manufacturer_slug, resolution_method, NULL, NULL, NULL FROM name_match)
  ),
  -- US states for disambiguating 2-part locations (city+state vs city+country)
  us_states(state_name) AS (
    VALUES ('Alabama'),('Alaska'),('Arizona'),('Arkansas'),('California'),('Colorado'),
    ('Connecticut'),('Delaware'),('Florida'),('Georgia'),('Hawaii'),('Idaho'),
    ('Illinois'),('Indiana'),('Iowa'),('Kansas'),('Kentucky'),('Louisiana'),
    ('Maine'),('Maryland'),('Massachusetts'),('Michigan'),('Minnesota'),
    ('Mississippi'),('Missouri'),('Montana'),('Nebraska'),('Nevada'),
    ('New Hampshire'),('New Jersey'),('New Mexico'),('New York'),
    ('North Carolina'),('North Dakota'),('Ohio'),('Oklahoma'),('Oregon'),
    ('Pennsylvania'),('Rhode Island'),('South Carolina'),('South Dakota'),
    ('Tennessee'),('Texas'),('Utah'),('Vermont'),('Virginia'),('Washington'),
    ('West Virginia'),('Wisconsin'),('Wyoming'),
    -- Typos found in IPDB data
    ('NewYork'),('SouthCarolina')
  )
SELECT
  r.raw_manufacturer,
  r.company_name,
  r.trade_name,
  r.manufacturer_slug,
  r.resolution_method,
  r.location_raw,
  COALESCE(r.ce_hq_city, CASE
    WHEN r.location_raw IS NULL OR r.location_raw = '' THEN NULL
    WHEN len(string_split(r.location_raw, ', ')) >= 2 THEN string_split(r.location_raw, ', ')[1]
    ELSE NULL
  END) AS headquarters_city,
  COALESCE(r.ce_hq_state, CASE
    WHEN r.location_raw IS NULL OR r.location_raw = '' THEN NULL
    WHEN len(string_split(r.location_raw, ', ')) >= 3 THEN string_split(r.location_raw, ', ')[2]
    WHEN len(string_split(r.location_raw, ', ')) = 2
      AND EXISTS(SELECT 1 FROM us_states WHERE lower(state_name) = lower(string_split(r.location_raw, ', ')[2]))
      THEN string_split(r.location_raw, ', ')[2]
    WHEN len(string_split(r.location_raw, ', ')) = 1
      AND EXISTS(SELECT 1 FROM us_states WHERE lower(state_name) = lower(r.location_raw))
      THEN r.location_raw
    ELSE NULL
  END) AS headquarters_state,
  COALESCE(r.ce_hq_country, CASE
    WHEN r.location_raw IS NULL OR r.location_raw = '' THEN NULL
    WHEN len(string_split(r.location_raw, ', ')) >= 3 THEN string_split(r.location_raw, ', ')[len(string_split(r.location_raw, ', '))]
    WHEN len(string_split(r.location_raw, ', ')) = 2
      AND EXISTS(SELECT 1 FROM us_states WHERE lower(state_name) = lower(string_split(r.location_raw, ', ')[2]))
      THEN 'USA'
    WHEN len(string_split(r.location_raw, ', ')) = 2 THEN string_split(r.location_raw, ', ')[2]
    WHEN len(string_split(r.location_raw, ', ')) = 1
      AND EXISTS(SELECT 1 FROM us_states WHERE lower(state_name) = lower(r.location_raw))
      THEN 'USA'
    ELSE r.location_raw
  END) AS headquarters_country
FROM resolved r;

-- catalog_ipdb_models
CREATE OR REPLACE VIEW catalog_ipdb_models AS WITH opdb_link AS ((SELECT ipdb_id, opdb_id AS opdb_machine_id, group_id AS opdb_group_id, opdb_id AS tier_opdb_id FROM opdb_machines WHERE ((is_machine = 't') AND (ipdb_id IS NOT NULL))) UNION ALL (SELECT ipdb_id, opdb_id AS opdb_machine_id, group_id AS opdb_group_id, ((group_id || '-') || machine_id) AS tier_opdb_id FROM opdb_machines WHERE ((is_alias = 't') AND (ipdb_id IS NOT NULL)))), best_link AS (SELECT DISTINCT ON (ipdb_id) * FROM opdb_link ORDER BY ipdb_id, tier_opdb_id)SELECT i.*, o.opdb_machine_id, o.opdb_group_id, o.tier_opdb_id FROM ipdb_machines AS i LEFT JOIN best_link AS o ON ((i.IpdbId = o.ipdb_id));

-- catalog_models
CREATE OR REPLACE VIEW catalog_models AS WITH opdb AS (SELECT opdb_id, opdb_group_id, machine_id, alias_id, tier_opdb_id, manufacturer, "name", common_name, shortname, manufacture_date, ipdb_id, images, is_default, is_synthetic, 'opdb' AS "source" FROM opdb_models), ipdb_only AS (SELECT CAST(NULL AS VARCHAR) AS opdb_id, CAST(NULL AS VARCHAR) AS opdb_group_id, CAST(NULL AS VARCHAR) AS machine_id, CAST(NULL AS VARCHAR) AS alias_id, CAST(NULL AS VARCHAR) AS tier_opdb_id, COALESCE(imr_mfr."name", NULLIF(imr.trade_name, ''), imr.company_name, im.ManufacturerShortName) AS manufacturer, im.Title AS "name", CAST(NULL AS VARCHAR) AS common_name, CAST(NULL AS VARCHAR) AS shortname, CASE  WHEN ((im.DateOfManufacture IS NOT NULL)) THEN (TRY_CAST(CAST(im.DateOfManufacture AS VARCHAR) AS DATE)) ELSE NULL END AS manufacture_date, im.IpdbId AS ipdb_id, CAST(main.list_value() AS STRUCT(title VARCHAR, "primary" BOOLEAN, "type" VARCHAR, urls STRUCT(medium VARCHAR, "large" VARCHAR, small VARCHAR), sizes STRUCT(medium STRUCT(width BIGINT, height BIGINT), "large" STRUCT(width BIGINT, height BIGINT), small STRUCT(width BIGINT, height BIGINT)))[]) AS images, CAST('t' AS BOOLEAN) AS is_default, CAST('f' AS BOOLEAN) AS is_synthetic, 'ipdb' AS "source" FROM ipdb_machines AS im LEFT JOIN opdb_machines AS om ON ((im.IpdbId = om.ipdb_id)) LEFT JOIN ipdb_manufacturer_resolution AS imr ON ((im.Manufacturer = imr.raw_manufacturer)) LEFT JOIN pinbase_manufacturers AS imr_mfr ON ((imr.manufacturer_slug = imr_mfr.slug)) WHERE (om.opdb_id IS NULL)), all_models AS ((SELECT * FROM opdb) UNION ALL (SELECT * FROM ipdb_only))SELECT m.*, COALESCE(om.technology_generation_slug, im.technology_generation_slug) AS technology_generation_slug, COALESCE(pm.display_type_slug, om.display_type_slug, im.display_type_slug) AS display_type_slug, COALESCE(om.system_slug, im.system_slug) AS system_slug FROM all_models AS m LEFT JOIN pinbase_models AS pm ON ((m.opdb_id = pm.opdb_id)) LEFT JOIN opdb_machines AS om ON ((m.opdb_id = om.opdb_id)) LEFT JOIN ipdb_machines AS im ON ((m.ipdb_id = im.IpdbId));

-- catalog_model_files
CREATE OR REPLACE VIEW catalog_model_files AS (SELECT cm.opdb_id, cm.ipdb_id, 'image' AS category, oi.image_type, oi.is_primary, oi.image_title AS file_name, CAST(NULL AS VARCHAR) AS file_url, oi.url_small, oi.url_medium, oi.url_large, oi.small_width, oi.small_height, oi.medium_width, oi.medium_height, oi.large_width, oi.large_height, 'opdb' AS "source" FROM opdb_machine_images AS oi INNER JOIN catalog_models AS cm ON ((oi.opdb_id = cm.opdb_id))) UNION ALL (SELECT cm.opdb_id, cm.ipdb_id, imf.category, CAST(NULL AS VARCHAR) AS image_type, CAST(NULL AS BOOLEAN) AS is_primary, imf.file_name, imf.file_url, CAST(NULL AS VARCHAR) AS url_small, CAST(NULL AS VARCHAR) AS url_medium, CAST(NULL AS VARCHAR) AS url_large, CAST(NULL AS BIGINT) AS small_width, CAST(NULL AS BIGINT) AS small_height, CAST(NULL AS BIGINT) AS medium_width, CAST(NULL AS BIGINT) AS medium_height, CAST(NULL AS BIGINT) AS large_width, CAST(NULL AS BIGINT) AS large_height, 'ipdb' AS "source" FROM ipdb_machine_files AS imf INNER JOIN catalog_models AS cm ON ((imf.ipdb_id = cm.ipdb_id)));

-- catalog_people
CREATE OR REPLACE VIEW catalog_people AS WITH alias_map AS (SELECT unnest(aliases) AS alias_name, "name" AS canonical_name FROM pinbase_people), ipdb_names AS (SELECT DISTINCT COALESCE(am.canonical_name, ip."name") AS "name" FROM ipdb_people AS ip LEFT JOIN alias_map AS am ON ((ip."name" = am.alias_name))), fandom_names AS (SELECT COALESCE(am.canonical_name, fp.title) AS "name", fp.page_id AS fandom_page_id, fp.wikitext AS fandom_wikitext FROM fandom_persons AS fp LEFT JOIN alias_map AS am ON ((fp.title = am.alias_name))), all_names AS ((SELECT "name" FROM ipdb_names) UNION (SELECT "name" FROM fandom_names))SELECT a."name", f.fandom_page_id, f.fandom_wikitext, (i."name" IS NOT NULL) AS in_ipdb, (f."name" IS NOT NULL) AS in_fandom FROM all_names AS a LEFT JOIN ipdb_names AS i ON ((a."name" = i."name")) LEFT JOIN fandom_names AS f ON ((a."name" = f."name"));

-- catalog_series
CREATE OR REPLACE VIEW catalog_series AS SELECT s.slug, s."name", s.description, count(ct.opdb_group_id) AS title_count FROM pinbase_series AS s LEFT JOIN catalog_titles AS ct ON ((s.slug = ct.series_slug)) GROUP BY s.slug, s."name", s.description ORDER BY title_count DESC;

-- catalog_systems
CREATE OR REPLACE VIEW catalog_systems AS SELECT ps.slug, ps."name", ps.manufacturer_slug, count(DISTINCT COALESCE(cm.opdb_id, ('ipdb:' || CAST(cm.ipdb_id AS VARCHAR)))) AS model_count FROM pinbase_systems AS ps LEFT JOIN catalog_models AS cm ON ((ps.slug = cm.system_slug)) GROUP BY ps.slug, ps."name", ps.manufacturer_slug ORDER BY model_count DESC;

-- catalog_technology_generations
CREATE OR REPLACE VIEW catalog_technology_generations AS SELECT tg.slug, tg.title AS "name", tg.display_order, tg.description, count(DISTINCT COALESCE(cm.opdb_id, ('ipdb:' || CAST(cm.ipdb_id AS VARCHAR)))) AS model_count FROM pinbase_technology_generations AS tg LEFT JOIN catalog_models AS cm ON ((tg.slug = cm.technology_generation_slug)) GROUP BY tg.slug, tg.title, tg.display_order, tg.description ORDER BY tg.display_order;

-- catalog_themes
CREATE OR REPLACE VIEW catalog_themes AS WITH ipdb_themes AS (SELECT DISTINCT Theme AS "name" FROM ipdb_machines WHERE (Theme IS NOT NULL)), opdb_kw AS (SELECT DISTINCT keyword AS "name" FROM opdb_keywords), all_themes AS ((SELECT "name", CAST('t' AS BOOLEAN) AS in_ipdb, CAST('f' AS BOOLEAN) AS in_opdb FROM ipdb_themes) UNION ALL (SELECT "name", CAST('f' AS BOOLEAN) AS in_ipdb, CAST('t' AS BOOLEAN) AS in_opdb FROM opdb_kw))SELECT "name", bool_or(in_ipdb) AS in_ipdb, bool_or(in_opdb) AS in_opdb FROM all_themes GROUP BY "name";

-- catalog_tiers
CREATE OR REPLACE VIEW catalog_tiers AS WITH opdb AS (SELECT opdb_id, opdb_group_id, machine_id, "name", common_name, shortname, manufacture_date, ipdb_id, images, is_combo_label, 'opdb' AS "source" FROM opdb_tiers), ipdb_only AS (SELECT CAST(NULL AS VARCHAR) AS opdb_id, CAST(NULL AS VARCHAR) AS opdb_group_id, CAST(NULL AS VARCHAR) AS machine_id, im.Title AS "name", CAST(NULL AS VARCHAR) AS common_name, CAST(NULL AS VARCHAR) AS shortname, CASE  WHEN ((im.DateOfManufacture IS NOT NULL)) THEN (TRY_CAST(CAST(im.DateOfManufacture AS VARCHAR) AS DATE)) ELSE NULL END AS manufacture_date, im.IpdbId AS ipdb_id, CAST(list_value() AS STRUCT(title VARCHAR, "primary" BOOLEAN, "type" VARCHAR, urls STRUCT(medium VARCHAR, "large" VARCHAR, small VARCHAR), sizes STRUCT(medium STRUCT(width BIGINT, height BIGINT), "large" STRUCT(width BIGINT, height BIGINT), small STRUCT(width BIGINT, height BIGINT)))[]) AS images, CAST('f' AS BOOLEAN) AS is_combo_label, 'ipdb' AS "source" FROM ipdb_machines AS im LEFT JOIN opdb_machines AS om ON ((im.IpdbId = om.ipdb_id)) WHERE (om.opdb_id IS NULL)), all_tiers AS ((SELECT * FROM opdb) UNION ALL (SELECT * FROM ipdb_only))SELECT e.*, COALESCE(oe.technology_generation_slug, im.technology_generation_slug) AS technology_generation_slug, COALESCE(pm.display_type_slug, oe.display_type_slug, im.display_type_slug) AS display_type_slug, COALESCE(oe.system_slug, im.system_slug) AS system_slug FROM all_tiers AS e LEFT JOIN pinbase_models AS pm ON ((e.opdb_id = pm.opdb_id)) LEFT JOIN opdb_tiers AS oe ON ((e.opdb_id = oe.opdb_id)) LEFT JOIN ipdb_machines AS im ON ((e.ipdb_id = im.IpdbId));

-- catalog_conversions
CREATE OR REPLACE VIEW catalog_conversions AS SELECT pc.converted_opdb_id, pc.converted_name, cm_conv.manufacturer AS converted_manufacturer, cm_conv.manufacture_date AS converted_date, pc.source_opdb_id, pc.source_name, cm_src.manufacturer AS source_manufacturer, cm_src.manufacture_date AS source_date FROM pinbase_conversions AS pc LEFT JOIN catalog_models AS cm_conv ON ((pc.converted_opdb_id = cm_conv.opdb_id)) LEFT JOIN catalog_models AS cm_src ON ((pc.source_opdb_id = cm_src.opdb_id));

-- catalog_display_types
CREATE OR REPLACE VIEW catalog_display_types AS SELECT dt.slug, dt.title AS "name", dt.display_order, dt.description, count(DISTINCT COALESCE(cm.opdb_id, ('ipdb:' || CAST(cm.ipdb_id AS VARCHAR)))) AS model_count FROM pinbase_display_types AS dt LEFT JOIN catalog_models AS cm ON ((dt.slug = cm.display_type_slug)) GROUP BY dt.slug, dt.title, dt.display_order, dt.description ORDER BY dt.display_order;
