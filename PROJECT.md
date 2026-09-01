# PROJECT.md

# Frampol NOC

## Purpose

Build a practical WAN monitoring platform for Frampol engineers.

The first release must provide real monitoring, not mocked monitoring.

## Primary principle

Engineer First.

Every screen should reduce the time required to identify and troubleshoot a customer WAN issue.

## Version 1 scope

IN:

- Customers
- Cities/Towns
- Suburbs/Areas
- Branches
- WAN Links
- ISP records
- ICMP
- SNMP
- SNMP interface discovery
- Historical measurements
- Bandwidth and consumption graphs
- Alerts
- Engineer notes
- Dashboard
- Branch WAN Overview
- WAN Link Details
- Basic users/authentication

OUT:

- Server monitoring
- Switch monitoring
- Wireless monitoring
- VPN monitoring
- NetFlow
- Syslog
- Topology
- IPAM
- Printer inventory
- Switch-port documentation
- Configuration backup
- FortiGate API
- SD-WAN awareness
- Customer portal
- AI root-cause analysis

## Hierarchy

Customer
  └── City / Town
        └── Suburb / Area (optional)
              └── Branch
                    └── WAN Link

A Branch is a physical customer location. Latitude and longitude are required during branch onboarding.

## Monitoring philosophy

A WAN Link is an operational record even when monitoring is disabled.

Monitoring states:

- Fully monitored
- ICMP only
- SNMP only
- ICMP + SNMP
- Monitoring disabled
- Not configured

## SNMP

The SNMP target is the IP address used to reach the device/interface being monitored.

The application must discover interfaces through SNMP. It must not hardcode interface names.

The engineer manually selects the interface that represents the WAN being onboarded.

If the entered IP matches a discovered interface IP, the UI may suggest that interface, but must never silently select it.

Where supported, collect:

- ifIndex
- interface name
- description
- alias
- IP
- speed
- administrative status
- operational status
- MAC address
- high-capacity RX octets
- high-capacity TX octets

Use counter deltas to calculate traffic rates.

## ICMP

ICMP independently provides:

- availability
- latency
- packet loss
- jitter

Default polling: 30 seconds.

## SNMP polling

Default polling: 60 seconds.

Polling must run in background workers and must never block web requests.

## Circuit capacity

Circuit speed/capacity is required for monitored WAN links.

Example: 100 Mbps.

It is used to calculate utilisation.

## Sustained utilisation

An alert can trigger when utilisation remains above a configurable threshold for a configurable duration.

Example: 90% for 10 minutes.

Both threshold and duration are configurable.

## Naming

WAN names are generated from stored fields rather than manually typed.

Example:

PCD - Harare - New Ardbennie - FortiGate 100F - Frampol LTZ - (169.239.24.126) - 100Mbps

The naming template must be configurable later without changing the underlying data.

## Architecture principles

- Web API must remain responsive while polling runs.
- Monitoring failures must be isolated per target.
- Credentials must not be stored in frontend code or logs.
- Configuration must use environment variables/secrets.
- Database migrations must be versioned.
- Monitoring data must use timestamps and UTC internally.
- Code should be modular and testable.
