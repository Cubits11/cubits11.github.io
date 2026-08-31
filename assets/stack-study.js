/* Stack Study Preflight

   This client-side calculator is deliberately narrow. It evaluates finite
   full-exposure static aggregates and makes the finite Frechet bounds visible.
   It does not estimate deployed-route or adaptive risk from those aggregates.
*/
(function () {
  'use strict';

  var form = document.getElementById('study-form');
  if (!form) return;

  var modeInputs = Array.prototype.slice.call(
    document.querySelectorAll('input[name="execution-mode"]'));
  var guidance = document.getElementById('mode-guidance');
  var staticMetrics = document.getElementById('static-metrics');
  var staticChecks = document.getElementById('static-checks');
  var guardRows = document.getElementById('guard-rows');
  var addGuard = document.getElementById('add-guard');
  var status = document.getElementById('preflight-status');
  var resultGrid = document.getElementById('result-grid');
  var packet = document.getElementById('packet');
  var copyPacket = document.getElementById('copy-packet');
  var resultMode = document.getElementById('result-mode');
  var resultModeNote = document.getElementById('result-mode-note');
  var resultBounds = document.getElementById('result-bounds');
  var resultBoundsNote = document.getElementById('result-bounds-note');
  var resultAllmiss = document.getElementById('result-allmiss');
  var resultAllmissNote = document.getElementById('result-allmiss-note');

  var MODE = {
    shadow_full_exposure: {
      title: 'Static full exposure',
      guidance: 'Static mode is selected. Enter a shared positive population and per-guard catches; a union is optional but is required to identify the observed static all-miss count.'
    },
    deployed_route: {
      title: 'Deployed route',
      guidance: 'Route mode is selected. This page will record a protocol shell, but it will not turn static component counts into a deployed-route result. Retain stage sequence, blocks, missingness, and terminal outcomes instead.'
    },
    adaptive_holdout: {
      title: 'Adaptive holdout',
      guidance: 'Adaptive mode is selected. This page will not calculate resilience from static aggregates. A real packet must name the attacker access model, budget, feedback channel, holdout policy, and terminal outcome.'
    }
  };

  function selectedMode() {
    var selected = modeInputs.filter(function (input) { return input.checked; })[0];
    return selected ? selected.value : 'shadow_full_exposure';
  }

  function setStatus(message, kind) {
    // An error a screen reader may never hear is not an error message. Errors
    // interrupt (assertive + role=alert); ordinary progress stays polite.
    var isError = kind === 'error';
    status.setAttribute('role', isError ? 'alert' : 'status');
    status.setAttribute('aria-live', isError ? 'assertive' : 'polite');
    status.textContent = message;
    status.className = 'preflight-status' + (kind ? ' ' + kind : '');
  }

  function integer(value) {
    if (value === '' || value === null || value === undefined) return null;
    var raw = String(value).trim();
    // Plain decimal only. Number() would otherwise accept '0x10', '1e3' and
    // '  12  ' as counts, and none of those is something a person typed as a
    // number of items.
    if (!/^[+-]?[0-9]+$/.test(raw)) return null;
    var n = Number(raw);
    // Beyond 2^53-1 integer arithmetic silently loses precision, so n - sum
    // and n - max stop being the bounds this tool claims to compute.
    return Number.isSafeInteger(n) ? n : null;
  }

  function value(id) {
    var element = document.getElementById(id);
    return element ? element.value.trim() : '';
  }

  function escapeText(raw) {
    return String(raw).replace(/[\r\n]+/g, ' ').trim();
  }

  function percent(numerator, denominator) {
    return (100 * numerator / denominator).toFixed(1) + '%';
  }

  function guardData() {
    return Array.prototype.slice.call(guardRows.querySelectorAll('.guard-row'))
      .map(function (row, index) {
        var label = row.querySelector('[name="guard-label"]').value.trim();
        var config = row.querySelector('[name="guard-config"]').value.trim();
        var catches = integer(row.querySelector('[name="guard-catches"]').value);
        return {
          label: label || 'Guard ' + (index + 1),
          config: config || 'not recorded',
          catches: catches
        };
      });
  }

  function removeGuard(event) {
    var button = event.target.closest('.remove-guard');
    if (!button) return;
    var rows = guardRows.querySelectorAll('.guard-row');
    if (rows.length <= 2) {
      setStatus('Keep at least two components: a one-column result is not a stack measurement.', 'error');
      return;
    }
    button.closest('.guard-row').remove();
    refreshGuardLabels();
    invalidatePacket();
  }

  function refreshGuardLabels() {
    Array.prototype.slice.call(guardRows.querySelectorAll('.guard-row')).forEach(function (row, index) {
      var n = index + 1;
      var label = row.querySelector('[name="guard-label"]');
      var config = row.querySelector('[name="guard-config"]');
      var catches = row.querySelector('[name="guard-catches"]');
      var remove = row.querySelector('.remove-guard');
      label.setAttribute('aria-label', 'Guard ' + n + ' name');
      config.setAttribute('aria-label', 'Guard ' + n + ' version or threshold');
      catches.setAttribute('aria-label', 'Guard ' + n + ' catches among positives');
      remove.setAttribute('aria-label', 'Remove Guard ' + n);
    });
  }

  function addGuardRow() {
    var n = guardRows.querySelectorAll('.guard-row').length + 1;
    var row = document.createElement('tr');
    row.className = 'guard-row';
    row.innerHTML = '<td><input aria-label="Guard ' + n + ' name" name="guard-label" type="text" autocomplete="off" placeholder="Guard ' + String.fromCharCode(64 + Math.min(n, 26)) + '"></td>'
      + '<td><input aria-label="Guard ' + n + ' version or threshold" name="guard-config" type="text" autocomplete="off" placeholder="Version / threshold"></td>'
      + '<td><input aria-label="Guard ' + n + ' catches among positives" name="guard-catches" type="number" inputmode="numeric" min="0" step="1" placeholder="0"></td>'
      + '<td><button class="remove-guard" type="button" aria-label="Remove Guard ' + n + '">Remove</button></td>';
    guardRows.appendChild(row);
    row.querySelector('[name="guard-label"]').focus();
    invalidatePacket();
  }

  function modeChanged() {
    var mode = selectedMode();
    guidance.textContent = MODE[mode].guidance;
    staticMetrics.hidden = mode !== 'shadow_full_exposure';
    staticChecks.hidden = mode !== 'shadow_full_exposure';
    invalidatePacket();
    if (mode === 'shadow_full_exposure') {
      setStatus('Static mode selected. A union is optional; without it, the result remains an identified set.', '');
    } else {
      setStatus('This mode intentionally emits no static stack result from marginal inputs.', '');
    }
  }

  function invalidatePacket() {
    resultGrid.hidden = true;
    packet.hidden = true;
    packet.textContent = '';
    copyPacket.disabled = true;
  }

  function protocolLines(mode) {
    var title = escapeText(value('study-name')) || 'Untitled local preflight';
    var sut = escapeText(value('sut-label')) || 'not declared';
    var event = escapeText(value('event-definition')) || 'not declared';
    var configuration = escapeText(value('configuration')) || 'not recorded';
    var route = escapeText(value('route-id')) || 'not recorded';
    var access = document.getElementById('release-access').value;
    return [
      'STACK STUDY PREFLIGHT v0.1 — DRAFT, LOCAL ONLY',
      'Study: ' + title,
      'Observation mode: ' + mode,
      'Declared SUT: ' + sut,
      'Positive event: ' + event,
      'Version/configuration/route digest: ' + configuration,
      'Route or protocol identifier: ' + route,
      'Evidence access posture: ' + access
    ];
  }

  function requireDeclaration(n) {
    var errors = [];
    if (!value('sut-label')) errors.push('Declare the system under test.');
    if (!value('event-definition')) errors.push('Declare the positive event definition.');
    if (n === null || n < 1) errors.push('Enter a positive integer denominator.');
    return errors;
  }

  function renderPacket(lines) {
    packet.textContent = lines.join('\n');
    packet.hidden = false;
    copyPacket.disabled = false;
  }

  function buildNonStaticPacket(mode) {
    var n = integer(value('denominator'));
    var errors = requireDeclaration(n);
    if (!value('route-id')) errors.push('Name a route or protocol identifier for this observation mode.');
    if (errors.length) {
      invalidatePacket();
      setStatus(errors.join(' '), 'error');
      return;
    }
    var modeTitle = MODE[mode].title;
    resultMode.textContent = modeTitle;
    resultModeNote.textContent = 'Protocol shell only; no static result is emitted.';
    resultBounds.textContent = 'Not computed';
    resultBoundsNote.textContent = 'Marginal-only bounds do not answer this observation mode.';
    resultAllmiss.textContent = 'Not computed';
    resultAllmissNote.textContent = mode === 'deployed_route'
      ? 'Retain ordered stage observations and a terminal outcome.'
      : 'Retain attacker model, budget, feedback, and holdout outcomes.';
    resultGrid.hidden = false;
    var lines = protocolLines(mode);
    lines.push('', 'RESULT STATUS: HOLD — ' + modeTitle.toUpperCase() + ' IS NOT REDUCED TO STATIC AGGREGATES.');
    if (mode === 'deployed_route') {
      lines.push('Required next evidence: route_id, ordered stage outcomes, block/intervention semantics, missingness policy, terminal outcome, false-positive burden, and timing/cost policy.');
    } else {
      lines.push('Required next evidence: attacker access model, budget, feedback channel, mutation/retry policy, sealed holdout, and terminal outcome.');
    }
    lines.push('Non-claim: this draft is not a result about deployed safety or robustness.');
    renderPacket(lines);
    setStatus('Protocol shell built. The tool correctly withheld a numerical stack result for this mode.', 'ok');
  }

  function buildStaticPacket() {
    var n = integer(value('denominator'));
    var errors = requireDeclaration(n);
    var guards = guardData();
    var incomplete = guards.filter(function (guard) { return guard.catches === null; });
    if (!document.getElementById('same-items').checked) errors.push('Confirm that every guard used the same named population and event.');
    if (!document.getElementById('full-exposure').checked) errors.push('Confirm full exposure, or switch to deployed-route mode.');
    if (guards.length < 2) errors.push('Enter at least two guards.');
    if (incomplete.length) errors.push('Enter an integer catch count for every listed guard.');
    guards.forEach(function (guard) {
      if (guard.catches !== null && (guard.catches < 0 || guard.catches > n)) {
        errors.push(guard.label + ' has a catch count outside 0–' + n + '.');
      }
    });
    if (errors.length) {
      invalidatePacket();
      setStatus(errors.join(' '), 'error');
      return;
    }

    var catches = guards.map(function (guard) { return guard.catches; });
    var sum = catches.reduce(function (total, catchCount) { return total + catchCount; }, 0);
    var max = Math.max.apply(Math, catches);
    var lower = Math.max(0, n - sum);
    var upper = n - max;
    var unionRaw = value('union-catches');
    var union = integer(unionRaw);
    if (unionRaw !== '' && union === null) errors.push('Union catches must be an integer when supplied.');
    if (union !== null && (union < max || union > Math.min(n, sum))) {
      errors.push('Union catches must be at least the largest guard count and no more than the denominator or sum of guard counts.');
    }
    if (errors.length) {
      invalidatePacket();
      setStatus(errors.join(' '), 'error');
      return;
    }

    resultMode.textContent = 'Static full exposure';
    resultModeNote.textContent = n + ' shared positive items; every listed guard saw every item.';
    resultBounds.textContent = lower + '–' + upper;
    resultBoundsNote.textContent = percent(lower, n) + '–' + percent(upper, n) + ' possible all-miss from the listed marginals alone.';

    var lines = protocolLines('shadow_full_exposure');
    lines.push('', 'STATIC OBSERVATION CONTRACT');
    lines.push('Population: ' + n + ' positive items on a shared item set.');
    lines.push('Same-items confirmation: yes.');
    lines.push('Full-exposure confirmation: yes.');
    lines.push('Per-guard catches:');
    guards.forEach(function (guard) {
      lines.push('- ' + escapeText(guard.label) + ' [' + escapeText(guard.config) + ']: ' + guard.catches + ' / ' + n + ' (' + percent(guard.catches, n) + ')');
    });
    lines.push('Marginal-only all-miss identified set: ' + lower + '–' + upper + ' / ' + n + ' (' + percent(lower, n) + '–' + percent(upper, n) + ').');

    if (union === null) {
      resultAllmiss.textContent = 'Not identified';
      resultAllmissNote.textContent = 'No observed union entered. The interval above is the exact finite feasible set, not a missing calculation.';
      lines.push('Observed union: NOT RETAINED OR NOT ENTERED.');
      lines.push('Observed static all-miss: NOT IDENTIFIED FROM MARGINALS.');
      lines.push('Next measurement: retain the union count or per-item outcomes for this exact full-exposure evaluation.');
      setStatus('Packet built: the marginal-only identified set is exact, and the observed static all-miss remains intentionally unresolved.', 'ok');
    } else {
      var allMiss = n - union;
      resultAllmiss.textContent = allMiss + ' / ' + n;
      resultAllmissNote.textContent = percent(allMiss, n) + ' all-miss; observed union ' + union + ' / ' + n + ' (' + percent(union, n) + ').';
      lines.push('Observed static union: ' + union + ' / ' + n + ' (' + percent(union, n) + ').');
      lines.push('Observed static all-miss: ' + allMiss + ' / ' + n + ' (' + percent(allMiss, n) + ').');
      lines.push('Interpretation: this exact all-miss result is identified only for this declared full-exposure static evaluation.');
      setStatus('Packet built: union and static all-miss are internally feasible for the declared aggregate counts.', 'ok');
    }
    lines.push('', 'NON-CLAIMS');
    lines.push('- This does not establish terminal deployed-route risk, adaptive resilience, general safety, or causal complementarity.');
    lines.push('- The marginal-only interval is a sharp finite feasibility bound, not a confidence interval or an independence estimate.');
    renderPacket(lines);
    resultGrid.hidden = false;
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var mode = selectedMode();
    if (mode === 'shadow_full_exposure') buildStaticPacket();
    else buildNonStaticPacket(mode);
  });

  addGuard.addEventListener('click', addGuardRow);
  guardRows.addEventListener('click', removeGuard);
  form.addEventListener('input', function () {
    if (!packet.hidden) {
      invalidatePacket();
      setStatus('Inputs changed. Build a fresh packet before copying it.', '');
    }
  });
  modeInputs.forEach(function (input) { input.addEventListener('change', modeChanged); });

  copyPacket.addEventListener('click', function () {
    var text = packet.textContent;
    if (!text) return;
    function done(ok) {
      setStatus(ok ? 'Draft packet copied locally. Review and scope it before sharing.' : 'Copy failed. Select the draft packet and copy it manually.', ok ? 'ok' : 'error');
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
    } else {
      done(false);
    }
  });

  modeChanged();
  refreshGuardLabels();
}());
