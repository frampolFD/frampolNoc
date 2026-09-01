# DOMAIN_MODEL.md

Ownership model for the core entities. This exists specifically to make the
Customer/City/Suburb/Branch relationship unambiguous, after an early
implementation mistake treated City and Suburb as if they belonged to a
Customer (see DECISIONS.md "Shared geographic ownership model" for the
correction and why it mattered).

## Ownership

```
Customer
  └── Branch (customer_id)
        ├── City (city_id)       — shared reference data, not owned by any Customer
        └── Suburb (suburb_id)   — shared reference data, belongs to a City, not to any Customer
```

- **Customer** owns **Branch** directly (`Branch.customer_id`).
- **Branch** references **City** (`Branch.city_id`) and optionally
  **Suburb** (`Branch.suburb_id`).
- **City** and **Suburb** are shared geographic reference data — think of
  them as a small preloaded gazetteer, not customer records. They exist
  independently of any Customer and are never deleted as a side effect of
  deleting a Customer or a Branch.
- **Suburb** belongs to exactly one **City** (`Suburb.city_id`) and must
  match the City selected on any Branch that references it.

## What this means in practice

- Two different customers can (and routinely do) have a Branch in the same
  city — e.g. two unrelated customers each have a Harare branch. Both
  branches reference the *same* `cities` row.
- Creating, editing, or deleting a City/Suburb is a shared administrative
  action — it is visible to and usable by every customer immediately, not
  scoped to whichever customer happened to be selected when it was added.
- The **Explorer** sidebar (Customer → City → Suburb → Branch → WAN Link)
  is *derived per customer* from that customer's own Branches, grouped by
  which City/Suburb each Branch uses — it is not read from a
  `Customer.cities` relationship, because no such relationship exists. The
  same City can legitimately appear under multiple customers in the
  Explorer, each showing only that customer's own branches under it.
- Deleting a City or Suburb that still has Branches pointing at it is
  **blocked**, never cascaded — a shared City must never delete another
  customer's Branch as a side effect.

## Why this matters

Before the correction, City had a `customer_id` and Customer had a `cities`
relationship. In practice this meant every customer that had a branch in,
say, Harare, ended up with its own private copy of a "Harare" city record —
duplicate rows for the same real-world place, with no way to share one
city across customers, and deleting a customer's city risked cascading into
deleting branches that depended on it. The corrected model treats cities
and suburbs as what they actually are: real-world places that exist
independently of which of Frampol's customers happens to have a branch
there.
