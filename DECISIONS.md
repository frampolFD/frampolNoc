# DECISIONS.md

## Customer-centric navigation

Approved.

The primary hierarchy is:

Customer → City → Suburb → Branch → WAN Link

## Explorer

Approved.

The Explorer is always visible and contains all customers.

No favourites/recent-only replacement.

## Branch navigation

Approved.

Clicking a branch immediately shows all WAN links together.

## Multi-WAN graphs

Approved.

Multiple WAN links remain visible in one vertically scrollable workspace.

This preserves the useful PRTG troubleshooting workflow.

## Live graph

Approved.

Default period is 1 hour.

Display RX, TX and Total Throughput.

## Historical periods

Approved.

1 Day, 7 Days, 1 Month, 1 Year.

## Ping

Approved.

Ping is represented by a compact status box and is clickable for details.

## Configuration

Approved.

WAN Details is read-only.

Editing occurs on a separate Edit page.

## Monitoring

Approved.

Monitoring is optional. Customers/WAN links can exist without monitoring.

## SNMP

Approved.

Real SNMP discovery is required.

Engineer selects the interface after discovery.

Never hardcode interfaces.

## SNMP metadata

Approved.

Persist discovered interface metadata where available.

## Circuit capacity

Approved.

Required for monitored WAN links and used for utilisation.

## Sustained utilisation

Approved.

Threshold and duration are configurable.

## ISP

Approved.

ISP is a reusable entity with support/NOC/portal/escalation information.

## WAN naming

Approved.

Names are generated from structured fields.

Example:

PCD - Harare - New Ardbennie - FortiGate 100F - Frampol LTZ - (169.239.24.126) - 100Mbps

## Branch GPS

Approved.

Latitude and longitude are required during branch onboarding.

## Version 1 scope

Approved.

Keep WAN monitoring tight. Broader network documentation is future work.
