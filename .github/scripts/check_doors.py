#!/usr/bin/env python3
"""Check that doorway cuts align with door leaf markers in the primary GLB."""
import gzip, json, struct
from pathlib import Path
raw=gzip.decompress(Path("modern_house_realistic.glb.gz").read_bytes())
n,t=struct.unpack_from("<II",raw,12)
g=json.loads(raw[20:20+n].decode("utf-8").rstrip(" \\0"))
accessors,meshes=g["accessors"],g["meshes"]
nodes={x.get("name"):x for x in g["nodes"]}
# Expected leaf ranges in world coordinates after source Z-up conversion.
pairs=[
 ("structure_53","structure_23","x"),
 ("structure_55","structure_28","z"),
 ("structure_56","structure_30","z"),
 ("structure_57","structure_32","z"),
 ("structure_58","structure_33","z"),
 ("structure_59","structure_37","z"),
]
def box(name):
 node=nodes[name]; acc=accessors[meshes[node["mesh"]]["primitives"][0]["attributes"]["POSITION"]]
 lo,hi=acc["min"],acc["max"]
 return (lo[0],hi[0],-hi[1],-lo[1])
for leaf,wall,axis in pairs:
 l=box(leaf); w=box(wall)
 if axis=="x":
  center=(l[0]+l[1])/2
  assert w[0]-.01 <= center <= w[1]+.01, (leaf,wall,l,w)
 else:
  center=(l[2]+l[3])/2
  assert w[2]-.01 <= center <= w[3]+.01, (leaf,wall,l,w)
print(f"Door alignment: {len(pairs)}/{len(pairs)} markers intersect intended wall spans.")
