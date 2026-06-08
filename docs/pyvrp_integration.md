# PyVRP integration plan

## Problem
Direct Allocation (DA) is artificially cheap if encoded as a normal PyVRP decision:

- DA outbound edge has cost
- DA return edge has zero cost
- objective minimizes total distance/cost
- solver will prefer DA whenever possible

So DA should not be a free decision inside PyVRP unless DA cost is made comparable to routing.

## Decision
Use DA as deterministic preprocessing, then solve residual routing in PyVRP.

Pipeline:
1. Build DA eligibility by depot coverage radius.
2. Assign DA clients outside PyVRP using a fixed policy.
3. Deduct DA demand from depot capacity.
4. Build routing-only PyVRP model for remaining clients.
5. Size routing fleet from residual depot capacity.
6. Solve residual CVRP/MDVRP.
7. Combine DA cost + routing cost + fixed costs in report.

## Stages

### 1. DA eligibility
Function:
```python
build_direct_allocation_data(inst, radius)
```

Outputs:
- `da_data[depot_id]["clients"]`
- `cost_ij[(depot_id, client_id)]`
- arc metadata for reporting/debugging

### 2. DA assignment
Function:
```python
assign_da_clients(inst, da_data, veh_cap)
```

Current policy:
- client eligible if within `R` from depot
- assign to nearest feasible depot
- depot DA capacity = `veh_cap * floor(depot_cap / veh_cap)`
- if no feasible depot capacity remains, client goes to routing

Output:
```python
da_assigned = {depot_id: [client_ids]}
routing_set = {client_ids}
```

### 3. Capacity accounting
For each depot:
```python
da_demand_i = sum(demand[j] for j in da_assigned[i])
remaining_capacity_i = depot_capacity_i - da_demand_i
```

Constraint emulation:
- PyVRP has no explicit depot capacity
- depot capacity is enforced by limiting vehicle capacity and count

### 4. Routing fleet construction
For each depot:
```python
n_full = floor(remaining_capacity_i / vehicle_capacity)
residual = remaining_capacity_i % vehicle_capacity
```

Create:
- `n_full` vehicles with capacity `vehicle_capacity`
- if `residual > 0`, 1 vehicle with capacity `residual`

Important: do not create routing vehicles for depots with zero remaining capacity.

### 5. Routing model
Build PyVRP model with:
- all active depots
- only routing clients (`routing_set`)
- routing profile only
- complete depot/client routing graph
- edge cost = `euclidean_distance * scale * F_R`

Do not add DA clients or DA edges to PyVRP.

### 6. Cost reporting
Compute DA cost outside PyVRP:
```python
da_cost = sum(distance(depot_i, client_j) * F_A for i, clients in da_assigned.items() for j in clients)
```

Compute routing cost from solution:
```python
routing_cost = routing_distance_scaled / scale
```

Total:
```python
total = routing_cost + da_cost + vehicle_cost + depot_cost
```

Where:
- `vehicle_cost = routing_vehicles_used * veh_fixed_cost`
- `depot_cost = cost_depots` from Excel

## Recommended implementation changes

### Add `da_preprocessor.py`
Functions:
- `build_direct_allocation_data(inst, radius)`
- `assign_da_clients(inst, da_data, veh_cap)`
- `compute_da_cost(inst, da_assigned, F_A)`
- `compute_depot_residual_capacity(inst, da_assigned)`

### Add routing-only builder
Function:
```python
build_routing_model(inst, routing_clients, residual_capacity_by_depot)
```

Returns:
```python
model, info
```

`info` should include:
- `scale`
- `routing_clients`
- `residual_capacity_by_depot`
- `vehicle_types`
- `depot_nodes`
- `client_nodes`

### Keep old combined builder only as experimental
Current `build_full_model()` mixes DA and routing in PyVRP. Keep it only if comparing formulations.

Recommended production flow should be:
```python
da_data, _ = build_direct_allocation_data(inst, inst.data["R"])
da_assigned, routing_clients = assign_da_clients(inst, da_data, inst.data["veh_cap"])
residual_cap = compute_depot_residual_capacity(inst, da_assigned)
m, info = build_routing_model(inst, routing_clients, residual_cap)
res = solve_fast(m)
report = build_residual_report(inst, res, config, info, da_assigned)
```

## Validation checks

Before solve:
- every client is either DA or routing
- no overlap between DA and routing clients
- depot DA demand <= depot capacity
- residual routing capacity sum >= routing demand

After solve:
- all routing clients served
- total served demand = total instance demand
- per depot demand <= depot capacity
- DA cost + routing cost + fixed costs matches report

## Open modeling choices

### DA policy
Current nearest-feasible policy is deterministic and simple.
Alternatives:
- cheapest global DA assignment
- prioritize high-demand clients
- reserve capacity for routing-heavy depots
- solve DA assignment as small LP/MIP outside PyVRP

### DA cost
If DA should include return travel, use:
```python
da_cost = 2 * distance * F_A
```

If return is truly free by problem definition, keep outbound only.

### Vehicle fixed cost
Need decide whether DA vehicles have fixed cost.
Current report counts routing vehicles only. If DA vehicles should count, add:
```python
vehicle_cost = (routing_vehicles_used + da_vehicles_used) * veh_fixed_cost
```
