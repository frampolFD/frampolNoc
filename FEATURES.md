# FEATURES.md

## Dashboard

Show:

- Total customers
- Total WAN links
- Online links
- Offline links
- Warning links
- Monitoring-disabled links
- Recent alerts

The dashboard starts with no customer selected.

The Customer Explorer is always visible.

## Customer Explorer

Always show all customers.

Hierarchy:

Customer
→ City/Town
→ Suburb/Area
→ Branch
→ WAN Link

Clicking a branch immediately loads its WAN links.

The Explorer remains visible while the main workspace changes.

## Branch WAN Overview

This is the primary operational screen.

Header:

Customer > City > Suburb > Branch

Show all branch WAN links vertically in one view.

Each WAN link shows:

- Health status
- ISP
- ISP badge
- Circuit capacity
- Role
- Current download
- Current upload
- Total throughput
- Latency
- Packet loss
- 1-hour RX/TX/Total graph
- Ping status box
- Quick actions

Graph health border follows monitoring health.

Multiple WAN graphs should have synchronized hover/cursor time when practical.

## WAN Link Details

Show the 1-hour live graph at the top.

Show:

- Download
- Upload
- Total throughput
- Utilisation
- Latency
- Packet loss
- Availability
- Consumption
- Last poll
- Ping details
- Historical graphs
- Alerts
- Configuration
- Engineer notes
- Diagnostic toolbox

Historical tabs:

- 1 Day
- 7 Days
- 1 Month
- 1 Year

Historical views support bandwidth, latency, packet loss, availability and consumption.

## Quick actions

- Open Firewall
- Ping Now
- Poll SNMP Now
- Alert History
- Full Graph
- Copy WAN Information
- Open Public IP

Editing is on a separate page and restricted by role.

## WAN onboarding

Structured workflow:

1. Customer
2. Location
3. WAN information
4. Monitoring
5. SNMP interface discovery
6. Review
7. Create

WAN information:

- ISP
- Circuit capacity
- Role
- Public IP where applicable
- Device vendor/model where required for naming
- Notes

ICMP:

- enabled
- target IP

SNMP:

- enabled
- target IP
- version
- credentials/community
- discovery
- selected interface

## Interface discovery

Perform real SNMP discovery.

Display discovered:

- interface name
- ifIndex
- IP where available
- description
- alias
- speed
- admin state
- operational state
- MAC where available

Allow manual selection.

## ISP

ISP is reusable.

Store:

- name
- badge identity
- support phone
- NOC email
- portal URL
- escalation contact
- notes

Initial providers may include Liquid, TelOne, Dandemutande, Starlink, ZOL and Other.

## Alerts

Initial alerts:

- WAN down
- WAN recovered
- high latency
- packet loss
- sustained high utilisation

Sustained utilisation has:

- threshold percentage
- duration

Example:

90% for 10 minutes.

## Engineer notes

Free-text operational notes attached to a WAN link.

## Naming

Generate names from structured data.

Example:

PCD - Harare - New Ardbennie - FortiGate 100F - Frampol LTZ - (169.239.24.126) - 100Mbps
