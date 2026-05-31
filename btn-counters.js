/* BTN dynamic counter client.
 * Fetches https://1328f.com/data/counters.json and populates every element
 * with a [data-counter="KEY"] OR [data-obp-c="KEY"] attribute on the page.
 *
 * Fallback: if fetch fails or a key is missing, the element's original
 * hardcoded text remains visible. Graceful degradation by design.
 *
 * Usage in HTML (either attribute name works — data-obp-c is canonical
 * network-wide, data-counter is the original 2025 naming):
 *   <span data-obp-c="domains">180+</span>
 *   <span data-obp-c="pages">22,000+</span>
 *   <span data-obp-c="spend_research">$508+</span>
 *   <span data-obp-c="recap_cases">549+</span>
 *   <span data-obp-c="recap_documents">3,100+</span>
 *
 * Static fallback values are kept in sync with counters.json by
 * scripts/sync_counters_to_static_html.py on every counters.json update.
 *
 * Include once per site:
 *   <script defer src="https://openbankruptcyproject.org/btn-counters.js"></script>
 */
(function () {
  'use strict';

  var ENDPOINT = 'https://1328f.com/data/counters.json';

  function applyCounters(data) {
    if (!data || typeof data !== 'object') return;
    var nodes = document.querySelectorAll('[data-counter], [data-obp-c]');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var key = el.getAttribute('data-obp-c') || el.getAttribute('data-counter');
      if (!key) continue;
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        var val = data[key];
        if (val !== null && val !== undefined) {
          el.textContent = String(val);
        }
      }
    }
    // Optional: expose last-updated timestamp
    var tsNodes = document.querySelectorAll('[data-counter-updated]');
    for (var j = 0; j < tsNodes.length; j++) {
      if (data.last_updated) {
        tsNodes[j].textContent = data.last_updated.replace('T', ' ').replace('Z', ' UTC');
      }
    }
  }

  function run() {
    try {
      var controller = ('AbortController' in window) ? new AbortController() : null;
      var timeout = null;
      if (controller) {
        timeout = setTimeout(function () { controller.abort(); }, 4000);
      }
      fetch(ENDPOINT, {
        cache: 'default',
        signal: controller ? controller.signal : undefined
      })
        .then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .then(function (d) {
          if (timeout) clearTimeout(timeout);
          applyCounters(d);
        })
        .catch(function () {
          /* graceful: hardcoded fallbacks remain visible */
        });
    } catch (e) {
      /* noop */
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
