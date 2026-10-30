"""Verify the frozen sources, output hashes, and core denominator claims."""
import csv, hashlib, json
from pathlib import Path

here=Path(__file__).resolve().parents[1]
root=here.parents[2]
manifest=json.loads((here/'run_manifest.json').read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for name,digest in manifest['source_sha256'].items():
    assert sha(root/name)==digest, f'frozen source changed: {name}'
for name,digest in manifest['artifacts_sha256'].items():
    assert sha(here/name)==digest, f'output changed: {name}'
def rows(name):
    with (here/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
a=rows('incremental_value_results.csv')
assert len(a)==642 and len({x['token_key'] for x in a})==214
b=rows('time_resolved_did_results.csv')
for contrast,n in [('EH_TO_AE',35),('IH_TO_IY',18)]:
    q=[x for x in b if x['support']=='strict' and x['contrast']==contrast and x.get('time_pct')]
    assert len(q)==5 and all(int(x['n_pairs'])==n for x in q)
c=rows('speaker_specific_preservation.csv')
assert len(c)==144 and sum(x['duration_match']=='1' for x in c)==70
print(f'PASS: {len(manifest["source_sha256"])} frozen inputs, {len(manifest["artifacts_sha256"])} artifacts; A 214, B 35/18, C 70/144')
