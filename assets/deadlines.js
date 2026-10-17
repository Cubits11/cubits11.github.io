/* Labels only: an overdue review never changes a scientific truth status. */
(function () {
  'use strict';
  var parts = new Intl.DateTimeFormat('en-CA', {timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  var values = {}; parts.forEach(function(part){values[part.type]=part.value;});
  var today = values.year + '-' + values.month + '-' + values.day;
  document.querySelectorAll('[data-deadline]').forEach(function (row) {
    var label = row.querySelector('[data-deadline-label]');
    if (!label) return;
    var due = row.dataset.deadline;
    if (row.dataset.disposedOn && row.dataset.disposedOn <= today) label.textContent = 'DISPOSITION RECORDED';
    else if (due < today) label.textContent = row.dataset.deadlineKind === 'claim-review' ? 'OVERDUE — REVIEW REQUIRED' : 'OVERDUE';
    else label.textContent = due === today ? 'DUE TODAY' : 'SCHEDULED';
  });
})();
