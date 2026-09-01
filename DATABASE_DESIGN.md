# DATABASE_DESIGN.md

This is the logical data model. Claude Code may adapt implementation details after reviewing the existing repository, but must preserve these business concepts.

## Customer

Fields:

- id
- name
- status
- primary_contact
- contact_phone
- contact_email
- notes
- created_at
- updated_at

Relationship:

Customer has many Cities.

## City

- id
- customer_id
- name

Relationship:

City belongs to Customer.
City has many Suburbs and/or Branches.

## Suburb

Optional.

- id
- city_id
- name

## Branch

- id
- customer_id
- city_id
- suburb_id nullable
- name
- physical_address
- latitude required
- longitude required
- primary_contact
- contact_phone
- notes
- created_at
- updated_at

Branch has many WAN Links.

## ISP

Reusable entity.

- id
- name
- badge_key / display identity
- support_phone
- noc_email
- portal_url
- escalation_contact
- notes

## WAN Link

Central monitoring record.

- id
- branch_id
- isp_id
- name_generated
- circuit_capacity_bps
- role
- public_ip nullable
- icmp_enabled
- icmp_target_ip nullable
- snmp_enabled
- snmp_target_ip nullable
- snmp_version nullable
- snmp_credential_reference
- selected_if_index nullable
- selected_interface_name nullable
- selected_interface_ip nullable
- selected_interface_alias nullable
- monitoring_status
- notes
- created_at
- updated_at

## SNMP Interface

Discovered metadata.

- id
- wan_link_id
- if_index
- name
- description
- alias
- ip_address nullable
- speed_bps nullable
- mac_address nullable
- admin_status nullable
- oper_status nullable
- last_discovered_at

A WAN Link has one selected interface but discovery may return many candidates.

## Measurements

Time-series measurements for a WAN Link.

Store timestamped data such as:

- rx_bps
- tx_bps
- total_bps
- utilisation_percent
- rx_bytes_delta / accumulated consumption as appropriate
- tx_bytes_delta / accumulated consumption as appropriate
- latency_ms
- packet_loss_percent
- jitter_ms
- availability

Use appropriate database/time-series strategy for scale.

## Alerts

- id
- wan_link_id
- alert_type
- severity
- threshold
- duration_seconds
- started_at
- ended_at
- acknowledged_at
- acknowledged_by
- message

## Engineer Notes

- id
- wan_link_id
- user_id
- body
- created_at
- updated_at

## Users

- id
- name
- email
- role
- password_hash where local auth is used
- created_at
- updated_at

Future Microsoft login can replace/augment local authentication.

## Important

Do not duplicate firewall/device data on every WAN link unless required for Version 1.

Device/API integration is a future capability. For MVP, retain only the vendor/model information needed for onboarding, monitoring and generated naming.
