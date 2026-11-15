#!/usr/bin/env python3
import re, subprocess, tempfile
from pathlib import Path
html = Path("index.html").read_text(encoding="utf-8")
scripts = re.findall(r'<script type="module">(.*?)</script>', html, flags=re.S)
if len(scripts) != 1:
    raise SystemExit(f"Expected one module script, found {len(scripts)}")
with tempfile.NamedTemporaryFile("w", suffix=".mjs", encoding="utf-8") as f:
    f.write(scripts[0]); f.flush()
    subprocess.run(["node", "--check", f.name], check=True)
print("HTML module JavaScript syntax: OK")
