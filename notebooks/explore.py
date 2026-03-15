import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Pinbase Data Explorer

        Browse the curated pinball machine catalog — titles, models,
        manufacturers, and people — loaded from `data/*.json` via DuckDB.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import duckdb
    from pathlib import Path

    # Connect to an in-memory DuckDB and load all curated JSON files.
    db = duckdb.connect()

    # Load each curated JSON file as a view.
    _json_views = {
        "cabinets": {},
        "corporate_entities": {},
        "credit_roles": {},
        "credits": {"union_by_name": True},
        "display_subtypes": {},
        "display_types": {},
        "franchises": {},
        "game_formats": {},
        "gameplay_features": {},
        "manufacturers": {},
        "models": {"union_by_name": True},
        "people": {"union_by_name": True},
        "series": {},
        "systems": {},
        "tags": {},
        "technology_generations": {},
        "technology_subgenerations": {},
        "titles": {"union_by_name": True},
    }

    for name, opts in _json_views.items():
        path = f"data/{name}.json"
        if not Path(path).exists():
            continue
        ubn = "(union_by_name = CAST('t' AS BOOLEAN))" if opts.get("union_by_name") else ""
        params = f", {ubn}" if ubn else ""
        db.execute(
            f"CREATE OR REPLACE VIEW pinbase_{name} AS "
            f"SELECT * FROM read_json_auto('{path}'{params})"
        )

    # Summary counts
    _counts = {}
    for name in _json_views:
        try:
            _counts[name] = db.execute(
                f"SELECT count(*) FROM pinbase_{name}"
            ).fetchone()[0]
        except Exception:
            pass

    _summary = " | ".join(f"**{v}** {k}" for k, v in _counts.items() if v > 0)
    mo.md(f"Loaded: {_summary}")
    return (db,)


@app.cell
def _(mo):
    # Tab selector for the main entity types.
    tabs = mo.ui.tabs(
        {
            "Titles & Models": "titles",
            "Manufacturers": "manufacturers",
            "People": "people",
            "Taxonomy": "taxonomy",
        }
    )
    tabs
    return (tabs,)


# -------------------------------------------------------------------
# Titles & Models tab
# -------------------------------------------------------------------


@app.cell
def _(db, mo, tabs):
    mo.stop(tabs.value != "titles")

    # Dropdown of all titles, sorted by name.
    _titles = db.execute(
        "SELECT slug, name FROM pinbase_titles ORDER BY name"
    ).fetchall()
    _options = {f"{name} ({slug})": slug for slug, name in _titles}

    title_picker = mo.ui.dropdown(
        options=_options,
        label="Pick a title",
    )
    title_picker
    return (title_picker,)


@app.cell
def _(db, mo, title_picker):
    import polars as pl

    mo.stop(title_picker.value is None)

    _slug = title_picker.value

    # Title details
    _title_row = db.execute(
        "SELECT * FROM pinbase_titles WHERE slug = ?", [_slug]
    ).pl()

    # Models for this title
    _models = db.execute(
        "SELECT * FROM pinbase_models WHERE title = ? ORDER BY name",
        [_slug],
    ).pl()

    mo.vstack([
        mo.md(f"### Title: {_title_row['name'][0]}"),
        mo.md("**Title record:**"),
        mo.ui.table(_title_row),
        mo.md(f"**Models ({len(_models)}):**"),
        mo.ui.table(_models) if len(_models) > 0 else mo.md("_No models curated yet._"),
    ])
    return


# -------------------------------------------------------------------
# Manufacturers tab
# -------------------------------------------------------------------


@app.cell
def _(db, mo, tabs):
    mo.stop(tabs.value != "manufacturers")

    _mfrs = db.execute(
        "SELECT slug, name FROM pinbase_manufacturers ORDER BY name"
    ).fetchall()
    _options = {f"{name} ({slug})": slug for slug, name in _mfrs}

    mfr_picker = mo.ui.dropdown(options=_options, label="Pick a manufacturer")
    mfr_picker
    return (mfr_picker,)


@app.cell
def _(db, mo, mfr_picker):
    mo.stop(mfr_picker.value is None)

    _slug = mfr_picker.value

    _mfr = db.execute(
        "SELECT * FROM pinbase_manufacturers WHERE slug = ?", [_slug]
    ).pl()

    # Corporate entities for this manufacturer
    _entities = db.execute(
        "SELECT * FROM pinbase_corporate_entities WHERE manufacturer_slug = ? ORDER BY year_start",
        [_slug],
    ).pl()

    mo.vstack([
        mo.md(f"### Manufacturer: {_mfr['name'][0]}"),
        mo.ui.table(_mfr),
        mo.md(f"**Corporate entities ({len(_entities)}):**"),
        mo.ui.table(_entities) if len(_entities) > 0 else mo.md("_None._"),
    ])
    return


# -------------------------------------------------------------------
# People tab
# -------------------------------------------------------------------


@app.cell
def _(db, mo, tabs):
    mo.stop(tabs.value != "people")

    _people = db.execute(
        "SELECT slug, name FROM pinbase_people ORDER BY name"
    ).fetchall()
    _options = {f"{name} ({slug})": slug for slug, name in _people}

    person_picker = mo.ui.dropdown(options=_options, label="Pick a person")
    person_picker
    return (person_picker,)


@app.cell
def _(db, mo, person_picker):
    mo.stop(person_picker.value is None)

    _slug = person_picker.value

    _person = db.execute(
        "SELECT * FROM pinbase_people WHERE slug = ?", [_slug]
    ).pl()

    # Credits involving this person
    _credits = db.execute(
        "SELECT * FROM pinbase_credits WHERE person_slug = ?", [_slug]
    ).pl()

    mo.vstack([
        mo.md(f"### Person: {_person['name'][0]}"),
        mo.ui.table(_person),
        mo.md(f"**Credits ({len(_credits)}):**"),
        mo.ui.table(_credits) if len(_credits) > 0 else mo.md("_None._"),
    ])
    return


# -------------------------------------------------------------------
# Taxonomy tab — browse the small reference tables
# -------------------------------------------------------------------


@app.cell
def _(db, mo, tabs):
    mo.stop(tabs.value != "taxonomy")

    _taxonomy_tables = [
        ("Technology Generations", "pinbase_technology_generations"),
        ("Technology Subgenerations", "pinbase_technology_subgenerations"),
        ("Display Types", "pinbase_display_types"),
        ("Display Subtypes", "pinbase_display_subtypes"),
        ("Cabinets", "pinbase_cabinets"),
        ("Game Formats", "pinbase_game_formats"),
        ("Gameplay Features", "pinbase_gameplay_features"),
        ("Tags", "pinbase_tags"),
        ("Franchises", "pinbase_franchises"),
        ("Series", "pinbase_series"),
        ("Systems", "pinbase_systems"),
    ]

    _sections = []
    for label, view in _taxonomy_tables:
        try:
            _df = db.execute(f"SELECT * FROM {view} ORDER BY 1").pl()
            _sections.append(mo.md(f"### {label} ({len(_df)})"))
            _sections.append(mo.ui.table(_df))
        except Exception as e:
            _sections.append(mo.md(f"### {label}\n\n_Error: {e}_"))

    mo.vstack(_sections)
    return


if __name__ == "__main__":
    app.run()
