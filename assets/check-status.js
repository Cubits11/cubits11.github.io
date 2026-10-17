/* Public workflow observations. A request failure is UNKNOWN, never a pass. */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root.document) {
    root.CheckStatus = api;
    api.mount(root.document);
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  var HISTORY = 'https://github.com/Cubits11/cubits11.github.io/actions/workflows/verify.yml';
  var ENDPOINT = 'https://api.github.com/repos/Cubits11/cubits11.github.io/actions/workflows/verify.yml/runs?branch=main&per_page=30';
  var DAY = 86400000;

  function unknown(reason) {
    return {state: 'UNKNOWN', reason: reason, url: HISTORY};
  }
  function validRun(run) {
    return run && run.head_branch === 'main' && run.event !== 'pull_request' &&
      /^[a-f0-9]{40}$/.test(run.head_sha || '') &&
      /^https:\/\/github\.com\/Cubits11\/cubits11\.github\.io\/actions\/runs\/\d+$/.test(run.html_url || '') &&
      Number.isFinite(Date.parse(run.created_at)) && Number.isFinite(Date.parse(run.updated_at));
  }
  function fromRuns(payload, now) {
    now = now == null ? Date.now() : now;
    if (!payload || !Array.isArray(payload.workflow_runs)) return unknown('GitHub returned no usable run list.');
    if (payload.workflow_runs.some(function (run) { return !run || !run.head_branch || !run.event; }))
      return unknown('GitHub returned a run whose identity could not be checked.');
    var runs = payload.workflow_runs.filter(function (run) { return run.head_branch === 'main' && run.event !== 'pull_request'; });
    if (runs.some(function (run) { return !Number.isFinite(Date.parse(run.created_at)); }))
      return unknown('GitHub returned a run whose date could not be checked.');
    runs.sort(function (a, b) {
      return Date.parse(b.created_at) - Date.parse(a.created_at) || Number(b.id) - Number(a.id);
    });
    if (!runs.length) return unknown('No usable full main-branch check was returned.');
    var latest = runs[0];
    if (!validRun(latest)) return unknown('The newest run could not be verified. No older pass is substituted.');
    var age = now - Date.parse(latest.created_at);
    if (age < -5 * 60000) return unknown('The run date is ahead of this device clock.');
    if (age > 8 * DAY) return unknown('The latest full run is more than eight days old. Inspect the history.');
    var state;
    if (['queued', 'in_progress', 'requested', 'waiting', 'pending'].indexOf(latest.status) !== -1) state = 'RUNNING';
    else if (latest.status !== 'completed') return unknown('GitHub returned an unrecognized run state.');
    else if (latest.conclusion === 'success') state = 'PASSED';
    else if (['failure', 'timed_out', 'action_required', 'startup_failure'].indexOf(latest.conclusion) !== -1) state = 'FAILED';
    else return unknown('The latest run did not finish with a pass or failure.');
    var success = runs.find(function (run) { return validRun(run) && run.status === 'completed' && run.conclusion === 'success'; });
    return {state: state, date: latest.created_at.slice(0, 10), revision: latest.head_sha,
      url: latest.html_url, lastSuccess: success ? success.created_at.slice(0, 10) : null, returnedRuns: runs.length,
      checkedAt: new Date(now).toISOString()};
  }
  function render(container, model) {
    var doc = container.ownerDocument;
    container.replaceChildren();
    container.dataset.checkState = model.state.toLowerCase();
    var label = doc.createElement('strong');
    label.textContent = 'Latest full check: ' + model.state;
    container.appendChild(label);
    if (model.date) container.appendChild(doc.createTextNode(' — ' + model.date));
    if (model.revision) {
      var revision = doc.createElement('code');
      revision.textContent = model.revision.slice(0, 7);
      revision.title = model.revision;
      container.appendChild(doc.createTextNode(' · revision '));
      container.appendChild(revision);
    }
    if (model.lastSuccess) container.appendChild(doc.createTextNode('. Last successful: ' + model.lastSuccess + '. '));
    else if (model.returnedRuns) container.appendChild(doc.createTextNode('. Last successful: not found in the ' + model.returnedRuns + ' returned main-branch runs. '));
    else container.appendChild(doc.createTextNode('. '));
    var link = doc.createElement('a');
    link.href = model.url || HISTORY;
    link.textContent = model.revision ? 'Inspect the run' : 'Inspect check history';
    container.appendChild(link);
    if (model.reason) {
      var reason = doc.createElement('span');
      reason.className = 'check-detail'; reason.textContent = model.reason;
      container.appendChild(reason);
    }
    if (model.checkedAt) {
      var time = doc.createElement('small');
      time.className = 'check-detail';
      time.textContent = 'Read from GitHub ' + model.checkedAt.replace('T', ' ').replace(/\.\d+Z$/, ' UTC') + '. Workflow result, not scientific validation.';
      container.appendChild(time);
    }
  }
  async function load(container, request, now) {
    render(container, unknown('Checking GitHub.'));
    try {
      var response = await request(ENDPOINT, {headers: {Accept: 'application/vnd.github+json'}, cache: 'no-store', signal: AbortSignal.timeout(8000)});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var model = fromRuns(await response.json(), now);
      render(container, model); return model;
    } catch (error) {
      var unavailable = unknown('GitHub could not be checked. No passing result is inferred.');
      render(container, unavailable); return unavailable;
    }
  }
  function mount(doc) {
    doc.querySelectorAll('[data-live-check], #public-check-status').forEach(function (container) {
      load(container, fetch.bind(globalThis));
    });
  }
  return {fromRuns: fromRuns, unknown: unknown, render: render, load: load, mount: mount};
});
