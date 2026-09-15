"""Read-only audit of frozen E6/E7B inputs; writes only beside this script.
No revised experiment outcomes or preregistration verdicts are computed.
"""
from pathlib import Path
import json,itertools,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
W=[.25,.5,.25]
perms=list(itertools.permutations(range(3)))
valid=[]
for p in perms:
    marginal=[sum(W[k] for k in range(3) if p[k]==j) for j in range(3)]
    if marginal==W: valid.append(p)
p=(1,0,2)
result={'e6':{'specified_weights':W,'counterexample_permutation':p,'counterexample_resulting_weights':[sum(W[k] for k in range(3) if p[k]==j) for j in range(3)],'weight_preserving_permutations':valid,'valid_constructions':len(valid)**4,'enumerated_constructions':len(perms)**4,'conclusion':'Published range is not established as a fixed-marginal coupling range.'}}
cache=ROOT/'experiments/e7b/freeze/cache'
r=json.loads((ROOT/'experiments/e7b/results/e7_result.json').read_text())
inj=set(json.loads((cache/'_inj_goals.json').read_text()))
ns=r['holdout_judges']+r['excluded_judges']
data={n:json.loads((cache/(n+'.json')).read_text()) for n in ns}
shared=set.intersection(*(set(d) for d in data.values()))
rows=[]
for n,d in sorted(data.items()):
    own=set(d)-inj
    def threshold(b):
        return next((t for t in sorted({d[k] for k in b}) if sum(d[k]>=t for k in b)/len(b)<=.05),None)
    rows.append({'judge':n,'own_benign_n':len(own),'shared_benign_n':len(shared-inj),'own_pool_threshold':threshold(own),'shared_pool_threshold':threshold(shared-inj),'recorded_threshold':r['thresholds'].get(n)})
result['e7b']={'calibration_comparison':rows,'changed_thresholds':sum(x['own_pool_threshold']!=x['recorded_threshold'] for x in rows),'conclusion':'Implementation calibrates on all-nine shared pool, contrary to own-pool prereg wording. No frozen outputs changed.'}
paths=['experiments/e7b/PREREG.md','experiments/e7b/run/measure.py','experiments/e7b/results/e7_result.json','experiments/e6/freeze/sources.json','scripts/verify_e6.py']
result['input_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
(HERE/'audit-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='input_sha256'},indent=2))
