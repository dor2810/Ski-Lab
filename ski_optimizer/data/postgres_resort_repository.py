"""
[PHASE 8 — not implemented yet]

Will implement the same load_resorts() -> List[Resort] interface as
resort_repository.py, backed by the Postgres SkiResort table (see
db/models.py) instead of the xlsx. Nothing outside this file needs to
change when this lands -- engine/ and cli/ only ever import
`load_resorts`, never the module it comes from.

seed_importer.py (also this phase) does the one-time migration:
reads data/ski_resort_database_seed.xlsx -> writes Postgres rows.
"""
raise NotImplementedError(
    "Postgres-backed resort repository is planned for Phase 8. "
    "Use resort_repository.load_resorts() (xlsx-backed) until then."
)
