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

Required for monitored WAN links (ICMP or SNMP enabled) and used for
utilisation. Nullable at the database level for a WAN link that is
inventory-only or not yet configured — the API rejects enabling ICMP/SNMP
without a capacity, but a link may exist with neither enabled and no
capacity set. Utilisation is left absent (not zero) when capacity is
unknown; a missing value must never be silently treated as 0%.

## Utilisation semantics

Approved (Stabilization Milestone 1).

`total_throughput = RX + TX` remains the number shown for combined
throughput/consumption — that's genuinely useful and correct as a total.

WAN utilisation, and the sustained-utilisation alert threshold, use the
busier direction instead: `max(RX, TX) / circuit_capacity`. RX and TX ride
independent channels on a full-duplex circuit, so 60 Mbps in *each*
direction on a 100 Mbps circuit is 60% utilised, not 120%. Using RX+TX for
utilisation would let a link alert as "over capacity" while each direction
still has headroom, which is misleading for engineers troubleshooting
saturation.

## Monitoring status semantics

Approved (Stabilization Milestone 1).

`not_configured` and `monitoring_disabled` are distinct states, backed by a
dedicated `monitoring_disabled` boolean column on WANLink (independent of
the `icmp_enabled`/`snmp_enabled` toggles):

- `not_configured` — the WAN exists but nobody has set up monitoring for it
  yet. The default state for a newly created link.
- `monitoring_disabled` — monitoring was deliberately turned off (e.g. the
  customer does not permit monitoring, or the link should exist purely as
  operational inventory). Set explicitly by the engineer, never inferred.

`monitoring_disabled` takes precedence over `icmp_enabled`/`snmp_enabled`
when computing the displayed status, so it can't be silently overridden by
those toggles. Both states render as the grey/"unknown" health colour per
UI_DESIGN.md — neither has a meaningful up/down signal — but they answer
different questions for an engineer scanning the Explorer ("still needs
setup" vs. "this one's deliberately hands-off").

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
