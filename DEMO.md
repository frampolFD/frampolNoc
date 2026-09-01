# MVP DEMO CHECKLIST

## Boss demonstration

The objective is to demonstrate that Frampol NOC is a real WAN monitoring application, not a static dashboard.

### Before the demo

- Start backend
- Start frontend
- Confirm database is running
- Confirm monitoring worker is running
- Confirm test/real FortiGate SNMP target is reachable
- Confirm ICMP target is reachable
- Confirm SNMP credentials work

### Demo flow

1. Login.
2. Show the Customer Explorer.
3. Open a customer.
4. Open City.
5. Open Suburb.
6. Open Branch.
7. Show multiple WAN links.
8. Add/onboard a WAN Link.
9. Enter SNMP target.
10. Click Discover Interfaces.
11. Show the real returned interfaces.
12. Select the WAN interface.
13. Save.
14. Show polling status.
15. Show RX/TX/Total throughput.
16. Show utilisation against circuit capacity.
17. Show ICMP latency/loss.
18. Show 1-hour graph.
19. Show another WAN on the same branch.
20. Demonstrate comparison.
21. Trigger or demonstrate a sustained-utilisation alert.
22. Open WAN Details.
23. Show Engineer Notes.
24. Use Open Firewall if configured.

### If there is not enough historical data

Do not fake production data.

Use a clearly labelled development/demo target or test dataset.

Explain that the graph begins accumulating measurements once monitoring starts.

### What to say to management

"Frampol NOC is being built around the way our engineers actually support customers. Instead of managing anonymous sensors, we navigate from the customer down to the branch and see all WAN links together. SNMP discovers the actual interfaces on the monitored device, the engineer selects the correct WAN interface, and the system then calculates traffic, utilisation and consumption while ICMP independently measures link health."

## MVP success

The most important proof is:

REAL DEVICE
→ REAL SNMP DISCOVERY
→ REAL INTERFACE SELECTION
→ REAL POLLING
→ REAL DATA
→ REAL GRAPH
