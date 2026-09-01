# Frampol NOC

Version 1.0 — MVP

Frampol NOC is a customer-centric WAN Monitoring Platform for Managed Service Providers.

The MVP focuses on real WAN monitoring using **SNMP and ICMP**, with a PRTG-inspired workflow for viewing multiple WAN links at a branch on one screen.

## Version 1 focus

- Customer and location inventory
- Customer → City/Town → Suburb/Area → Branch → WAN Link hierarchy
- WAN link onboarding
- SNMP interface discovery
- SNMP traffic monitoring
- ICMP availability monitoring
- RX / TX / Total Throughput
- Circuit-capacity utilisation
- Data consumption
- 1-hour live graphs
- 1 Day / 7 Day / 1 Month / 1 Year historical views
- WAN alerts
- Sustained-utilisation alerts
- Engineer notes
- ISP records
- Generated WAN names
- Branch WAN overview
- WAN Link Details

Monitoring is optional. A WAN link can exist even when a customer does not permit ICMP/SNMP monitoring.

## Core workflow

Customer → City → Suburb → Branch → WAN Link → Monitoring

For SNMP:

SNMP Target IP → Discover Interfaces → Engineer selects interface → Poll interface → Store counters → Calculate traffic/utilisation → Graph

## Long-term vision

Future versions may add network-device monitoring, topology, IPAM, printer inventory, switch-port documentation, FortiGate APIs, NetFlow, Syslog, customer portal and AI assistance.

These are deliberately outside Version 1.

## Running the MVP

Requires Python 3.10+. No Docker, no external database server — SQLite is
used for the MVP (see "Technology choices" below for why).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file in the project root (never commit this — it holds
secrets):

```
FRAMPOL_DATABASE_URL=sqlite:///./frampol_noc.db
FRAMPOL_SESSION_SECRET_KEY=<random string>
FRAMPOL_CREDENTIAL_KEY=<random string — encrypts SNMP community strings at rest>
FRAMPOL_ADMIN_EMAIL=admin@frampol.local
FRAMPOL_ADMIN_PASSWORD=<a real password>
```

Generate random values for the two secrets with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then set up the database and start the app:

```bash
python -m alembic upgrade head     # create/upgrade the schema
python -m app.seed                 # create the admin user + starter ISP list
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/login and sign in with the admin email/password
from `.env`. The background monitoring worker starts automatically with the
app — no separate process to launch.

Run the test suite with:

```bash
python -m pytest
```

## Technology choices

- **Backend**: FastAPI (Python), chosen for async support (needed so slow
  SNMP/ICMP polling never blocks the API) and a mature ecosystem.
- **Database**: SQLite via SQLAlchemy + Alembic migrations for the MVP —
  zero setup, works immediately without Docker or a database server.
  SQLAlchemy makes moving to PostgreSQL later a connection-string change,
  not a rewrite, once the platform needs concurrent multi-process access.
- **SNMP**: `pysnmp` (classic synchronous hlapi), used for real IF-MIB/IP-MIB
  discovery and Counter32/Counter64 polling over SNMP v2c. Structured so
  SNMP v3 (`UsmUserData`) can be added by extending one function
  (`app/monitoring/snmp_client.py::_auth_data`) without touching discovery
  or polling logic.
- **ICMP**: shells out to the operating system's real `ping` utility and
  parses its output. This sends genuine ICMP echo requests without
  requiring administrator/root privileges for raw sockets, which matters
  for running this on a normal engineer's Windows machine.
- **Frontend**: server-rendered Jinja2 pages with vanilla JS and Chart.js
  (vendored locally, no CDN dependency at runtime) — chosen to ship a
  working full-stack MVP today without a separate frontend build/deploy
  pipeline. Live data flows through a small JSON API (`/api/...`) that a
  richer SPA could consume later without backend changes.
- **Background polling**: a single asyncio "tick" loop inside the FastAPI
  process (see `app/monitoring/worker.py`) checks every 5 seconds which WAN
  links are due for an ICMP (30s) or SNMP (60s) poll and fires independent,
  per-target-locked async tasks — never blocking the HTTP server, never
  overlapping the same target, and isolating one target's failure from
  every other target.
- **SNMP credential protection**: community strings are encrypted at rest
  (Fernet, key from `FRAMPOL_CREDENTIAL_KEY`) in a dedicated
  `snmp_credentials` table. The API only ever returns a credential's name
  and version — never the secret — and SNMP error messages are scrubbed to
  protocol-level detail only, so a mistyped community string never leaks
  into a browser console or log line.

## Known limitations of this MVP

- SNMP v3 is modeled in the schema but not implemented for polling yet.
- The automated test suite covers traffic-rate math, alert logic and the
  SNMP discovery *merge* logic with synthetic data (no live device
  required). It does not include a full wire-protocol SNMP agent simulator
  — that needs a real (or lab) SNMP v2c device, which is exactly what the
  live demo exercises against a FortiGate.
- Authentication is a single shared admin login for the demo; per-engineer
  accounts/roles exist in the data model but aren't yet exposed in the UI.
