"""Runs the actual shared-geographic-model migration against a throwaway
SQLite file seeded with the exact duplicate-city/duplicate-suburb scenario
this project hit in practice (two customers, each with their own "Harare"
city and "Highlands" suburb, one branch and one WAN link depending on one
of them) — and proves the migration preserves every reference correctly."""

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

import app.config


def _run_alembic_upgrade(db_path: Path, revision: str, monkeypatch):
    # alembic/env.py always does
    # `config.set_main_option("sqlalchemy.url", settings.database_url)`,
    # so the only way to point a real `alembic upgrade` invocation at a
    # throwaway database is to patch the settings object it reads from —
    # not the Alembic Config passed in here.
    monkeypatch.setattr(app.config.settings, "database_url", f"sqlite:///{db_path}")
    project_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "alembic"))
    command.upgrade(cfg, revision)


def test_migration_preserves_branch_suburb_and_wan_link_through_dedup(tmp_path, monkeypatch):
    db_path = tmp_path / "migration_test.db"

    # Build the pre-migration schema (everything up to, but not including,
    # the shared-geographic-model migration).
    _run_alembic_upgrade(db_path, "259ebaf4072a", monkeypatch)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Two customers, each with their own duplicate "Harare" city and
    # "Highlands" suburb — exactly the real-world scenario this migration
    # exists to fix.
    cur.execute("INSERT INTO customers (id, name, status) VALUES (1, 'Customer A', 'active')")
    cur.execute("INSERT INTO customers (id, name, status) VALUES (2, 'Customer B', 'active')")
    cur.execute("INSERT INTO cities (id, customer_id, name) VALUES (1, 1, 'Harare')")
    cur.execute("INSERT INTO cities (id, customer_id, name) VALUES (2, 2, 'Harare')")
    cur.execute("INSERT INTO suburbs (id, city_id, name) VALUES (1, 1, 'Highlands')")
    cur.execute("INSERT INTO suburbs (id, city_id, name) VALUES (2, 2, 'Highlands')")
    # Only Customer B's copies are actually referenced by a branch.
    cur.execute(
        "INSERT INTO branches (id, customer_id, city_id, suburb_id, name, latitude, longitude) "
        "VALUES (1, 2, 2, 2, 'Head Office', -17.8, 31.0)"
    )
    cur.execute(
        "INSERT INTO wan_links "
        "(id, branch_id, name_generated, role, icmp_enabled, snmp_enabled, monitoring_status, monitoring_disabled, "
        "sustained_util_threshold_percent, sustained_util_duration_seconds) "
        "VALUES (1, 1, 'Test WAN', 'primary', 0, 0, 'not_configured', 0, 90.0, 600)"
    )
    cur.execute(
        "INSERT INTO measurements (id, wan_link_id, latency_ms, availability) VALUES (1, 1, 12.5, 1)"
    )
    conn.commit()
    conn.close()

    # Apply the migration under test.
    _run_alembic_upgrade(db_path, "8610f8c7c2c6", monkeypatch)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM cities WHERE name = 'Harare'")
    assert cur.fetchone()[0] == 1, "duplicate per-customer Harare rows must be merged into one"

    cur.execute("SELECT COUNT(*) FROM suburbs WHERE name = 'Highlands'")
    assert cur.fetchone()[0] == 1, "duplicate per-customer Highlands rows must be merged into one"

    cur.execute("SELECT city_id, suburb_id FROM branches WHERE id = 1")
    branch_city_id, branch_suburb_id = cur.fetchone()
    assert branch_city_id is not None and branch_suburb_id is not None

    cur.execute("SELECT id FROM cities WHERE name = 'Harare'")
    (canonical_city_id,) = cur.fetchone()
    cur.execute("SELECT id FROM suburbs WHERE name = 'Highlands'")
    (canonical_suburb_id,) = cur.fetchone()
    assert branch_city_id == canonical_city_id, "branch must be repointed to the surviving city row"
    assert branch_suburb_id == canonical_suburb_id, "branch must be repointed to the surviving suburb row"

    # The WAN link and its measurement history must be completely untouched.
    cur.execute("SELECT branch_id, name_generated FROM wan_links WHERE id = 1")
    assert cur.fetchone() == (1, "Test WAN")
    cur.execute("SELECT wan_link_id, latency_ms FROM measurements WHERE id = 1")
    assert cur.fetchone() == (1, 12.5)

    # And the full Zimbabwe preload landed alongside the migrated data.
    cur.execute("SELECT COUNT(*) FROM cities")
    assert cur.fetchone()[0] == 66

    conn.close()
