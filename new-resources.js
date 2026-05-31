/* OBP "New Resources" dynamic feed.
 *
 * Fetches /data/new-resources.json and replaces the static fallback inside
 * <ul id="new-resources"> with the most recent entries by pubdate.
 *
 * Fallback: if fetch fails or the JSON is malformed, the static HTML inside
 * the <ul> remains visible. Graceful degradation by design.
 *
 * Usage:
 *   <ul id="new-resources" data-limit="5">
 *     <!-- static HTML fallback here -->
 *   </ul>
 *   <script defer src="/new-resources.js"></script>
 *
 * Optional attributes on the <ul>:
 *   data-limit="5"           number of entries to show (default 5)
 *   data-show-description    if present, renders description as subtext
 */
(function () {
  'use strict';

  var ENDPOINT = '/data/new-resources.json';
  var DEFAULT_LIMIT = 5;
  var FETCH_TIMEOUT_MS = 4000;

  function escapeHTML(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function isHttpUrl(u) {
    return typeof u === 'string' && /^https?:\/\//i.test(u);
  }

  function renderEntry(entry, showDescription) {
    var icon = escapeHTML(entry.icon || '');
    var label = escapeHTML(entry.label || '');
    var url = isHttpUrl(entry.url) ? entry.url : '';
    if (!url || !label) return '';
    var desc = '';
    if (showDescription && entry.description) {
      desc = '<div style="color:#7d8590;font-size:0.85em;margin-top:0.15rem">'
        + escapeHTML(entry.description)
        + '</div>';
    }
    return '<li>'
      + '<a href="' + escapeHTML(url) + '" style="color:#c9d1d9;text-decoration:none">'
      + icon + ' ' + label
      + '</a>'
      + desc
      + '</li>';
  }

  function applyResources(data, container) {
    if (!data || !Array.isArray(data.resources)) return;

    var limitAttr = container.getAttribute('data-limit');
    var limit = limitAttr ? parseInt(limitAttr, 10) : DEFAULT_LIMIT;
    if (!isFinite(limit) || limit <= 0) limit = DEFAULT_LIMIT;

    var showDescription = container.hasAttribute('data-show-description');

    var sorted = data.resources
      .filter(function (r) { return r && r.pubdate && r.label && r.url; })
      .slice()
      .sort(function (a, b) {
        if (a.pubdate < b.pubdate) return 1;
        if (a.pubdate > b.pubdate) return -1;
        return 0;
      })
      .slice(0, limit);

    if (sorted.length === 0) return;

    var html = '';
    for (var i = 0; i < sorted.length; i++) {
      html += renderEntry(sorted[i], showDescription);
    }
    if (html) {
      container.innerHTML = html;
    }
  }

  function run() {
    var container = document.getElementById('new-resources');
    if (!container) return;

    var controller = ('AbortController' in window) ? new AbortController() : null;
    var timeoutId = null;
    if (controller) {
      timeoutId = setTimeout(function () { controller.abort(); }, FETCH_TIMEOUT_MS);
    }

    var opts = controller ? { signal: controller.signal, cache: 'no-cache' } : { cache: 'no-cache' };

    fetch(ENDPOINT, opts)
      .then(function (r) {
        if (timeoutId) clearTimeout(timeoutId);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) { applyResources(data, container); })
      .catch(function () { /* fallback static HTML stays */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
