# CLAUDE.md — Frampol NOC Build Instructions

You are building Frampol NOC.

Read these files before coding:

- README.md
- PROJECT.md
- FEATURES.md
- UI_DESIGN.md
- DATABASE_DESIGN.md
- ROADMAP.md
- DECISIONS.md
- TERMINOLOGY.md
- PARKING_LOT.md

These documents are the project source of truth.

## Immediate objective

Build a demonstrable MVP with REAL ICMP and REAL SNMP.

Do not build an ICMP-only prototype.

Do not fake SNMP data.

Do not hardcode interface lists.

The application must perform real SNMP discovery and real SNMP polling.

## First demonstrable workflow

Customer
→ City
→ Suburb
→ Branch
→ WAN Link
→ SNMP Target
→ Discover Interfaces
→ Select Interface
→ Poll
→ Calculate RX/TX/Total
→ Calculate utilisation
→ Store measurements
→ Display 1-hour graph
→ ICMP latency/loss/availability
→ Branch WAN Overview

## SNMP requirements

Use a mature Python SNMP library.

Support at least SNMP v2c for MVP.

Structure the monitoring code so SNMP v3 can be added later.

Use environment/configuration mechanisms for secrets.

Never expose SNMP communities/secrets in frontend bundles, logs or error messages.

Interface discovery must query the target.

Where practical, use standard IF-MIB objects and high-capacity counters:

- ifIndex
- ifName
- ifDescr
- ifAlias
- ifHCInOctets
- ifHCOutOctets
- ifSpeed
- ifAdminStatus
- ifOperStatus
- ifPhysAddress

Discover interface IP addresses where supported by the device.

The engineer must select the interface.

If an IP match is found, highlight/suggest it but do not silently select it.

Store the selected ifIndex. Poll by stable identifier where possible rather than relying only on interface name.

## Traffic calculation

SNMP octet counters are cumulative.

Do not display cumulative octets as Mbps.

Calculate rate from counter deltas:

delta_octets = current_counter - previous_counter

bps = delta_octets * 8 / elapsed_seconds

Handle counter resets/wraps safely.

Total throughput:

RX bps + TX bps

Utilisation:

total throughput / circuit capacity × 100

Use 64-bit counters where available.

## Polling architecture

SNMP and ICMP polling must run outside HTTP request handlers.

Use a background worker/scheduler architecture.

A failed/unreachable device must not block the API or other monitored links.

Implement per-target timeouts and retries.

Prevent overlapping polls for the same target.

Record poll timestamps.

## Data retention

Store raw/derived measurements needed for the graph and consumption calculations.

Design the storage so it can scale beyond the MVP.

Do not prematurely build an elaborate distributed time-series architecture.

## ICMP

Default interval: 30 seconds.

Collect:

- latency
- packet loss
- availability
- jitter

## SNMP

Default interval: 60 seconds.

Collect traffic and interface health.

## UI

Preserve the PRTG-style workflow:

Customer
→ location
→ branch
→ all WAN links together

Do not force engineers to open each WAN in a separate page to compare links.

Branch WAN Overview uses vertical scrolling.

Each WAN has:

- ISP
- health
- circuit capacity
- current RX
- current TX
- total throughput
- utilisation
- latency
- packet loss
- ping box
- 1-hour graph
- quick actions

## Graph

Default live range: 1 hour.

Display:

- RX
- TX
- Total

Historical ranges:

- 1 Day
- 7 Days
- 1 Month
- 1 Year

Use a reliable chart library.

## Alert

Implement:

- down
- recovery
- high latency
- packet loss
- sustained utilisation

Sustained utilisation must have configurable:

- threshold %
- duration

Example: 90% for 10 minutes.

## Naming

Generate WAN names from structured data.

Do not ask engineers to type the full sensor name.

Example:

PCD - Harare - New Ardbennie - FortiGate 100F - Frampol LTZ - (169.239.24.126) - 100Mbps

## Code quality

- Keep modules small.
- Use typed schemas/models.
- Validate input.
- Use migrations.
- Write tests for traffic calculations and alert logic.
- Do not duplicate monitoring logic.
- Do not hardcode customer data.
- Do not hardcode SNMP interfaces.
- Do not add unnecessary dependencies.

## Development behaviour

Before a major implementation step, briefly state what you will build.

Then build it.

Do not stop every few minutes asking for permission.

The user needs a working MVP today.

If a decision is genuinely ambiguous and blocks implementation, ask one concise question.

Otherwise use the documented decisions.

## Scope discipline

Do NOT implement:

- topology
- IPAM
- printers
- switches
- switch ports
- server monitoring
- NetFlow
- Syslog
- SD-WAN awareness
- FortiGate API
- customer portal
- AI features

Those are future work.

## Demo mode

The product must support a real monitoring setup.

If no SNMP target is available during development, create a clearly separated development/test adapter or simulator for automated tests.

Do not present simulated data as real production monitoring.

## Definition of done for the MVP

A real SNMP-capable WAN can be onboarded.

The application can discover interfaces.

An engineer can select an interface.

The worker polls it.

RX/TX/total/utilisation are calculated.

Measurements are stored.

The 1-hour graph updates.

ICMP status is visible.

The branch can display multiple WAN links.

At least one alert can be demonstrated.

The application can be run from documented startup commands.
