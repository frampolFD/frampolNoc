# DATA_SOURCES.md

External datasets embedded in this project's source or migrations.

## Zimbabwe cities/towns preload

- **Dataset**: `dr5hn/countries-states-cities-database`
- **Source repository**: https://github.com/dr5hn/countries-states-cities-database
- **Pinned commit**: `b3b49250ff3906f6119e16c088c0053a2c972926`
- **File**: `contributions/cities/ZW.json`
- **Source URL**: https://github.com/dr5hn/countries-states-cities-database/blob/b3b49250ff3906f6119e16c088c0053a2c972926/contributions/cities/ZW.json
- **Filter applied**: records where `type` is one of `city`, `adm1`, `capital`, `section`; records with `type` = `district` excluded. This produced 66 records.
- **Fields persisted**: `name`, `province` (mapped from the dataset's `state_code` — see below), `country_code` (`ZW`), `latitude`, `longitude`. All other fields in the source dataset (population, timezone, translations, etc.) were discarded.
- **State code → province mapping used**:

  | Code | Province |
  |------|----------|
  | BU | Bulawayo |
  | HA | Harare |
  | MA | Manicaland |
  | MC | Mashonaland Central |
  | ME | Mashonaland East |
  | MW | Mashonaland West |
  | MN | Matabeleland North |
  | MS | Matabeleland South |
  | MV | Masvingo |
  | MI | Midlands |

- **License**: Open Database License (ODbL) v1.0. Per ODbL Section 4.3 (Attribution), this notice constitutes attribution for the data derived from the above source.
- **Date imported**: 2026-09-01, via Alembic migration `8610f8c7c2c6` (`shared geographic reference model for cities and suburbs`). The dataset is embedded directly in that migration file as a Python literal — it is not fetched at install or application-startup time, so installation stays deterministic and works offline.
