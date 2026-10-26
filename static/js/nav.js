/* nav.js — view switcher for the EcoLifyBuddy shell (no build step).
 * Primary pages are fetched from /partials/<name>; the legacy cleanliness UI
 * lives in #view-legacy inside index.html and is only shown on its own tab.
 */
(function () {
  'use strict';

  var DEFAULT_VIEW = 'visitor_overview';
  var LEGACY_VIEW = 'legacy';
  var cache = {};

  var appView = document.getElementById('view-app');
  var legacyView = document.getElementById('view-legacy');
  var navButtons = document.querySelectorAll('[data-view]');

  function setActive(view) {
    navButtons.forEach(function (btn) {
      var active = btn.getAttribute('data-view') === view;
      btn.classList.toggle('bg-brand-50', active);
      btn.classList.toggle('dark:bg-brand-900/40', active);
      btn.classList.toggle('text-brand-700', active);
      btn.classList.toggle('dark:text-brand-300', active);
      btn.classList.toggle('font-bold', active);
      if (active) btn.setAttribute('aria-current', 'page');
      else btn.removeAttribute('aria-current');
    });
  }

  function toggleLegacyControls(show) {
    document.querySelectorAll('[data-legacy-only]').forEach(function (el) {
      // '' restores the element's own class-based display (e.g. flex)
      el.style.display = show ? '' : 'none';
    });
  }

  function loadPartial(name) {
    if (cache[name]) return Promise.resolve(cache[name]);
    return fetch('/partials/' + encodeURIComponent(name), { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      })
      .then(function (html) { cache[name] = html; return html; });
  }

  function show(view) {
    var isLegacy = view === LEGACY_VIEW;
    legacyView.classList.toggle('hidden', !isLegacy);
    appView.classList.toggle('hidden', isLegacy);
    toggleLegacyControls(isLegacy);
    setActive(view);

    if (isLegacy) return;
    appView.innerHTML = '<p class="text-sm text-slate-500 p-4">Loading…</p>';
    loadPartial(view)
      .then(function (html) {
        appView.innerHTML = html;
        // Scripts inside fetched partials do not execute through innerHTML.
        // Recreate them after insertion so each view can initialize its controls.
        Array.prototype.forEach.call(appView.querySelectorAll('script'), function (script) {
          var replacement = document.createElement('script');
          Array.prototype.forEach.call(script.attributes, function (attribute) {
            replacement.setAttribute(attribute.name, attribute.value);
          });
          replacement.textContent = script.textContent;
          script.parentNode.replaceChild(replacement, script);
        });
      })
      .catch(function () {
        appView.innerHTML = '<p class="text-sm text-red-600 p-4">Could not load this page.</p>';
      });
  }

  function route() {
    var view = (location.hash || '').replace('#', '') || DEFAULT_VIEW;
    var known = Array.prototype.some.call(navButtons, function (b) {
      return b.getAttribute('data-view') === view;
    });
    show(known ? view : DEFAULT_VIEW);
  }

  navButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      location.hash = btn.getAttribute('data-view');
    });
  });
  window.addEventListener('hashchange', route);
  route();
})();
