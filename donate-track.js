/* Donation attribution for /donate.html (added 2026-09-28).
   1. Fires GA4 begin_checkout with the tier's real amount when a donate button is clicked.
   2. Appends client_reference_id to the Stripe Payment Link so the completed Checkout Session
      carries the GA client id and, when present, the Google Ads click id (gclid). No personal
      data: both are pseudonymous ids the browser already holds.
   Stripe allows only [A-Za-z0-9_-] in client_reference_id (max 200), so dots become underscores. */
(function () {
  var TIERS = {
    '28EdR25i330h6nN2LiaVa02': { value: 10, kind: 'one_time' },
    'cNi9AMcKv30h3bBdpWaVa03': { value: 25, kind: 'one_time' },
    '3cI7sEaCn9oF13tfy4aVa04': { value: 50, kind: 'one_time' },
    '7sY7sE7qbeIZdQfclSaVa05': { value: 0, kind: 'one_time_custom' },
    '6oU6oAbGr6cteUj3PmaVa06': { value: 5, kind: 'monthly' },
    'dRm14g4dZ30h8vV99GaVa07': { value: 10, kind: 'monthly' },
    '00w14gbGr9oFh2r2LiaVa08': { value: 25, kind: 'monthly' }
  };

  function cookie(name) {
    var m = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.$?*|{}()[\]\\/+^]/g, '\\$&') + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }
  function clean(s) { return String(s || '').replace(/[^A-Za-z0-9_-]/g, '_'); }

  function refId() {
    var ga = cookie('_ga').split('.').slice(-2).join('_');   // GA1.1.<rand>.<ts> -> <rand>_<ts>
    var aw = cookie('_gcl_aw').split('.').pop() || '';       // GCL.<ts>.<gclid> -> <gclid>
    var q = new URLSearchParams(location.search).get('gclid') || '';
    var gclid = q || aw;
    return clean('ga_' + (ga || 'none') + '__g_' + (gclid || 'none')).slice(0, 200);
  }

  function tierFor(href) {
    var id = (href.split('?')[0].split('/').pop() || '');
    return { id: id, t: TIERS[id] };
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href*="stripe.com/"]');
    if (!a) return;
    var f = tierFor(a.getAttribute('href'));
    if (!f.t) return;
    try {
      var u = new URL(a.href);
      u.searchParams.set('client_reference_id', refId());
      a.href = u.toString();
    } catch (err) {}
    if (typeof gtag === 'function') {
      gtag('event', 'begin_checkout', {
        currency: 'USD', value: f.t.value, transport_type: 'beacon',
        items: [{ item_id: f.id, item_name: 'donation_' + f.t.kind, price: f.t.value, quantity: 1 }]
      });
    }
  }, true);
})();
