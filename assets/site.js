/* Shared progressive enhancement for the site shell.

   The navigation remains visible without JavaScript. When JavaScript is
   available, this script adds a real mobile menu control instead of asking
   people to discover a tiny, horizontally scrolling list of links. */
(function () {
  'use strict';

  var root = document.documentElement;
  var header = document.querySelector('.site-head');
  var nav = header && header.querySelector('.site-nav');
  if (!header || !nav) return;

  root.classList.add('js');
  root.classList.add('nav-enhanced');
  if (!nav.id) nav.id = 'site-navigation';

  var toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'nav-toggle mono';
  toggle.setAttribute('aria-controls', nav.id);
  toggle.setAttribute('aria-expanded', 'false');
  toggle.setAttribute('aria-label', 'Open site navigation');
  toggle.innerHTML = '<span aria-hidden="true">Menu</span>';
  header.querySelector('.container').insertBefore(toggle, nav);

  function closeMenu(returnFocus) {
    nav.classList.remove('nav-open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Open site navigation');
    if (returnFocus) toggle.focus();
  }

  function openMenu() {
    nav.classList.add('nav-open');
    toggle.setAttribute('aria-expanded', 'true');
    toggle.setAttribute('aria-label', 'Close site navigation');
  }

  toggle.addEventListener('click', function () {
    if (nav.classList.contains('nav-open')) closeMenu(false);
    else openMenu();
  });

  nav.addEventListener('click', function (event) {
    if (event.target.closest('a')) closeMenu(false);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && nav.classList.contains('nav-open')) {
      closeMenu(true);
    }
  });

  document.addEventListener('click', function (event) {
    if (nav.classList.contains('nav-open')
        && !header.contains(event.target)) closeMenu(false);
  });

  window.addEventListener('resize', function () {
    if (window.matchMedia('(min-width: 701px)').matches) closeMenu(false);
  });
}());
