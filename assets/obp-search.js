/* OBP search widget — drop-in autocomplete that hits the Cloudflare Worker.
 *
 * Usage on any page:
 *   <div class="obp-search" data-program="ppp"></div>
 *   <script src="/assets/obp-search.js" defer></script>
 *
 * data-program is optional. Values: "ppp" | "eidl" | "all" (default).
 * data-state optional. Values: two-letter USPS code (e.g. "MO").
 *
 * Styling pulled from /assets/obp-search.css.
 */
(function () {
  "use strict";

  var ENDPOINT = "https://obp-search.openbankruptcyproject.workers.dev/search";
  var DEBOUNCE_MS = 200;
  var MIN_CHARS = 2;

  function debounce(fn, ms) {
    var t = null;
    return function () {
      var args = arguments, ctx = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }

  function fmtAmount(s) {
    if (!s) return "";
    var v = parseFloat(s);
    if (isNaN(v)) return s;
    if (v >= 1e6) return "$" + (v / 1e6).toFixed(2) + "M";
    if (v >= 1e3) return "$" + v.toLocaleString(undefined, {maximumFractionDigits: 0});
    return "$" + v.toFixed(0);
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  var BANNER_HTML = (
    '<div class="obp-search-banner" role="note">' +
    '<span class="obp-search-banner-label">Public records.</span> ' +
    'Results sourced from PACER bankruptcy filings and Treasury SBA-loan records. ' +
    'Accurate publication of lawfully-obtained public-record information is protected speech under ' +
    '<a href="https://supreme.justia.com/cases/federal/us/491/524/" target="_blank" rel="noopener"><em>Florida Star v. B.J.F.</em>, 491 U.S. 524 (1989)</a>, and ' +
    '<a href="https://supreme.justia.com/cases/federal/us/420/469/" target="_blank" rel="noopener"><em>Cox Broadcasting v. Cohn</em>, 420 U.S. 469 (1975)</a>.' +
    '</div>'
  );

  // Two-letter state code to "D. <state>" district label, used in scope copy.
  var STATE_LABELS = {
    AL:"Alabama", AK:"Alaska", AZ:"Arizona", AR:"Arkansas", CA:"California",
    CO:"Colorado", CT:"Connecticut", DE:"Delaware", DC:"D.C.", FL:"Florida",
    GA:"Georgia", HI:"Hawaii", ID:"Idaho", IL:"Illinois", IN:"Indiana",
    IA:"Iowa", KS:"Kansas", KY:"Kentucky", LA:"Louisiana", ME:"Maine",
    MD:"Maryland", MA:"Massachusetts", MI:"Michigan", MN:"Minnesota",
    MS:"Mississippi", MO:"Missouri", MT:"Montana", NE:"Nebraska", NV:"Nevada",
    NH:"New Hampshire", NJ:"New Jersey", NM:"New Mexico", NY:"New York",
    NC:"North Carolina", ND:"North Dakota", OH:"Ohio", OK:"Oklahoma",
    OR:"Oregon", PA:"Pennsylvania", RI:"Rhode Island", SC:"South Carolina",
    SD:"South Dakota", TN:"Tennessee", TX:"Texas", UT:"Utah", VT:"Vermont",
    VA:"Virginia", WA:"Washington", WV:"West Virginia", WI:"Wisconsin", WY:"Wyoming"
  };

  function scopeLabel(program, state) {
    var parts = [];
    if (state && STATE_LABELS[state]) parts.push(STATE_LABELS[state]);
    if (program === "cases") parts.push("bankruptcy cases");
    else if (program === "ppp") parts.push("PPP recipients");
    else if (program === "eidl") parts.push("EIDL recipients");
    return parts.join(" ");
  }

  // Detects when a query looks like the user is reaching for a case number.
  // Catches the partial-typing variants the worker's exact-match short-circuit
  // misses: "26-0315" (still typing), "6-03153" (dropped a digit), "(26-03153"
  // (paste with leading paren). Used only for empty-state hinting.
  function looksLikeCaseNumber(q) {
    if (!q) return false;
    var s = q.trim();
    if (/^\(?\d{1,4}-\d{0,6}\)?$/.test(s)) return true;
    if (/\b\d{2}-\d{1,6}\b/.test(s)) return true;
    return false;
  }

  // Client-side GA4 event for 0-hit interactions. Server-side worker already
  // logs every search, but this gives us a discrete channel to dashboard
  // widen-link impressions vs clicks vs case-hint usage — the existing UI
  // surfaces these on every stuck-filter case, but we don't know if users
  // actually see them or just keep typing past them.
  function fireGtag(name, params) {
    try {
      if (typeof window.gtag === "function") {
        window.gtag("event", name, params || {});
      }
    } catch (_) {}
  }

  function renderResults(results, container, ctx) {
    ctx = ctx || {};
    if (!results || results.length === 0) {
      // When the scope filter is active, surface widening actions — the
      // 5/17 Etna 60-query drill was a single user stuck on a state-locked
      // case-index page who never realized the filter was on.
      var scope = scopeLabel(ctx.program, ctx.state);
      var widenLinks = "";
      if (ctx.state) {
        widenLinks += ' <a href="#" class="obp-search-widen" data-widen="state">Try all states</a>';
      }
      if (ctx.program && ctx.program !== "all") {
        widenLinks += (widenLinks ? ' &middot; ' : ' ') + '<a href="#" class="obp-search-widen" data-widen="program">Try all programs</a>';
      }
      // Outside-scope hint: when the worker reports matches exist outside the
      // active scope, prepend a strong line so the user knows widening will
      // surface something (5/19 Bellevue cluster was searching "feist joseph"
      // in IL when the only Feist in our data was in Iowa).
      var hint = "";
      var outside = (ctx.outside_scope_hits | 0);
      if (outside > 0 && ctx.state) {
        var plural = outside === 1
          ? "1 match exists"
          : (outside >= 50 ? "50+ matches exist" : outside + " matches exist");
        hint = '<div class="obp-search-outside-hint"><strong>' + plural + ' outside this scope.</strong> Click "Try all states" to see them.</div>';
      }
      // Case-number affordance: when the input contains a case-number-shaped
      // fragment, prompt the user to complete it. The 5/19 Milwaukee cluster
      // typed "26-03153" + "26-0315" + "(26-03153" interleaved with name
      // tokens — the worker matched "26-03153" exactly but partial variants
      // fell through to FTS and got 0. Showing the format prompts the user
      // to keep typing the full case number rather than thrashing on partials.
      var caseHint = "";
      var qstr = (ctx.query || "").trim();
      if (qstr && looksLikeCaseNumber(qstr)) {
        caseHint = '<div class="obp-search-casehint">Looking for a case? Try the full case number in <code>NN-NNNNN</code> format (e.g. <code>24-12345</code>).</div>';
      }
      var emptyMsg = scope
        ? 'No matches in ' + escapeHtml(scope) + '.' + widenLinks
        : 'No matches.';
      container.innerHTML = BANNER_HTML + hint + caseHint + '<div class="obp-search-empty">' + emptyMsg + '</div>';
      // Instrumentation: log what the user was offered on this 0-hit. Lets us
      // measure widen-link impressions vs clicks separately from server logs.
      fireGtag("obp_search_empty", {
        program: ctx.program || "all",
        state: ctx.state || "",
        outside_scope_hits: outside,
        widen_state_shown: ctx.state ? 1 : 0,
        widen_program_shown: (ctx.program && ctx.program !== "all") ? 1 : 0,
        case_hint_shown: caseHint ? 1 : 0,
        q_len: qstr.length
      });
      return;
    }
    var html = BANNER_HTML + results.map(function (r) {
      var program = (r.program || "").toUpperCase();
      var name = escapeHtml(r.name || "");
      var url = escapeHtml(r.url || "#");
      var meta;
      if (r.program === "cases") {
        var ch = escapeHtml(r.chapter || "");
        var df = escapeHtml(r.date_filed || "");
        var district = escapeHtml(r.district || "");
        var cn = escapeHtml(r.case_number || "");
        meta = cn + ' &middot; Ch. ' + ch + ' &middot; ' + df + ' &middot; ' + district;
      } else {
        var amount = fmtAmount(r.amount);
        var date = escapeHtml(r.approval_date || "");
        var state = escapeHtml(r.state || "");
        var city = escapeHtml(r.city || "");
        var lender = r.lender ? '<span class="obp-search-lender"> &middot; ' + escapeHtml(r.lender) + '</span>' : "";
        meta = city + (city ? ', ' : '') + state + ' &middot; ' + amount + ' &middot; ' + date + lender;
      }
      return (
        '<a class="obp-search-row" href="' + url + '">' +
        '<span class="obp-search-pgm obp-pgm-' + program.toLowerCase() + '">' + program + '</span>' +
        '<span class="obp-search-name">' + name + '</span>' +
        '<span class="obp-search-meta">' + meta + '</span>' +
        '</a>'
      );
    }).join("");
    container.innerHTML = html;
  }

  function attach(el) {
    var program = el.getAttribute("data-program") || "all";
    var state = el.getAttribute("data-state") || "";
    var placeholder = el.getAttribute("data-placeholder");
    if (!placeholder) {
      if (program === "cases") {
        placeholder = "Search bankruptcy cases by debtor name...";
      } else if (program === "ppp" || program === "eidl") {
        placeholder = "Search " + program.toUpperCase() + " recipients by borrower name...";
      } else {
        placeholder = "Search bankruptcy court records, PPP, or EIDL recipients...";
      }
    }

    // Cases-only filter chips. Opt-in via data-filters="1" (default) or off via "0".
    var enableFilters = (program === "cases") && (el.getAttribute("data-filters") !== "0");
    var filtersHtml = "";
    if (enableFilters) {
      var years = [];
      var thisYear = new Date().getFullYear();
      for (var y = thisYear; y >= thisYear - 15; y--) years.push(String(y));
      filtersHtml = (
        '<div class="obp-search-filters">' +
          '<label class="obp-search-filter">Chapter ' +
            '<select class="obp-search-chapter">' +
              '<option value="">Any</option>' +
              '<option value="7">7</option>' +
              '<option value="11">11</option>' +
              '<option value="12">12</option>' +
              '<option value="13">13</option>' +
            '</select>' +
          '</label>' +
          '<label class="obp-search-filter">Year ' +
            '<select class="obp-search-year">' +
              '<option value="">Any</option>' +
              years.map(function (yy) { return '<option value="' + yy + '">' + yy + '</option>'; }).join("") +
            '</select>' +
          '</label>' +
        '</div>'
      );
    }

    // Track scope locally so the user can clear it from the chip without
    // mutating the data-attribute (which would re-apply on next page load).
    var activeProgram = program;
    var activeState = state;

    function scopeChipHtml() {
      var lbl = scopeLabel(activeProgram, activeState);
      if (!lbl) return '';
      return (
        '<div class="obp-search-scope" role="note">' +
        '<span class="obp-search-scope-label">Searching in:</span> ' +
        '<span class="obp-search-scope-value">' + escapeHtml(lbl) + '</span> ' +
        '<button type="button" class="obp-search-scope-clear" aria-label="Clear scope filter" title="Search across all states + programs">&times;</button>' +
        '</div>'
      );
    }

    var html = (
      '<div class="obp-search-wrap">' +
      '<div class="obp-search-scope-mount">' + scopeChipHtml() + '</div>' +
      '<input type="search" class="obp-search-input" placeholder="' + escapeHtml(placeholder) + '" autocomplete="off" spellcheck="false" maxlength="200">' +
      filtersHtml +
      '<div class="obp-search-results" hidden></div>' +
      '<div class="obp-search-hint">Press enter to land on the borrower\'s row on its state page.</div>' +
      '</div>'
    );
    el.innerHTML = html;

    var input = el.querySelector(".obp-search-input");
    var results = el.querySelector(".obp-search-results");
    var chapterSel = el.querySelector(".obp-search-chapter");
    var yearSel = el.querySelector(".obp-search-year");
    var scopeMount = el.querySelector(".obp-search-scope-mount");

    function rerenderScope() {
      scopeMount.innerHTML = scopeChipHtml();
    }

    var ACK_KEY = "obp-search-ack-v1";
    function isAcknowledged() {
      try { return localStorage.getItem(ACK_KEY) === "1"; }
      catch (_) { return false; }
    }
    function setAcknowledged() {
      try { localStorage.setItem(ACK_KEY, "1"); } catch (_) {}
    }

    function showAckGate(onContinue) {
      results.innerHTML = (
        '<div class="obp-search-ack">' +
        '<p class="obp-search-ack-title">Public records search</p>' +
        '<p class="obp-search-ack-body">This search queries a free public-record index sourced from PACER bankruptcy filings and Treasury SBA-loan records. Accurate publication of lawfully-obtained public-record information is protected speech under <a href="https://supreme.justia.com/cases/federal/us/491/524/" target="_blank" rel="noopener"><em>Florida Star v. B.J.F.</em>, 491 U.S. 524 (1989)</a>, and <a href="https://supreme.justia.com/cases/federal/us/420/469/" target="_blank" rel="noopener"><em>Cox Broadcasting v. Cohn</em>, 420 U.S. 469 (1975)</a>.</p>' +
        '<button type="button" class="obp-search-ack-btn">Continue to search</button>' +
        '</div>'
      );
      results.hidden = false;
      var btn = results.querySelector(".obp-search-ack-btn");
      btn.addEventListener("click", function () {
        setAcknowledged();
        onContinue();
      });
    }

    function runFetch(q) {
      var params = new URLSearchParams({ q: q, program: activeProgram, limit: "12" });
      if (activeState) params.set("state", activeState);
      if (chapterSel && chapterSel.value) params.set("chapter", chapterSel.value);
      if (yearSel && yearSel.value) params.set("year", yearSel.value);

      fetch(ENDPOINT + "?" + params.toString(), { method: "GET" })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          renderResults(data.results || [], results, {
            program: activeProgram,
            state: activeState,
            outside_scope_hits: data.outside_scope_hits || 0,
            query: q
          });
          results.hidden = false;
        })
        .catch(function (err) {
          results.innerHTML = '<div class="obp-search-empty">Search unavailable.</div>';
          results.hidden = false;
        });
    }

    // Scope-chip clear: drop state + program filters in-place and re-search.
    el.addEventListener("click", function (e) {
      if (e.target.classList && e.target.classList.contains("obp-search-scope-clear")) {
        e.preventDefault();
        activeState = "";
        activeProgram = "all";
        rerenderScope();
        var q = input.value.trim();
        if (q.length >= MIN_CHARS) runFetch(q);
      }
    });

    // 0-result widen links: drop the named filter and re-fetch.
    results.addEventListener("click", function (e) {
      var t = e.target;
      if (t.classList && t.classList.contains("obp-search-widen")) {
        e.preventDefault();
        var which = t.getAttribute("data-widen");
        // Instrumentation: capture click before mutating state so we can
        // dashboard widen-link impressions (obp_search_empty) vs clicks
        // (obp_search_widen_click) and compute the conversion rate.
        fireGtag("obp_search_widen_click", {
          widen: which,
          from_state: activeState || "",
          from_program: activeProgram || "all"
        });
        if (which === "state") activeState = "";
        else if (which === "program") activeProgram = "all";
        rerenderScope();
        var q = input.value.trim();
        if (q.length >= MIN_CHARS) runFetch(q);
      }
    });

    var doSearch = debounce(function () {
      var q = input.value.trim();
      if (q.length < MIN_CHARS) {
        results.hidden = true;
        results.innerHTML = "";
        return;
      }
      if (!isAcknowledged()) {
        showAckGate(function () { runFetch(q); });
        return;
      }
      runFetch(q);
    }, DEBOUNCE_MS);

    input.addEventListener("input", doSearch);
    input.addEventListener("focus", function () {
      if (results.innerHTML) results.hidden = false;
    });
    if (chapterSel) chapterSel.addEventListener("change", doSearch);
    if (yearSel) yearSel.addEventListener("change", doSearch);

    // Submit on Enter — navigates to the first result if present.
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        var first = results.querySelector("a.obp-search-row");
        if (first) {
          e.preventDefault();
          window.location.href = first.getAttribute("href");
        }
      }
    });

    // Close results when clicking outside the widget.
    document.addEventListener("click", function (e) {
      if (!el.contains(e.target)) {
        results.hidden = true;
      }
    });
  }

  function init() {
    var els = document.querySelectorAll(".obp-search");
    Array.prototype.forEach.call(els, attach);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
