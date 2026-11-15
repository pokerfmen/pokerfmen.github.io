#!/usr/bin/env python3
"""Static route-connectivity check for the primary house model."""
import gzip, json, math, struct
from collections import deque
from pathlib import Path

raw = gzip.decompress(Path("modern_house_realistic.glb.gz").read_bytes())
magic, version, length = struct.unpack_from("<III", raw, 0)
if magic != 0x46546C67 or version != 2 or length != len(raw):
    raise SystemExit("Invalid GLB header")
json_length, json_type = struct.unpack_from("<II", raw, 12)
if json_type != 0x4E4F534A:
    raise SystemExit("Missing GLB JSON chunk")
gltf = json.loads(raw[20:20 + json_length].decode("utf-8").rstrip(" \0"))
accessors, meshes = gltf["accessors"], gltf["meshes"]

# Doorway spans are taken from the primary model's door markers and approved
# room connectivity. Coordinates are world X/Z after the Z-up conversion.
OPENINGS = {
    "structure_23": ("x", [(4.25, 5.03)]),
    "structure_28": ("z", [(-4.8, -4.0), (-7.8, -7.0)]),
    "structure_30": ("z", [(-7.8, -7.0)]),
    "structure_32": ("z", [(-10.9, -10.1)]),
    "structure_33": ("z", [(-10.8, -10.0)]),
    "structure_37": ("z", [(-11.0, -10.2)]),
    "structure_31": ("x", [(2.0, 2.9)]),
    "structure_36": ("x", [(8.7, 9.7)]),
    "structure_35": ("x", [(4.5, 5.3)]),
}
RADIUS, STEP = 0.23, 0.10
X_MIN, Z_MIN, NX, NZ = -0.5, -17.5, 135, 185
SPAWN = (4.7, -9.7)
TARGETS = {
    "bedroom_1": (3.0, -2.5), "bedroom_2": (3.0, -6.8),
    "bedroom_3": (6.8, -1.5), "bathroom_1": (8.0, -4.3),
    "bathroom_2": (8.4, -6.7), "kitchen": (11.5, -4.3),
    "living_room": (11.5, -7.2), "utility_room": (8.0, -10.5),
    "garage": (4.7, -13.5),
}
walls = []
for node in gltf["nodes"]:
    name = node.get("name", "")
    if "mesh" not in node or not name.startswith("structure_"):
        continue
    suffix = name.split("_")[-1]
    if not suffix.isdigit() or not 14 <= int(suffix) <= 40:
        continue
    primitive = meshes[node["mesh"]]["primitives"][0]
    accessor = accessors[primitive["attributes"]["POSITION"]]
    lo, hi = accessor["min"], accessor["max"]
    box = [lo[0], hi[0], -hi[1], -lo[1]]
    axis_gaps = OPENINGS.get(name)
    if axis_gaps:
        axis, gaps = axis_gaps
        low, high = (box[0], box[1]) if axis == "x" else (box[2], box[3])
        spans, cursor = [], low
        for a, b in sorted(gaps):
            a, b = max(a, low), min(b, high)
            if a > cursor + 0.01:
                spans.append((cursor, a))
            cursor = max(cursor, b)
        if high > cursor + 0.01:
            spans.append((cursor, high))
        for a, b in spans:
            walls.append((a-RADIUS, b+RADIUS, box[2]-RADIUS, box[3]+RADIUS)
                         if axis == "x" else
                         (box[0]-RADIUS, box[1]+RADIUS, a-RADIUS, b+RADIUS))
    else:
        walls.append((box[0]-RADIUS, box[1]+RADIUS, box[2]-RADIUS, box[3]+RADIUS))

def blocked(x, z):
    return any(a <= x <= b and c <= z <= d for a, b, c, d in walls)
def cell(p):
    return round((p[0]-X_MIN)/STEP), round((p[1]-Z_MIN)/STEP)
def world(c):
    return X_MIN+c[0]*STEP, Z_MIN+c[1]*STEP

if blocked(*SPAWN):
    raise SystemExit("Spawn point intersects a structural wall")
start = cell(SPAWN)
queue, parent = deque([start]), {start: None}
dirs = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
while queue:
    x, z = queue.popleft()
    for dx, dz in dirs:
        nxt = x+dx, z+dz
        if not (0 <= nxt[0] < NX and 0 <= nxt[1] < NZ) or nxt in parent:
            continue
        px, pz = world(nxt)
        if blocked(px, pz):
            continue
        if dx and dz and (blocked(*world((x+dx,z))) or blocked(*world((x,z+dz)))):
            continue
        parent[nxt] = (x,z)
        queue.append(nxt)

results = {}
for name, point in TARGETS.items():
    if blocked(*point) or cell(point) not in parent:
        results[name] = False
    else:
        results[name] = True
report = {"spawn": SPAWN, "player_radius_m": RADIUS, "reachable": results}
Path(".github/route-audit.json").write_text(json.dumps(report, indent=2) + "\n")
failed = [name for name, ok in results.items() if not ok]
print(f"Route connectivity: {len(results)-len(failed)}/{len(results)} destinations reachable.")
if failed:
    raise SystemExit("Unreachable destinations: " + ", ".join(failed))
