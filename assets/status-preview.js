(function () {
  'use strict';
  var target = document.getElementById('preview-status');
  var fixture = {id:1,created_at:'2026-10-12T13:00:00Z',updated_at:'2026-10-12T13:05:00Z',head_branch:'main',event:'schedule',status:'completed',conclusion:'failure',head_sha:'f2249c113335feb8b2a3ccb9e4cd9951e002592a',html_url:'https://github.com/Cubits11/cubits11.github.io/actions/runs/38311805955'};
  document.getElementById('preview-failed').addEventListener('click', function () {
    CheckStatus.render(target, CheckStatus.fromRuns({workflow_runs:[fixture]}, Date.parse('2026-10-17T16:00:00Z')));
  });
  document.getElementById('preview-unavailable').addEventListener('click', function () {
    CheckStatus.load(target, function () {return Promise.reject(new Error('Synthetic unavailable request'));});
  });
})();
