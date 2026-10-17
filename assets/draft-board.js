/* Observe branch movement without promoting a draft to a published result. */
(function () {
  'use strict';
  document.querySelectorAll('[data-draft-revision]').forEach(async function (article) {
    var message = document.createElement('p');
    message.setAttribute('role', 'status'); message.textContent = 'Current repository status: UNKNOWN — checking GitHub.';
    article.appendChild(message);
    try {
      var published = article.dataset.publicationState.indexOf('Published') === 0;
      var comparison = published ? article.dataset.draftRevision + '...main' : 'main...claude/e9-result';
      var response = await fetch('https://api.github.com/repos/Cubits11/cubits11.github.io/compare/' + comparison, {cache:'no-store',headers:{Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(8000)});
      if (!response.ok) throw Error('unavailable');
      var data = await response.json();
      var sha = data.commits && data.commits.length ? data.commits[data.commits.length - 1].sha : null;
      if (!Number.isInteger(data.ahead_by) || !Number.isInteger(data.behind_by) ||
          ['ahead','behind','diverged','identical'].indexOf(data.status) === -1) throw Error('invalid comparison');
      if (published) {
        message.textContent = ['ahead','identical'].indexOf(data.status) !== -1 ? 'Published revision remains in main. Publication does not establish independent replication or E2 completion.' : 'Main no longer descends from the recorded publication revision. Inspect the current repository before relying on this snapshot.';
        return;
      }
      if (data.ahead_by === 0) message.textContent = 'Branch has no commits ahead of main. Review the publication status; this observation does not itself release a result.';
      else if (sha === article.dataset.draftRevision) message.textContent = 'Current branch: ' + data.ahead_by + ' commits ahead of main; pinned draft still matches the branch. Pending review.';
      else message.textContent = 'Branch changed since this pinned draft. Inspect the current branch before relying on the observation above. Pending review.';
    } catch (error) {
      message.textContent = 'Current repository status: UNKNOWN. GitHub could not be checked; the dated pinned result remains available.';
    }
  });
})();
