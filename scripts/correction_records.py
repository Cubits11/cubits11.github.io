"""Shared rendering of the dated E6/E7B dispositions; no estimator changes."""
import html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
RECORD=ROOT/'corrections/records/2026-09-10.json'
def records():
    return json.loads(RECORD.read_text())
def notice():
    return '<aside class="snapshot-note" aria-label="Current correction status"><strong>Correction status · 2026-09-10:</strong> E6’s fixed-marginal range and E7B’s preregistration-conforming claim are <strong>rejected</strong>. Original outputs are retained for audit. <a href="/corrections/#research-dispositions">Read the dispositions</a>. <a href="/overlap/">Start with a constructed example</a>.</aside>'
def sections():
    doc=records();parts=[]
    for r in doc['records']:
        esc=html.escape
        parts.append(f'<article id="{esc(r["anchor"])}"><h3>{esc(r["title"])}</h3><p><strong>{esc(r["claim_id"])} · {esc(r["disposition"])} · {esc(doc["recorded_on"])}</strong></p><p>{esc(r["summary"])}</p><p>{esc(r["basis"])}</p><p><a href="/{esc(r["artifact"])}">Full disposition beside original artifacts</a> · <a href="/ledger/#{esc(r["claim_id"])}">Registry and historical assertion</a></p></article>')
    return '<section class="zone" id="research-dispositions" aria-labelledby="dispositions-h"><h2 id="dispositions-h">Research claim dispositions</h2><p>The previous coupling campaign is superseded for launch purposes. These are corrections to this repository’s analyses. Frozen inputs, estimators and outputs remain unchanged. CORRECT records the history transition while REJECT records the disposition; the claim IDs remain addressable.</p>'+''.join(parts)+'<p><a href="/corrections/records/2026-09-10-preserved-inputs.json">Preserved-byte manifest</a> · <a href="/distribution/research-2026-09-10/audit-results.json">Reproducible audit</a> · <a href="/overlap/">Constructed teaching example</a></p></section>'
