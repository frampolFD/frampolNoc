# UI_DESIGN.md

## Brand

Use the marketing-approved Frampol palette:

- Grey
- Burgundy
- Black

Brand colours are separate from health colours.

Health:

- Green = healthy
- Amber/yellow = warning
- Red = critical
- Grey = unknown/monitoring disabled

## Global layout

- Fixed left Explorer
- Top navigation
- Main workspace
- Optional contextual actions
- Bottom/status information where useful

The Explorer is always visible after login.

## Explorer

All customers are shown.

Expand:

Customer → City → Suburb → Branch → WAN Link

Clicking a branch loads all WAN links in the workspace.

The arrow controls expansion. The node itself controls navigation.

## Branch WAN Overview

Header:

PCD > Harare > New Ardbennie > Head Office

Then vertically:

WAN 1
graph

WAN 2
graph

WAN 3
graph

Do not replace this with separate pages for each WAN.

Each WAN section contains compact metrics and the graph.

ISP identity is shown with an ISP-specific badge.

WAN health controls the graph/card border.

## Graphs

Live graph default: 1 hour.

Lines:

- RX
- TX
- Total

Ping is shown separately in a compact square status box.

Clicking Ping opens more detailed ping information.

Historical tabs:

- 1 Day
- 7 Days
- 1 Month
- 1 Year

## WAN Link Details

Live graph remains at the top.

Below:

current metrics → ping → historical tabs → alerts → configuration → notes

Configuration is read-only here.

Use a separate Edit page.

## Quick actions

Use compact icons/actions rather than large buttons where appropriate.

Examples:

- Open Firewall
- Ping Now
- Poll SNMP Now
- Alert History
- Copy WAN Info
- Open Public IP

## UX rules

- Preserve the PRTG-like multi-WAN comparison workflow.
- Avoid unnecessary clicks.
- Do not hide critical WAN metrics behind menus.
- Do not make graphs enormous.
- Vertical scrolling is preferred for multiple WANs.
