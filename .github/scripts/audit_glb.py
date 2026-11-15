#!/usr/bin/env python3
"""Audit the primary compressed GLB and write a machine-readable geometry report."""
import gzip
import json
import struct
from pathlib import Path

MODEL = Path("modern_house_realistic.glb.gz")
raw = gzip.decompress(MODEL.read_bytes())
magic, version, total_length = struct.unpack_from("<III", raw, 0)
if magic != 0x46546C67 or version != 2 or total_length != len(raw):
    raise SystemExit("Invalid GLB header")
json_length, json_type = struct.unpack_from("<II", raw, 12)
if json_type != 0x4E4F534A:
    raise SystemExit("Missing GLB JSON chunk")
gltf = json.loads(raw[20:20 + json_length].decode("utf-8").rstrip(" \0"))
accessors = gltf.get("accessors", [])
meshes = gltf.get("meshes", [])
nodes = gltf.get("nodes", [])

def bounds(node):
    mesh = meshes[node["mesh"]]
    prim = mesh["primitives"][0]
    accessor = accessors[prim["attributes"]["POSITION"]]
    if "min" not in accessor or "max" not in accessor:
        return None
    lo, hi = accessor["min"], accessor["max"]
    scale = node.get("scale", [1, 1, 1])
    translation = node.get("translation", [0, 0, 0])
    pairs = [(lo[i] * scale[i] + translation[i], hi[i] * scale[i] + translation[i]) for i in range(3)]
    return [[min(a, b), max(a, b)] for a, b in pairs]

floors, walls, objects = [], [], []
for node in nodes:
    if "mesh" not in node:
        continue
    b = bounds(node)
    if b is None:
        continue
    name = node.get("name", "")
    item = {"name": name, "x": b[0], "source_y": b[1], "source_z": b[2]}
    if name.lower().startswith(("floor", "ground")):
        floors.append(item)
    if name.lower().startswith(("structure_", "outer_", "p_")):
        walls.append(item)
    objects.append(item)

report = {
    "glb_bytes": len(raw),
    "nodes": len(nodes),
    "meshes": len(meshes),
    "floor_meshes": floors,
    "wall_meshes": walls,
    "mesh_bounds": objects,
}
out = Path(".github/audit-report.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"GLB audit passed: {len(nodes)} nodes, {len(meshes)} meshes, {len(floors)} floors, {len(walls)} walls.")
