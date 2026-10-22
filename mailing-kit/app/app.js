/* OBP Notice & Mailing Kit, workspace script.
   Everything runs in this browser tab. No document, name, or address is sent anywhere.
   Libraries: pdf-lib 1.17.1 (MIT) and PapaParse 5.4.1 (MIT), vendored in ../vendor/ (hashes in VENDOR_HASHES.txt).
   Analytics on this page: one privacy-safe event, mailing_kit_download_complete, with no names, counts, filenames, or case data. */
(function () {
  'use strict';

  /* ---------- analytics bootstrap (no inline scripts on this page; CSP in the HTML) ---------- */
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('set', 'allow_google_signals', false);
  gtag('set', 'allow_ad_personalization_signals', false);
  gtag('config', 'G-FTWLM223G7', { send_page_view: true, allow_google_signals: false, allow_ad_personalization_signals: false });
  var conversionFired = false;
  function fireDownloadComplete(components) {
    if (conversionFired) return;
    conversionFired = true;
    try { gtag('event', 'mailing_kit_download_complete', { site: location.hostname, components: components, transport_type: 'beacon' }); } catch (e) {}
  }

  /* ---------- constants ---------- */
  var PT = 72;
  var LETTER = { w: 612, h: 792 };
  var LABEL = { cols: 3, rows: 10, w: 2.625 * PT, h: 1 * PT, left: 0.1875 * PT, top: 0.5 * PT, pitchX: 2.75 * PT, pitchY: 1 * PT, inset: 0.125 * PT };
  var ENV10 = { w: 9.5 * PT, h: 4.125 * PT };
  var LIMITS = { maxRecipients: 500, maxPdfBytes: 25 * 1024 * 1024, maxPdfPages: 60, warnPages: 800 };
  var MAX_LINES = 6;

  var state = {
    districts: null,
    district: null,
    recipients: [],
    nextId: 1,
    pdf: null,          // { bytes, name, pages, confirmed }
    outputs: [],        // { label, url, blob, kind }
    generatedAt: null,
    log: {}             // id -> { date, method, docs }
  };

  var $ = function (id) { return document.getElementById(id); };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function announce(msg, isError) {
    var el = $('status');
    el.textContent = msg;
    el.className = 'status' + (isError ? ' error' : '');
  }
  function todayISO() { var d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }

  /* ---------- 1. district catalogue ---------- */
  function loadDistricts() {
    var sel = $('district');
    fetch('../data/districts.json', { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (cat) {
      state.districts = cat;
      var frag = document.createDocumentFragment();
      cat.districts.slice().sort(function (a, b) { return a.name.localeCompare(b.name); }).forEach(function (d) {
        var o = document.createElement('option');
        o.value = d.slug;
        o.textContent = d.name.replace('United States Bankruptcy Court for the ', '') + (d.status === 'confirmed' ? ' (court notice on file)' : '');
        frag.appendChild(o);
      });
      sel.appendChild(frag);
      renderNational(cat.national);
    }).catch(function (e) {
      $('district-panel').innerHTML = '<p class="warn">The district catalogue did not load (' + esc(e.message) + '). Use the official court website list at <a href="https://www.uscourts.gov/about-federal-courts/federal-courts-public/court-website-links" rel="noopener" target="_blank">uscourts.gov</a> and check your court\'s current instructions before mailing anything.</p>';
    });
  }
  function renderNational(n) {
    if (!n || !n.advisory_active) { $('national').hidden = true; return; }
    $('national').innerHTML = '<strong>BNC disruption, status as of ' + esc(n.last_verified) + ':</strong> ' + esc(n.summary) + ' Source: <a href="' + esc(n.url) + '" rel="noopener" target="_blank">' + esc(n.source) + ', ' + esc(n.date) + '</a>. This line is updated by hand; it is not a live feed. Check your district\'s official guidance.';
  }
  function onDistrictChange() {
    var slug = $('district').value;
    var panel = $('district-panel');
    state.district = null;
    if (!slug) { panel.innerHTML = ''; return; }
    if (slug === 'unsure') {
      panel.innerHTML = '<p>Bankruptcy courts are organized by federal judicial district. Find yours from the official list: <a href="https://www.uscourts.gov/about-federal-courts/federal-courts-public/court-website-links" rel="noopener" target="_blank">Court website links (uscourts.gov)</a>. The notice you received, if you have one, names the court at the top.</p>';
      return;
    }
    var d = state.districts.districts.filter(function (x) { return x.slug === slug; })[0];
    if (!d) return;
    state.district = d;
    var html = '<p><strong>' + esc(d.name) + '</strong><br>Official court website: <a href="' + esc(d.official_url) + '" rel="noopener" target="_blank">' + esc(d.official_url.replace('https://', '')) + '</a></p>';
    if (d.status === 'confirmed' && d.guidance) {
      html += '<div class="advisory"><strong>Court notice on file (read ' + esc(d.guidance.last_verified) + '):</strong> ' + esc(d.guidance.summary) + ' <a href="' + esc(d.guidance.guidance_url) + '" rel="noopener" target="_blank">Read the court\'s page</a> (dated ' + esc(d.guidance.guidance_date) + '). The court\'s page controls if it has changed since.</div>';
    } else {
      html += '<p class="muted">We have not reviewed this court\'s BNC-disruption guidance. Open the official website above and verify current local instructions before mailing. This tool does not decide whom you must serve.</p>';
    }
    panel.innerHTML = html;
  }

  /* ---------- 2. output modes ---------- */
  function modes() {
    return { labels: $('m-labels').checked, envelopes: $('m-envelopes').checked, packets: $('m-packets').checked, checklist: $('m-checklist').checked, log: $('m-log').checked };
  }

  /* ---------- 3. recipients ---------- */
  function normLine(s) { return String(s || '').replace(/\s+/g, ' ').trim(); }
  function addRecipient(lines, source) {
    lines = lines.map(normLine).filter(function (l) { return l.length; });
    if (!lines.length) return null;
    var r = { id: state.nextId++, name: lines[0], lines: lines.slice(1), source: source || 'manual' };
    state.recipients.push(r);
    return r;
  }
  function parsePaste(text) {
    var blocks = String(text || '').replace(/\r\n?/g, '\n').split(/\n\s*\n+/);
    var n = 0;
    blocks.forEach(function (b) { if (addRecipient(b.split('\n'), 'paste')) n++; });
    return n;
  }
  function parseCSVText(text) {
    var res = Papa.parse(String(text || ''), { skipEmptyLines: 'greedy' });
    if (!res.data || !res.data.length) return 0;
    var rows = res.data;
    var header = rows[0].map(function (h) { return normLine(h).toLowerCase(); });
    var known = { name: ['name', 'creditor', 'recipient', 'party'], a1: ['address1', 'address 1', 'address', 'line1', 'line 1', 'street'], a2: ['address2', 'address 2', 'line2', 'line 2', 'suite', 'attn', 'attention'], a3: ['address3', 'address 3', 'line3', 'line 3'], city: ['city'], st: ['state', 'st'], zip: ['zip', 'zipcode', 'zip code', 'postal', 'postal code'] };
    function col(keys) { for (var i = 0; i < header.length; i++) if (keys.indexOf(header[i]) >= 0) return i; return -1; }
    var c = { name: col(known.name), a1: col(known.a1), a2: col(known.a2), a3: col(known.a3), city: col(known.city), st: col(known.st), zip: col(known.zip) };
    var hasHeader = c.name >= 0 || c.a1 >= 0 || c.zip >= 0;
    var n = 0;
    rows.slice(hasHeader ? 1 : 0).forEach(function (row) {
      var lines;
      if (hasHeader) {
        var last = [c.city >= 0 ? row[c.city] : '', c.st >= 0 ? row[c.st] : '', c.zip >= 0 ? row[c.zip] : ''].map(normLine);
        var cityLine = last[0] ? last[0] + (last[1] || last[2] ? ', ' : '') : '';
        cityLine += [last[1], last[2]].filter(Boolean).join(' ');
        lines = [c.name >= 0 ? row[c.name] : '', c.a1 >= 0 ? row[c.a1] : '', c.a2 >= 0 ? row[c.a2] : '', c.a3 >= 0 ? row[c.a3] : '', cityLine];
      } else {
        lines = row.slice();
      }
      if (addRecipient(lines, 'csv')) n++;
    });
    return n;
  }
  function zipOf(r) {
    var all = [r.name].concat(r.lines).join(' ');
    var m = all.match(/\b(\d{5})(?:-(\d{4}))?\b(?!.*\b\d{5}\b)/);
    return m ? m[0] : '';
  }
  function flagsFor(r, all) {
    var f = [];
    if (!r.lines.length) f.push('no address lines');
    var lastLine = r.lines[r.lines.length - 1] || '';
    if (r.lines.length && !/\b\d{5}(-\d{4})?\b/.test(lastLine)) f.push('last line has no 5- or 9-digit ZIP');
    if (r.lines.length + 1 > MAX_LINES) f.push('more than ' + MAX_LINES + ' lines; label will truncate');
    [r.name].concat(r.lines).forEach(function (l) { if (l.length > 45) f.push('long line (' + l.length + ' chars)'); });
    var key = (r.name.toLowerCase().replace(/[^a-z0-9]/g, '') + '|' + zipOf(r));
    var dup = all.filter(function (o) { return o.id !== r.id && (o.name.toLowerCase().replace(/[^a-z0-9]/g, '') + '|' + zipOf(o)) === key; });
    if (dup.length) f.push('possible duplicate of #' + dup.map(function (o) { return o.id; }).join(', #'));
    if (r.encodingIssue) f.push('characters not supported by the PDF font were replaced with ?');
    return f;
  }
  function renderRecipients() {
    var tb = $('recipients-body');
    var rs = state.recipients;
    $('recipient-count').textContent = rs.length;
    if (!rs.length) { tb.innerHTML = '<tr><td colspan="4" class="muted">No recipients yet.</td></tr>'; return; }
    tb.innerHTML = rs.map(function (r) {
      var f = flagsFor(r, rs);
      return '<tr data-id="' + r.id + '"><td>#' + r.id + '</td><td><textarea class="edit" aria-label="Recipient ' + r.id + ' name and address" rows="' + (r.lines.length + 1) + '">' + esc([r.name].concat(r.lines).join('\n')) + '</textarea></td><td class="flags">' + (f.length ? f.map(esc).join('<br>') : '<span class="ok">ok</span>') + '</td><td><button type="button" class="sm del" data-id="' + r.id + '">Remove</button></td></tr>';
    }).join('');
  }
  function onRecipientEdit(e) {
    var ta = e.target;
    if (!ta.classList.contains('edit')) return;
    var id = +ta.closest('tr').getAttribute('data-id');
    var r = state.recipients.filter(function (x) { return x.id === id; })[0];
    if (!r) return;
    var lines = ta.value.replace(/\r\n?/g, '\n').split('\n').map(normLine).filter(Boolean);
    r.name = lines[0] || '';
    r.lines = lines.slice(1);
    r.encodingIssue = false;
  }
  function onRecipientClick(e) {
    var b = e.target.closest('button.del');
    if (!b) return;
    var id = +b.getAttribute('data-id');
    state.recipients = state.recipients.filter(function (x) { return x.id !== id; });
    delete state.log[id];
    renderRecipients();
    announce('Recipient #' + id + ' removed.');
  }

  /* ---------- 4. original PDF ---------- */
  function onPdfFile(e) {
    var f = e.target.files && e.target.files[0];
    state.pdf = null;
    $('pdf-confirm').checked = false;
    $('pdf-info').textContent = '';
    if (!f) return;
    if (f.size > LIMITS.maxPdfBytes) { announce('That PDF is larger than ' + Math.round(LIMITS.maxPdfBytes / 1048576) + ' MB. Split it or choose a smaller file.', true); e.target.value = ''; return; }
    f.arrayBuffer().then(function (buf) {
      return PDFLib.PDFDocument.load(buf, { ignoreEncryption: false, updateMetadata: false }).then(function (doc) {
        var n = doc.getPageCount();
        if (n > LIMITS.maxPdfPages) { throw new Error('This file has ' + n + ' pages; the limit is ' + LIMITS.maxPdfPages + '.'); }
        state.pdf = { bytes: buf, name: f.name, pages: n, confirmed: false };
        $('pdf-info').textContent = f.name + ': ' + n + ' page' + (n === 1 ? '' : 's') + ', ' + (f.size / 1024).toFixed(0) + ' KB. Pages are copied as they are; nothing in them is edited.';
        announce('PDF read. Confirm it is the document you intend to mail.');
      });
    }).catch(function (err) {
      var msg = String(err && err.message || err);
      if (/encrypt/i.test(msg)) msg = 'This PDF is password-protected or encrypted. This tool does not open encrypted files; print it from its own viewer instead.';
      else if (!/limit is/.test(msg)) msg = 'That file could not be read as a PDF (' + msg + ').';
      announce(msg, true);
      e.target.value = '';
    });
  }

  /* ---------- 5. generation ---------- */
  function returnLines() { return $('return-address').value.replace(/\r\n?/g, '\n').split('\n').map(normLine).filter(Boolean).slice(0, 5); }
  function offsets() { return { x: (parseFloat($('off-x').value) || 0) * PT, y: (parseFloat($('off-y').value) || 0) * PT }; }

  function makeSafe(font) {
    return function (s, r) {
      s = String(s || '');
      try { font.widthOfTextAtSize(s, 10); return s; } catch (e) {}
      var out = '';
      for (var i = 0; i < s.length; i++) {
        var ch = s[i];
        try { font.widthOfTextAtSize(ch, 10); out += ch; } catch (e2) { out += '?'; if (r) r.encodingIssue = true; }
      }
      return out;
    };
  }
  function fitSize(font, lines, maxWidth, start, min) {
    var size = start;
    while (size > min) {
      var tooWide = lines.some(function (l) { return font.widthOfTextAtSize(l, size) > maxWidth; });
      if (!tooWide) break;
      size -= 0.5;
    }
    return size;
  }

  function buildLabels(testSheet) {
    var P = PDFLib;
    return P.PDFDocument.create().then(function (doc) {
      return doc.embedFont(P.StandardFonts.Helvetica).then(function (font) {
        var safe = makeSafe(font);
        var off = offsets();
        var rs = testSheet ? [] : state.recipients;
        var perSheet = LABEL.cols * LABEL.rows;
        var sheets = testSheet ? 1 : Math.max(1, Math.ceil(rs.length / perSheet));
        for (var s = 0; s < sheets; s++) {
          var page = doc.addPage([LETTER.w, LETTER.h]);
          for (var i = 0; i < perSheet; i++) {
            var idx = s * perSheet + i;
            var col = i % LABEL.cols, row = Math.floor(i / LABEL.cols);
            var x = LABEL.left + col * LABEL.pitchX + off.x;
            var yTop = LETTER.h - LABEL.top - row * LABEL.pitchY - off.y;
            if (testSheet) {
              page.drawRectangle({ x: x, y: yTop - LABEL.h, width: LABEL.w, height: LABEL.h, borderColor: P.rgb(0.6, 0.6, 0.6), borderWidth: 0.5 });
              page.drawText('Label ' + (i + 1), { x: x + LABEL.inset, y: yTop - 16, size: 8, font: font, color: P.rgb(0.5, 0.5, 0.5) });
              continue;
            }
            if (idx >= rs.length) break;
            var r = rs[idx];
            var lines = [r.name].concat(r.lines).slice(0, MAX_LINES).map(function (l) { return safe(l, r); });
            var size = fitSize(font, lines, LABEL.w - 2 * LABEL.inset, 10, 7);
            var lh = size * 1.18;
            var blockH = lines.length * lh;
            var y = yTop - LABEL.inset - size - Math.max(0, (LABEL.h - 2 * LABEL.inset - blockH) / 2);
            lines.forEach(function (l) { page.drawText(l, { x: x + LABEL.inset, y: y, size: size, font: font }); y -= lh; });
          }
          if (testSheet) {
            page.drawText('Avery 5160 / 8160 alignment test. Print at 100% (Actual size), no scaling. Hold against a label sheet. Adjust the X / Y offsets if the boxes sit off the labels.', { x: 36, y: 14, size: 7, font: font, color: P.rgb(0.4, 0.4, 0.4) });
          }
        }
        return doc.save({ updateFieldAppearances: false });
      });
    });
  }

  function buildEnvelopes() {
    var P = PDFLib;
    return P.PDFDocument.create().then(function (doc) {
      return doc.embedFont(P.StandardFonts.Helvetica).then(function (font) {
        var safe = makeSafe(font);
        var ret = returnLines().map(function (l) { return safe(l); });
        var rotate = $('env-rotate').checked;
        state.recipients.forEach(function (r) {
          var page = doc.addPage([ENV10.w, ENV10.h]);
          var y = ENV10.h - 36;
          ret.forEach(function (l) { page.drawText(l, { x: 28, y: y, size: 10, font: font }); y -= 12.5; });
          var lines = [r.name].concat(r.lines).slice(0, MAX_LINES).map(function (l) { return safe(l, r); });
          var size = fitSize(font, lines, ENV10.w - 250 - 36, 12, 9);
          var yy = 150 + (lines.length - 1) * size * 1.25 / 2;
          lines.forEach(function (l) { page.drawText(l, { x: 250, y: yy, size: size, font: font }); yy -= size * 1.25; });
          if (rotate) page.setRotation(P.degrees(90));
        });
        return doc.save({ updateFieldAppearances: false });
      });
    });
  }

  function buildPackets(progress) {
    var P = PDFLib;
    var rs = state.recipients;
    var sep = $('separator').checked;
    var batchPages = Math.max(50, parseInt($('batch-pages').value, 10) || 200);
    var pagesPer = state.pdf.pages + (sep ? 1 : 0);
    var parts = [];
    return P.PDFDocument.load(state.pdf.bytes, { ignoreEncryption: false, updateMetadata: false }).then(function (src) {
      var srcIdx = src.getPageIndices();
      var i = 0;
      function nextPart() {
        if (i >= rs.length) return Promise.resolve(parts);
        var startI = i;
        return P.PDFDocument.create().then(function (doc) {
          return doc.embedFont(P.StandardFonts.Helvetica).then(function (font) {
            var safe = makeSafe(font);
            var pagesIn = 0;
            function addOne() {
              if (i >= rs.length || (pagesIn > 0 && pagesIn + pagesPer > batchPages)) return Promise.resolve();
              var r = rs[i];
              if (sep) {
                var pg = doc.addPage([LETTER.w, LETTER.h]);
                pg.drawText('COPY FOR MAILING', { x: 54, y: LETTER.h - 90, size: 18, font: font });
                var y = LETTER.h - 130;
                [r.name].concat(r.lines).map(function (l) { return safe(l, r); }).forEach(function (l) { pg.drawText(l, { x: 54, y: y, size: 12, font: font }); y -= 16; });
                pg.drawText('Copy ' + (i + 1) + ' of ' + rs.length + '. Document: ' + safe(state.pdf.name) + ' (' + state.pdf.pages + ' page' + (state.pdf.pages === 1 ? '' : 's') + ').', { x: 54, y: y - 16, size: 10, font: font, color: P.rgb(0.35, 0.35, 0.35) });
                pg.drawText('Separator sheet generated for sorting. Remove before mailing if your court or the recipient should not receive it.', { x: 54, y: y - 32, size: 9, font: font, color: P.rgb(0.35, 0.35, 0.35) });
                pagesIn++;
              }
              return doc.copyPages(src, srcIdx).then(function (pages) {
                pages.forEach(function (p) { doc.addPage(p); });
                pagesIn += pages.length;
                i++;
                if (progress) progress(i, rs.length);
                return new Promise(function (res) { setTimeout(res, 0); }).then(addOne);
              });
            }
            return addOne().then(function () { return doc.save({ updateFieldAppearances: false }); }).then(function (bytes) {
              parts.push({ bytes: bytes, from: startI + 1, to: i, pages: pagesIn });
              return nextPart();
            });
          });
        });
      }
      return nextPart();
    });
  }

  function tableDoc(title, subtitle, header, rows, footerNote) {
    var P = PDFLib;
    return P.PDFDocument.create().then(function (doc) {
      return Promise.all([doc.embedFont(P.StandardFonts.Helvetica), doc.embedFont(P.StandardFonts.HelveticaBold)]).then(function (fonts) {
        var font = fonts[0], bold = fonts[1], safe = makeSafe(font);
        var colX = [40, 70, 300, 400, 480];
        var maxW = LETTER.w - 80;
        function wrap(text, size) {
          var words = safe(text).split(' '), lines = [], cur = '';
          words.forEach(function (w) {
            var t = cur ? cur + ' ' + w : w;
            if (font.widthOfTextAtSize(t, size) <= maxW) cur = t; else { if (cur) lines.push(cur); cur = w; }
          });
          if (cur) lines.push(cur);
          return lines;
        }
        var page, y;
        function newPage() {
          page = doc.addPage([LETTER.w, LETTER.h]);
          y = LETTER.h - 54;
          page.drawText(safe(title), { x: 40, y: y, size: 14, font: bold }); y -= 16;
          subtitle.forEach(function (s) { wrap(s, 9).forEach(function (l) { page.drawText(l, { x: 40, y: y, size: 9, font: font, color: P.rgb(0.3, 0.3, 0.3) }); y -= 12; }); });
          y -= 6;
          header.forEach(function (h, k) { page.drawText(h, { x: colX[k], y: y, size: 9, font: bold }); });
          y -= 6;
          page.drawLine({ start: { x: 40, y: y }, end: { x: LETTER.w - 40, y: y }, thickness: 0.5 });
          y -= 12;
        }
        newPage();
        rows.forEach(function (row) {
          var lines = row[1];
          var need = Math.max(lines.length, 1) * 10.5 + 8;
          if (y - need < 50) newPage();
          page.drawRectangle({ x: colX[0], y: y - 2, width: 9, height: 9, borderWidth: 0.6, borderColor: P.rgb(0, 0, 0) });
          page.drawText(String(row[0]), { x: colX[0] + 13, y: y, size: 8, font: font });
          var yy = y;
          lines.forEach(function (l) { page.drawText(safe(l), { x: colX[1] + 18, y: yy, size: 8.5, font: font }); yy -= 10.5; });
          for (var k = 2; k < header.length; k++) {
            var v = row[k] || '';
            if (v) page.drawText(safe(v), { x: colX[k], y: y, size: 8.5, font: font });
            else page.drawLine({ start: { x: colX[k], y: y - 2 }, end: { x: colX[k] + (k === header.length - 1 ? 90 : 70), y: y - 2 }, thickness: 0.4, color: P.rgb(0.6, 0.6, 0.6) });
          }
          y -= need;
        });
        y -= 10;
        footerNote.forEach(function (s) { wrap(s, 8).forEach(function (l) { if (y < 60) newPage(); page.drawText(l, { x: 40, y: y, size: 8, font: font, color: P.rgb(0.3, 0.3, 0.3) }); y -= 11; }); });
        return doc.save({ updateFieldAppearances: false });
      });
    });
  }

  function buildChecklist() {
    var rs = state.recipients, m = modes();
    var pages = state.pdf ? state.pdf.pages : 0;
    var sub = [
      'Prepared ' + todayISO() + ' with the OBP Notice & Mailing Kit. This is a worksheet for your own use. It is not a certificate of service and it does not say whom you must serve.',
      'Recipients listed: ' + rs.length + '. ' + (state.pdf ? 'Document: ' + state.pdf.name + ', ' + pages + ' page' + (pages === 1 ? '' : 's') + ' per copy; ' + (rs.length * pages) + ' pages in all' + ($('separator').checked ? ' plus ' + rs.length + ' separator sheets' : '') + '.' : 'No document attached; labels/checklist only.'),
      'Quantities: ' + (m.envelopes ? rs.length + ' envelopes; ' : '') + (m.labels ? Math.ceil(rs.length / 30) + ' label sheet' + (Math.ceil(rs.length / 30) === 1 ? '' : 's') + ' (30 per sheet); ' : '') + 'postage for ' + rs.length + ' pieces (weight depends on page count; confirm at the counter).',
      (state.district ? 'Court selected: ' + state.district.name + '. ' : '') + 'Check the court\'s current instructions for what must be mailed, to whom, and how to report it.'
    ];
    var rows = rs.map(function (r) { return [r.id, [r.name].concat(r.lines), '', '', '']; });
    return tableDoc('Mailing checklist', sub, ['', 'Recipient', 'Date mailed', 'Method', 'Initials'], rows, ['Tick each box only when that piece has actually been mailed. Fill in the date and method by hand after mailing.']);
  }

  function buildLogPdf() {
    var rs = state.recipients;
    var declarant = normLine($('declarant').value);
    var docs = normLine($('log-docs').value);
    var sub = [
      'Service log worksheet, prepared ' + todayISO() + '. UNSIGNED. Editable record of what was actually mailed, entered by the user after mailing.',
      'This is not a certificate of service, affidavit, or declaration. If your court requires a certificate, use the court\'s form or format and your own signature.',
      'Documents (as entered): ' + (docs || '[not entered]') + '.   Declarant (as entered): ' + (declarant || '[not entered]') + '.'
    ];
    var rows = rs.map(function (r) { var l = state.log[r.id] || {}; return [r.id, [r.name].concat(r.lines), l.date || '', l.method || '', '']; });
    var blank = rs.filter(function (r) { return !(state.log[r.id] && state.log[r.id].date); }).length;
    return tableDoc('Service log worksheet', sub, ['', 'Recipient', 'Date mailed', 'Method', 'Notes'], rows, [blank ? blank + ' recipient' + (blank === 1 ? ' has' : 's have') + ' no mailing date entered. A blank means not recorded, not served.' : 'Every recipient has a date entered by the user.', 'Entries reflect only what the user typed. Nothing is marked mailed by default.']);
  }

  function revokeOutputs() {
    state.outputs.forEach(function (o) { try { URL.revokeObjectURL(o.url); } catch (e) {} });
    state.outputs = [];
    $('outputs').innerHTML = '';
  }
  function addOutput(label, bytes, kind) {
    var blob = new Blob([bytes], { type: 'application/pdf' });
    var url = URL.createObjectURL(blob);
    state.outputs.push({ label: label, url: url, blob: blob, kind: kind });
    var li = document.createElement('li');
    var a = document.createElement('a');
    a.href = url; a.download = label; a.textContent = label; a.className = 'dl'; a.setAttribute('data-kind', kind);
    a.addEventListener('click', function () { if (kind !== 'test') fireDownloadComplete(Object.keys(modes()).filter(function (k) { return modes()[k]; }).join('|')); });
    li.appendChild(a);
    li.appendChild(document.createTextNode(' (' + (blob.size / 1024).toFixed(0) + ' KB)'));
    $('outputs').appendChild(li);
  }

  function summary() {
    var rs = state.recipients, m = modes();
    var pages = state.pdf ? state.pdf.pages : 0;
    var sep = $('separator').checked;
    var parts = [];
    parts.push(rs.length + ' recipient' + (rs.length === 1 ? '' : 's'));
    if (m.packets && state.pdf) parts.push(rs.length + ' copies x ' + pages + ' page' + (pages === 1 ? '' : 's') + ' = ' + (rs.length * pages) + ' sheets' + (sep ? ' + ' + rs.length + ' separators' : ''));
    if (m.labels) parts.push(Math.ceil(rs.length / 30) + ' label sheet' + (Math.ceil(rs.length / 30) === 1 ? '' : 's'));
    if (m.envelopes) parts.push(rs.length + ' envelopes');
    parts.push('postage for ' + rs.length + ' piece' + (rs.length === 1 ? '' : 's'));
    $('summary').textContent = parts.join(' | ');
  }

  function generate() {
    var m = modes(), rs = state.recipients;
    if (!rs.length) { announce('Add at least one recipient first.', true); return; }
    if (rs.length > LIMITS.maxRecipients) { announce('This tool handles up to ' + LIMITS.maxRecipients + ' recipients at a time. Split the list.', true); return; }
    if (m.packets && !state.pdf) { announce('Packet copies need the original PDF. Add it in step 4, or untick "Packet copies".', true); return; }
    if (m.packets && !$('pdf-confirm').checked) { announce('Confirm in step 4 that the PDF is the document you intend to mail.', true); return; }
    if (!m.labels && !m.envelopes && !m.packets && !m.checklist) { announce('Choose at least one output.', true); return; }
    if (m.packets && rs.length * state.pdf.pages > LIMITS.warnPages && !window.confirm('That is ' + (rs.length * state.pdf.pages) + ' pages. It will be split into several files. Continue?')) return;
    revokeOutputs();
    state.recipients.forEach(function (r) { r.encodingIssue = false; });
    var btn = $('generate'); btn.disabled = true;
    announce('Generating. Nothing leaves this tab.');
    var chain = Promise.resolve();
    if (m.labels) chain = chain.then(buildLabels.bind(null, false)).then(function (b) { addOutput('labels-5160.pdf', b, 'labels'); });
    if (m.envelopes) chain = chain.then(buildEnvelopes).then(function (b) { addOutput('envelopes-10.pdf', b, 'envelopes'); });
    if (m.packets) chain = chain.then(function () { return buildPackets(function (i, n) { announce('Copying packets: ' + i + ' of ' + n + '.'); }); }).then(function (parts) {
      parts.forEach(function (p, k) { addOutput(parts.length > 1 ? 'packets-part' + (k + 1) + '-recipients-' + p.from + '-to-' + p.to + '.pdf' : 'packets-all-recipients.pdf', p.bytes, 'packets'); });
    });
    if (m.checklist) chain = chain.then(buildChecklist).then(function (b) { addOutput('mailing-checklist.pdf', b, 'checklist'); });
    chain.then(function () {
      state.generatedAt = new Date();
      renderRecipients();
      summary();
      $('step-log').hidden = !m.log;
      if (m.log) renderLog();
      announce('Done. Download each file below, then print at 100% (Actual size). Recipients are not marked as mailed by anything this tool does.');
    }).catch(function (err) {
      announce('Generation failed: ' + String(err && err.message || err), true);
    }).then(function () { btn.disabled = false; });
  }

  /* ---------- 6. service log ---------- */
  function renderLog() {
    var tb = $('log-body');
    tb.innerHTML = state.recipients.map(function (r) {
      var l = state.log[r.id] || {};
      return '<tr data-id="' + r.id + '"><td>#' + r.id + '</td><td>' + esc(r.name) + '<br><span class="muted">' + esc(r.lines.join(', ')) + '</span></td><td><input type="date" class="log-date" aria-label="Date mailed to recipient ' + r.id + '" value="' + esc(l.date || '') + '"></td><td><select class="log-method" aria-label="Method for recipient ' + r.id + '"><option value=""' + (!l.method ? ' selected' : '') + '>Not recorded</option>' + ['First-class mail', 'Certified mail', 'Certificate of mailing', 'Hand delivery', 'Other'].map(function (o) { return '<option' + (l.method === o ? ' selected' : '') + '>' + o + '</option>'; }).join('') + '</select></td></tr>';
    }).join('');
    if (!$('log-docs').value && state.pdf) $('log-docs').value = state.pdf.name;
  }
  function onLogInput(e) {
    var tr = e.target.closest('tr'); if (!tr) return;
    var id = +tr.getAttribute('data-id');
    state.log[id] = state.log[id] || {};
    if (e.target.classList.contains('log-date')) state.log[id].date = e.target.value;
    if (e.target.classList.contains('log-method')) state.log[id].method = e.target.value;
  }
  function exportLogCsv() {
    var rows = [['id', 'name', 'address', 'date_mailed', 'method', 'documents', 'declarant']];
    state.recipients.forEach(function (r) { var l = state.log[r.id] || {}; rows.push([r.id, r.name, r.lines.join(' | '), l.date || '', l.method || '', normLine($('log-docs').value), normLine($('declarant').value)]); });
    var csv = Papa.unparse(rows);
    var blob = new Blob([csv], { type: 'text/csv' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a'); a.href = url; a.download = 'service-log.csv'; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
  }
  function exportLogPdf() {
    buildLogPdf().then(function (b) {
      var blob = new Blob([b], { type: 'application/pdf' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a'); a.href = url; a.download = 'service-log-worksheet.pdf'; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
    }).catch(function (err) { announce('Export failed: ' + String(err && err.message || err), true); });
  }

  /* ---------- reset ---------- */
  function resetAll() {
    revokeOutputs();
    state.recipients = []; state.nextId = 1; state.pdf = null; state.log = {}; state.generatedAt = null;
    ['paste', 'return-address', 'declarant', 'log-docs'].forEach(function (id) { $(id).value = ''; });
    $('csv-file').value = ''; $('pdf-file').value = ''; $('pdf-confirm').checked = false; $('pdf-info').textContent = '';
    renderRecipients(); $('summary').textContent = ''; $('step-log').hidden = true; $('log-body').innerHTML = '';
    announce('Cleared. Nothing was stored.');
  }

  /* ---------- wiring ---------- */
  function init() {
    if (!window.PDFLib || !window.Papa) { announce('A required library did not load. Reload the page.', true); return; }
    loadDistricts();
    $('district').addEventListener('change', onDistrictChange);
    $('paste-add').addEventListener('click', function () { var n = parsePaste($('paste').value); $('paste').value = ''; renderRecipients(); announce(n + ' recipient' + (n === 1 ? '' : 's') + ' added from pasted text.'); });
    $('csv-file').addEventListener('change', function (e) {
      var f = e.target.files && e.target.files[0]; if (!f) return;
      f.text().then(function (t) { var n = parseCSVText(t); renderRecipients(); announce(n + ' recipient' + (n === 1 ? '' : 's') + ' added from ' + f.name + '.'); e.target.value = ''; }).catch(function (err) { announce('Could not read that file: ' + err.message, true); });
    });
    $('manual-add').addEventListener('click', function () { var r = addRecipient($('manual').value.replace(/\r\n?/g, '\n').split('\n'), 'manual'); $('manual').value = ''; renderRecipients(); announce(r ? 'Recipient #' + r.id + ' added.' : 'Type a name and address first.', !r); });
    $('recipients-body').addEventListener('input', onRecipientEdit);
    $('recipients-body').addEventListener('change', function () { renderRecipients(); });
    $('recipients-body').addEventListener('click', onRecipientClick);
    $('pdf-file').addEventListener('change', onPdfFile);
    $('pdf-confirm').addEventListener('change', function (e) { if (state.pdf) state.pdf.confirmed = e.target.checked; });
    $('test-sheet').addEventListener('click', function () { buildLabels(true).then(function (b) { addOutput('label-alignment-test.pdf', b, 'test'); announce('Alignment test sheet added to the downloads list.'); }).catch(function (err) { announce('Could not build the test sheet: ' + err.message, true); }); });
    $('generate').addEventListener('click', generate);
    ['m-labels', 'm-envelopes', 'm-packets', 'm-checklist', 'm-log', 'separator'].forEach(function (id) { $(id).addEventListener('change', summary); });
    $('log-body').addEventListener('input', onLogInput);
    $('log-body').addEventListener('change', onLogInput);
    $('log-csv').addEventListener('click', exportLogCsv);
    $('log-pdf').addEventListener('click', exportLogPdf);
    $('reset').addEventListener('click', function () { if (window.confirm('Clear all recipients, the PDF, generated files, and the log?')) resetAll(); });
    renderRecipients();
  }
  /* read-only accessor for automated tests; exposes the generated blobs of THIS tab only */
  window.obpKitOutputs = function () { return state.outputs.map(function (o) { return { label: o.label, blob: o.blob }; }); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
