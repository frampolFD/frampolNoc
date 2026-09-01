# ROADMAP.md

## MVP — Working WAN Monitor

Priority: NOW

The MVP must demonstrate a complete real monitoring workflow.

### Phase 1 — Application foundation

- Backend
- Frontend
- PostgreSQL
- Docker
- Environment configuration
- Authentication
- Basic layout
- Explorer
- Dashboard

### Phase 2 — Inventory

- Customer
- City
- Suburb
- Branch
- Required GPS coordinates
- ISP records
- WAN Link

### Phase 3 — Real ICMP

- ICMP worker
- 30-second polling
- latency
- packet loss
- availability
- jitter
- status engine

### Phase 4 — Real SNMP

- SNMP credential handling
- SNMP target
- real interface discovery
- interface selection
- ifIndex persistence
- interface metadata
- 60-second polling
- high-capacity counters
- RX/TX calculation
- total throughput
- utilisation

### Phase 5 — Graphs

- 1-hour live graph
- 1 Day
- 7 Days
- 1 Month
- 1 Year
- RX/TX/Total
- latency
- packet loss
- availability
- consumption

### Phase 6 — Branch WAN Overview

- customer path header
- multiple WANs vertically
- live graphs
- ISP badges
- health indicators
- quick actions
- synchronized graph hover

### Phase 7 — Alerts

- down
- recovery
- latency
- packet loss
- sustained utilisation
- configurable threshold/duration

### Phase 8 — Operational polish

- engineer notes
- generated WAN names
- report basics
- error handling
- audit/logging
- backup strategy

## MVP acceptance test

A demonstrable MVP must allow an engineer to:

1. Create a customer.
2. Create a branch.
3. Add a WAN link.
4. Enter SNMP details.
5. Discover real SNMP interfaces.
6. Select the WAN interface.
7. Start SNMP polling.
8. See real RX/TX/Total traffic.
9. See utilisation based on circuit capacity.
10. See a 1-hour graph.
11. Configure ICMP.
12. See latency/loss/availability.
13. See the WAN inside the Branch WAN Overview.
14. Trigger/test an alert.

## Version 2 parking

- Microsoft Entra ID
- topology
- IPAM
- printer inventory
- switch inventory
- switch-port documentation
- server monitoring
- FortiGate API
- Cisco API
- SD-WAN awareness
- NetFlow
- Syslog
- customer portal
- mobile app
- AI assistance
