#!/usr/bin/env python3
"""Regression audit for the meshes selected by the walkthrough collision system."""
import gzip, json, struct
from pathlib import Path

raw = gzip.decompress(Path("modern_house_realistic.glb.gz").read_bytes())
magic, version, total = struct.unpack_from("<III", raw, 0)
if magic != 0x46546C67 or version != 2 or total != len(raw):
    raise SystemExit("Invalid GLB header")
size, kind = struct.unpack_from("<II", raw, 12)
if kind != 0x4E4F534A:
    raise SystemExit("Missing GLB JSON chunk")
g = json.loads(raw[20:20+size].decode("utf-8").rstrip(" \\0"))
accessors, meshes = g.get("accessors", []), g.get("meshes", [])
selected, structural, furniture, excluded = [], [], [], []
for node in g.get("nodes", []):
    if "mesh" not in node:
        continue
    mesh = meshes[node["mesh"]]
    if not mesh.get("primitives"):
        continue
    acc_id = mesh["primitives"][0]["attributes"].get("POSITION")
    if acc_id is None:
        continue
    acc = accessors[acc_id]
    if "min" not in acc or "max" not in acc:
        continue
    lo, hi = acc["min"], acc["max"]
    scale, trans = node.get("scale", [1,1,1]), node.get("translation", [0,0,0])
    z0, z1 = sorted((lo[2]*scale[2]+trans[2], hi[2]*scale[2]+trans[2]))
    height = z1-z0
    name = node.get("name", "")
    primary_wall = bool(__import__("re").match(r"^structure_(?:1[4-9]|[23]\\d|40)$", name))
    compatibility_wall = name.startswith(("Outer_", "P_"))
    decorative_structure = name.startswith("structure_") and not primary_wall
    floor_ceiling = height < 0.08 or any(x in name.lower() for x in ("floor","ceiling","roof"))
    body_overlap = z1 > 0.12 and z0 < 1.72
    include = primary_wall or compatibility_wall or (not decorative_structure and not floor_ceiling and body_overlap and z1 > 0.28)
    item = {"name":name,"source_z":[round(z0,3),round(z1,3)],"height":round(height,3)}
    if include:
        selected.append(item)
        if primary_wall or compatibility_wall:
            structural.append(item)
        else:
            furniture.append(item)
    else:
        excluded.append(item)

if len(structural) < 8:
    raise SystemExit(f"Too few structural collision meshes selected: {len(structural)}")
if len(furniture) < 5:
    raise SystemExit(f"Too few furniture/fixture collision meshes selected: {len(furniture)}")
report = {
    "selected_meshes": len(selected),
    "structural_wall_meshes": len(structural),
    "furniture_fixture_meshes": len(furniture),
    "excluded_meshes": len(excluded),
    "sample_furniture": furniture[:30],
}
Path(".github/collision-audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
print(f"Collision selection audit passed: {len(structural)} structural + {len(furniture)} furniture/fixture meshes.")
