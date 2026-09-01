"""shared geographic reference model for cities and suburbs

Cities/suburbs stop being customer-owned and become shared reference data.
This migration:

1. Adds province/country_code/latitude/longitude to cities (nullable at
   first).
2. Backfills existing city rows' province/lat/lng by matching them
   case-insensitively against the embedded Zimbabwe seed dataset. A city
   that can't be matched is preserved (never deleted) with province
   "Unknown" rather than being dropped.
3. Deduplicates cities that were previously created once per customer
   (same country_code+province+name), reassigning branches and suburbs
   off the duplicates onto one canonical row before deleting the
   duplicates.
4. Deduplicates suburbs that end up sharing a (city_id, name) after the
   city dedup above, reassigning branches off the duplicates first.
5. Makes province NOT NULL, drops cities.customer_id and its old unique
   constraint, adds the new (country_code, province, name) constraint.
6. Idempotently inserts the remaining Zimbabwe localities from the seed
   dataset that don't already exist.

See DATA_SOURCES.md for the seed dataset's origin, filter and licensing.

Revision ID: 8610f8c7c2c6
Revises: 259ebaf4072a
Create Date: 2026-09-01 16:50:35.698304

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8610f8c7c2c6'
down_revision: Union[str, None] = '259ebaf4072a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Filtered from dr5hn/countries-states-cities-database, commit
# b3b49250ff3906f6119e16c088c0053a2c972926,
# contributions/cities/ZW.json — records with type in
# {city, adm1, capital, section}, excluding type "district". 66 records.
ZW_SEED_CITIES = [
    {"name": 'Bulawayo', "province": 'Bulawayo', "country_code": 'ZW', "latitude": -20.15, "longitude": 28.58333},
    {"name": 'Chitungwiza', "province": 'Harare', "country_code": 'ZW', "latitude": -18.01274, "longitude": 31.07555},
    {"name": 'Epworth', "province": 'Harare', "country_code": 'ZW', "latitude": -17.89, "longitude": 31.1475},
    {"name": 'Harare', "province": 'Harare', "country_code": 'ZW', "latitude": -17.82772, "longitude": 31.05337},
    {"name": 'Chimanimani', "province": 'Manicaland', "country_code": 'ZW', "latitude": -19.8, "longitude": 32.86667},
    {"name": 'Chipinge', "province": 'Manicaland', "country_code": 'ZW', "latitude": -20.18833, "longitude": 32.62365},
    {"name": 'Dorowa Mining Lease', "province": 'Manicaland', "country_code": 'ZW', "latitude": -19.06667, "longitude": 31.75},
    {"name": 'Headlands', "province": 'Manicaland', "country_code": 'ZW', "latitude": -18.27733, "longitude": 32.0515},
    {"name": 'Mutare', "province": 'Manicaland', "country_code": 'ZW', "latitude": -18.9707, "longitude": 32.67086},
    {"name": 'Nyanga', "province": 'Manicaland', "country_code": 'ZW', "latitude": -18.21667, "longitude": 32.75},
    {"name": 'Nyazura', "province": 'Manicaland', "country_code": 'ZW', "latitude": -18.70587, "longitude": 32.16796},
    {"name": 'Odzi', "province": 'Manicaland', "country_code": 'ZW', "latitude": -18.96167, "longitude": 32.40557},
    {"name": 'Penhalonga', "province": 'Manicaland', "country_code": 'ZW', "latitude": -18.89112, "longitude": 32.69781},
    {"name": 'Rusape', "province": 'Manicaland', "country_code": 'ZW', "latitude": -18.52785, "longitude": 32.12843},
    {"name": 'Bindura', "province": 'Mashonaland Central', "country_code": 'ZW', "latitude": -17.30192, "longitude": 31.33056},
    {"name": 'Centenary', "province": 'Mashonaland Central', "country_code": 'ZW', "latitude": -16.72289, "longitude": 31.11462},
    {"name": 'Concession', "province": 'Mashonaland Central', "country_code": 'ZW', "latitude": -17.38333, "longitude": 30.95},
    {"name": 'Glendale', "province": 'Mashonaland Central', "country_code": 'ZW', "latitude": -17.35514, "longitude": 31.06718},
    {"name": 'Mazowe', "province": 'Mashonaland Central', "country_code": 'ZW', "latitude": -17.50404, "longitude": 30.97388},
    {"name": 'Mount Darwin', "province": 'Mashonaland Central', "country_code": 'ZW', "latitude": -16.77251, "longitude": 31.58381},
    {"name": 'Mvurwi', "province": 'Mashonaland Central', "country_code": 'ZW', "latitude": -17.03333, "longitude": 30.85},
    {"name": 'Shamva', "province": 'Mashonaland Central', "country_code": 'ZW', "latitude": -17.31159, "longitude": 31.57561},
    {"name": 'Beatrice', "province": 'Mashonaland East', "country_code": 'ZW', "latitude": -18.25283, "longitude": 30.8473},
    {"name": 'Chivhu', "province": 'Mashonaland East', "country_code": 'ZW', "latitude": -19.02112, "longitude": 30.89218},
    {"name": 'Macheke', "province": 'Mashonaland East', "country_code": 'ZW', "latitude": -18.13901, "longitude": 31.84933},
    {"name": 'Marondera', "province": 'Mashonaland East', "country_code": 'ZW', "latitude": -18.18527, "longitude": 31.55193},
    {"name": 'Murehwa', "province": 'Mashonaland East', "country_code": 'ZW', "latitude": -17.64322, "longitude": 31.784},
    {"name": 'Mutoko', "province": 'Mashonaland East', "country_code": 'ZW', "latitude": -17.39699, "longitude": 32.22677},
    {"name": 'Ruwa', "province": 'Mashonaland East', "country_code": 'ZW', "latitude": -17.88972, "longitude": 31.24472},
    {"name": 'Banket', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -17.38333, "longitude": 30.4},
    {"name": 'Chakari', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -18.06294, "longitude": 29.89246},
    {"name": 'Chegutu', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -18.13021, "longitude": 30.14074},
    {"name": 'Chinhoyi', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -17.36667, "longitude": 30.2},
    {"name": 'Chirundu', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -16.03333, "longitude": 28.85},
    {"name": 'Kadoma', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -18.33328, "longitude": 29.91534},
    {"name": 'Kariba', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -16.51667, "longitude": 28.8},
    {"name": 'Karoi', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -16.80993, "longitude": 29.69247},
    {"name": 'Mhangura', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -16.89387, "longitude": 30.16828},
    {"name": 'Norton', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -17.88333, "longitude": 30.7},
    {"name": 'Raffingora', "province": 'Mashonaland West', "country_code": 'ZW', "latitude": -17.03333, "longitude": 30.43333},
    {"name": 'Chiredzi', "province": 'Masvingo', "country_code": 'ZW', "latitude": -21.05, "longitude": 31.66667},
    {"name": 'Mashava', "province": 'Masvingo', "country_code": 'ZW', "latitude": -20.03665, "longitude": 30.48225},
    {"name": 'Masvingo', "province": 'Masvingo', "country_code": 'ZW', "latitude": -20.06373, "longitude": 30.82766},
    {"name": 'Zvishavane', "province": 'Masvingo', "country_code": 'ZW', "latitude": -20.32674, "longitude": 30.06648},
    {"name": 'Binga', "province": 'Matabeleland North', "country_code": 'ZW', "latitude": -17.62027, "longitude": 27.34139},
    {"name": 'Dete', "province": 'Matabeleland North', "country_code": 'ZW', "latitude": -18.61667, "longitude": 26.86667},
    {"name": 'Hwange', "province": 'Matabeleland North', "country_code": 'ZW', "latitude": -18.36446, "longitude": 26.49877},
    {"name": 'Inyati', "province": 'Matabeleland North', "country_code": 'ZW', "latitude": -19.67563, "longitude": 28.84687},
    {"name": 'Kamativi Mine', "province": 'Matabeleland North', "country_code": 'ZW', "latitude": -18.31563, "longitude": 27.05729},
    {"name": 'Lupane', "province": 'Matabeleland North', "country_code": 'ZW', "latitude": -18.93149, "longitude": 27.80696},
    {"name": 'Victoria Falls', "province": 'Matabeleland North', "country_code": 'ZW', "latitude": -17.93285, "longitude": 25.83066},
    {"name": 'Beitbridge', "province": 'Matabeleland South', "country_code": 'ZW', "latitude": -22.21667, "longitude": 30.0},
    {"name": 'Esigodini', "province": 'Matabeleland South', "country_code": 'ZW', "latitude": -20.28979, "longitude": 28.92261},
    {"name": 'Filabusi', "province": 'Matabeleland South', "country_code": 'ZW', "latitude": -20.53333, "longitude": 29.28502},
    {"name": 'Gwanda', "province": 'Matabeleland South', "country_code": 'ZW', "latitude": -20.93622, "longitude": 29.00698},
    {"name": 'Insiza', "province": 'Matabeleland South', "country_code": 'ZW', "latitude": -19.78333, "longitude": 29.2},
    {"name": 'Matobo', "province": 'Matabeleland South', "country_code": 'ZW', "latitude": -20.95545, "longitude": 28.49463},
    {"name": 'Plumtree', "province": 'Matabeleland South', "country_code": 'ZW', "latitude": -20.48333, "longitude": 27.81667},
    {"name": 'Gokwe', "province": 'Midlands', "country_code": 'ZW', "latitude": -18.20476, "longitude": 28.9349},
    {"name": 'Gweru', "province": 'Midlands', "country_code": 'ZW', "latitude": -19.45, "longitude": 29.81667},
    {"name": 'Kwekwe', "province": 'Midlands', "country_code": 'ZW', "latitude": -18.92809, "longitude": 29.81486},
    {"name": 'Lalapanzi', "province": 'Midlands', "country_code": 'ZW', "latitude": -19.33225, "longitude": 30.17768},
    {"name": 'Mvuma', "province": 'Midlands', "country_code": 'ZW', "latitude": -19.27924, "longitude": 30.52828},
    {"name": 'Redcliff', "province": 'Midlands', "country_code": 'ZW', "latitude": -19.03333, "longitude": 29.78333},
    {"name": 'Shangani', "province": 'Midlands', "country_code": 'ZW', "latitude": -19.78333, "longitude": 29.36667},
    {"name": 'Shurugwi', "province": 'Midlands', "country_code": 'ZW', "latitude": -19.67016, "longitude": 30.00589},
]


def _norm(s: str) -> str:
    return s.strip().lower()


def upgrade() -> None:
    bind = op.get_bind()

    # --- Step 1: add new columns to cities, nullable for now ---
    with op.batch_alter_table('cities', schema=None) as batch_op:
        batch_op.add_column(sa.Column('province', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('country_code', sa.String(length=2), nullable=False, server_default='ZW'))
        batch_op.add_column(sa.Column('latitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('longitude', sa.Float(), nullable=True))

    cities_t = sa.table(
        'cities',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('province', sa.String),
        sa.column('country_code', sa.String),
        sa.column('latitude', sa.Float),
        sa.column('longitude', sa.Float),
    )
    suburbs_t = sa.table(
        'suburbs',
        sa.column('id', sa.Integer),
        sa.column('city_id', sa.Integer),
        sa.column('name', sa.String),
    )
    branches_t = sa.table(
        'branches',
        sa.column('id', sa.Integer),
        sa.column('city_id', sa.Integer),
        sa.column('suburb_id', sa.Integer),
    )

    # --- Step 2: backfill province/lat/lng on existing (pre-migration)
    # city rows by matching them case-insensitively against the seed
    # dataset. A city that can't be matched is preserved rather than
    # dropped, flagged with province "Unknown".
    seed_by_name = {_norm(r['name']): r for r in ZW_SEED_CITIES}
    existing_cities = list(bind.execute(sa.select(cities_t.c.id, cities_t.c.name)))
    for row in existing_cities:
        match = seed_by_name.get(_norm(row.name))
        if match:
            bind.execute(
                cities_t.update()
                .where(cities_t.c.id == row.id)
                .values(province=match['province'], latitude=match['latitude'], longitude=match['longitude'])
            )
        else:
            bind.execute(cities_t.update().where(cities_t.c.id == row.id).values(province='Unknown'))

    # --- Step 3: deduplicate cities previously created once per customer,
    # keyed on (country_code, province, name) case-insensitive. Reassign
    # branches and suburbs off the duplicates onto one canonical row
    # *before* deleting the duplicates, so no branch/suburb is ever left
    # pointing at a row that's about to disappear.
    #
    # The suburbs (city_id, name) unique constraint is dropped first: two
    # suburbs with the same name that previously lived under two different
    # per-customer copies of "the same" city will collide the instant they
    # both point at one canonical city_id, and that collision has to be
    # resolved by the dedup in step 4 — which can't run until step 3's
    # reassignment UPDATE has actually been allowed to complete.
    with op.batch_alter_table('suburbs', schema=None) as batch_op:
        batch_op.drop_constraint('uq_suburb_city_name', type_='unique')

    all_cities = list(
        bind.execute(sa.select(cities_t.c.id, cities_t.c.name, cities_t.c.province, cities_t.c.country_code))
    )
    city_groups: dict[tuple[str, str, str], list[int]] = {}
    for row in all_cities:
        key = (_norm(row.country_code), _norm(row.province), _norm(row.name))
        city_groups.setdefault(key, []).append(row.id)

    for ids in city_groups.values():
        if len(ids) <= 1:
            continue
        canonical_id = min(ids)
        duplicate_ids = [i for i in ids if i != canonical_id]
        bind.execute(branches_t.update().where(branches_t.c.city_id.in_(duplicate_ids)).values(city_id=canonical_id))
        bind.execute(suburbs_t.update().where(suburbs_t.c.city_id.in_(duplicate_ids)).values(city_id=canonical_id))
        bind.execute(cities_t.delete().where(cities_t.c.id.in_(duplicate_ids)))

    # --- Step 4: deduplicate suburbs that now collide on (city_id, name)
    # as a result of step 3's city merges. Reassign branch.suburb_id off
    # the duplicates before deleting them, then restore the uniqueness
    # constraint now that no duplicates remain.
    all_suburbs = list(bind.execute(sa.select(suburbs_t.c.id, suburbs_t.c.city_id, suburbs_t.c.name)))
    suburb_groups: dict[tuple[int, str], list[int]] = {}
    for row in all_suburbs:
        key = (row.city_id, _norm(row.name))
        suburb_groups.setdefault(key, []).append(row.id)

    for ids in suburb_groups.values():
        if len(ids) <= 1:
            continue
        canonical_id = min(ids)
        duplicate_ids = [i for i in ids if i != canonical_id]
        bind.execute(branches_t.update().where(branches_t.c.suburb_id.in_(duplicate_ids)).values(suburb_id=canonical_id))
        bind.execute(suburbs_t.delete().where(suburbs_t.c.id.in_(duplicate_ids)))

    with op.batch_alter_table('suburbs', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_suburb_city_name', ['city_id', 'name'])

    # --- Step 5: province is now populated on every row -> enforce
    # NOT NULL; drop customer_id (and its FK/unique constraint) now that
    # every branch reference has been safely repointed; add the new
    # shared-city uniqueness constraint.
    with op.batch_alter_table('cities', schema=None) as batch_op:
        batch_op.alter_column('province', existing_type=sa.String(length=200), nullable=False)
        batch_op.drop_constraint('uq_city_customer_name', type_='unique')
        # No explicit FK drop needed: batch mode recreates the table from
        # the surviving column list, so dropping customer_id here already
        # excludes the FK that referenced it — an explicit
        # drop_constraint(None, type_='foreignkey') fails in this Alembic
        # version because an unnamed constraint has nothing to match on.
        batch_op.drop_column('customer_id')
        batch_op.create_unique_constraint('uq_city_country_province_name', ['country_code', 'province', 'name'])

    # --- Step 6: idempotently insert the remaining Zimbabwe localities
    # that don't already exist (e.g. from step 2/3 matching a
    # pre-existing customer city onto the same seed record).
    existing_keys = {
        (_norm(row.country_code), _norm(row.province), _norm(row.name))
        for row in bind.execute(sa.select(cities_t.c.country_code, cities_t.c.province, cities_t.c.name))
    }
    for rec in ZW_SEED_CITIES:
        key = (_norm(rec['country_code']), _norm(rec['province']), _norm(rec['name']))
        if key in existing_keys:
            continue
        bind.execute(
            cities_t.insert().values(
                name=rec['name'],
                province=rec['province'],
                country_code=rec['country_code'],
                latitude=rec['latitude'],
                longitude=rec['longitude'],
            )
        )
        existing_keys.add(key)


def downgrade() -> None:
    # The dedup/merge performed in upgrade() is not reversible (customer
    # attribution of a shared city is gone); this restores the column
    # shape only, re-adding a nullable customer_id for schema compatibility.
    with op.batch_alter_table('cities', schema=None) as batch_op:
        batch_op.add_column(sa.Column('customer_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'customers', ['customer_id'], ['id'])
        batch_op.drop_constraint('uq_city_country_province_name', type_='unique')
        batch_op.create_unique_constraint('uq_city_customer_name', ['customer_id', 'name'])
        batch_op.drop_column('longitude')
        batch_op.drop_column('latitude')
        batch_op.drop_column('country_code')
        batch_op.drop_column('province')
