# dat_loader

Parser for LoR `.dat` files.

## File spec
Order:
1. `n_clients`
2. `n_depots`
3. `max_depots_open`
4. `n_veh`
5. depot coords: `n_depots` lines, `x y`
6. client coords: `n_clients` lines, `x y`
7. vehicle capacity
8. depot capacities: `n_depots` lines
9. client demands: `n_clients` lines
10. depot fixed costs: `n_depots` lines
11. vehicle fixed cost
12. optional `cola`

Coords parse as float. Counts parse as int.

## API

### `Instance`
Dataclass:
- `depots: dict[int, dict]`
- `clients: dict[int, dict]`
- `data: dict`

Keys:
- `depots[i] = {x, y, cap, fixed_cost}`
- `clients[j] = {x, y, demand}`
- `data = {n_clients, n_depots, max_depots_open, n_veh, veh_cap, veh_fixed_cost, cola}`

### `load_dat(source)`
Load from path or iterable of lines.

### `load_dat_path(path)`
Alias for `load_dat`.

### `load_dat_folder(folder)`
Load all `*.dat` in folder.

### `list_dat_files(folder)`
List `*.dat` paths.

## Example
```python
from dat_loader import load_dat

inst = load_dat("instances/coord100-5-1.dat")
print(inst.data)
print(inst.depots[1])
```
