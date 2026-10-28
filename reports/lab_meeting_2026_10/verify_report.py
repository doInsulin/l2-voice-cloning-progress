"""Check the offline report package, numerical joins, and file links."""
import csv
import base64
import hashlib
import html.parser
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = ROOT / "docs" / "lab_meeting_progress_2026_10.html"
SRC = HERE / "source_results"

class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        for key in ("href", "src"):
            if key in data:
                self.links.append(data[key])

doc = DOC.read_text(encoding="utf-8")
parser = Links(); parser.feed(doc)
anchors = set(re.findall(r'id="([^"]+)"', doc))
inline_image_hashes = []
for link in parser.links:
    if link.startswith("#"):
        assert link[1:] in anchors, link
    elif link.startswith("data:image/png;base64,"):
        inline_image_hashes.append(hashlib.sha256(base64.b64decode(link.split(",",1)[1])).hexdigest())
    else:
        assert not re.match(r"^[a-z]+://", link), f"network dependency: {link}"
        assert (DOC.parent / link).resolve().is_file(), f"broken HTML link: {link}"
assert len(inline_image_hashes) == 28
with (HERE / "figure_registry.csv").open(encoding="utf-8", newline="") as f:
    figures = list(csv.DictReader(f))
assert len(figures) == 28
assert sorted(inline_image_hashes) == sorted(r["sha256"] for r in figures)
for r in figures:
    assert hashlib.sha256((HERE / r["file"]).read_bytes()).hexdigest() == r["sha256"]

for p in (HERE / "figures").glob("*.svg"):
    ET.parse(p)
assert len(list((HERE / "figures").glob("*.svg"))) == 7

with (SRC / "SHA256SUMS.csv").open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        p = SRC / row["file"]
        assert p.is_file(), p
        assert hashlib.sha256(p.read_bytes()).hexdigest() == row["sha256"], p

with (HERE / "experiment_summary.csv").open(encoding="utf-8", newline="") as f:
    csv_rows = list(csv.DictReader(f))
json_rows = json.loads((HERE / "experiment_summary.json").read_text(encoding="utf-8"))
assert len(csv_rows) == len(json_rows) >= 35
assert all(str(c[k]) == str(j[k]) for c,j in zip(csv_rows,json_rows)
           for k in ("experiment","trait","model","speakers","n","metric","source_file"))
for row in json_rows:
    assert (HERE / row["source_file"]).is_file(), row["source_file"]

for readme in (ROOT / "README.md", HERE / "README.md"):
    content = readme.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", content):
        if target.startswith(("http:", "https:", "#")):
            continue
        assert (readme.parent / target).resolve().exists(), f"broken README link: {readme}: {target}"

for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts:
        continue
    limit = 15_000_000 if path == DOC else 2_000_000
    assert path.stat().st_size < limit, f"unexpected large file: {path}"
    assert path.suffix.lower() not in {".wav", ".flac", ".pt", ".pth", ".ckpt", ".safetensors"}, path

original_root = ROOT.parent / "research"
if original_root.is_dir():
    mapping = re.findall(r"^\| `([^`]+)` \| `([^`]+)` \|$", (SRC / "README.md").read_text(encoding="utf-8"), re.M)
    assert len(mapping) >= 20
    for packaged, original in mapping:
        assert hashlib.sha256((SRC / packaged).read_bytes()).digest() == hashlib.sha256((original_root / original).read_bytes()).digest(), packaged
    for r in figures:
        original = ROOT.parent / r["original_path"]
        assert hashlib.sha256(original.read_bytes()).hexdigest() == r["sha256"], original

by = {(r["experiment"],r["trait"]): r for r in json_rows}
expected = {
    ("Final reference intervention","estimated voiced-F0 range"): 0.7269175628376776,
    ("Final reference intervention","MFA local word-boundary gap"): 0.21129547538945792,
    ("Final reference intervention","RMS-detected low-energy interval"): 0.06725988340563674,
    ("Final matched segmental reconstruction","EH→AE"): 0.7978105127112246,
    ("Final matched segmental reconstruction","IH→IY"): 0.5108723035592827,
}
for key,val in expected.items():
    assert abs(by[key]["estimate"]-val) < 1e-12, key
assert "thesis draft" not in doc.lower()
assert "2026 年 10 月 28 日" in doc
assert '<html lang="zh-CN">' in doc
print(f"Verified {len(parser.links)} HTML links/assets, 28 embedded original figures, README links, 7 SVG files, {len(csv_rows)} result records, frozen headline estimates, source snapshots when present, and package size rules.")
