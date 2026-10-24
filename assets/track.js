/* OZ International - conversion tracking
 *
 * Five events, one file. Without these GA4 can tell you how many people
 * arrived and nothing about what they did, so the answer to "why no enquiry"
 * is a guess. With them, every lead has a path back to the page that produced
 * it and the channel that brought the visitor.
 *
 *   quote_request     form submitted successfully (the only true conversion)
 *   quote_fallback    form failed, visitor was handed the email/copy route
 *   whatsapp_click    WhatsApp tapped
 *   email_click       mailto tapped
 *   phone_click       tel tapped
 *
 * Design notes
 * - Uses the plain `gtag` queue rather than a separate GA4 import: the queue
 *   exists before gtag.js finishes downloading, so nothing fired early is lost.
 * - Delegated at the document level. The site is static, and generated pages
 *   are rewritten by tools/gen_*.py, so per-element onclick handlers would be
 *   wiped by the next generator run.
 * - Never sends form contents. Only which fields were filled in, which is
 *   enough to see where people abandon without putting buyer data in GA4.
 * - Safe when GA4 is absent (blocked, offline): every call is guarded, so this
 *   cannot break the form.
 */
(function () {
  'use strict';

  /* ---------------------------------------------------------------- */
  /* First-party beacon. Mirror every event into our own D1 via the    */
  /* oz-analytics Worker, fully independent of GA4. If GA4 is blocked  */
  /* the beacon still fires; if the Worker is unreachable the page is   */
  /* untouched (sendBeacon losses are silent). This is the "self-built  */
  /* data loop": we own the raw rows we can attribute and replay.       */
  /* ---------------------------------------------------------------- */
  var BEACON_URL = 'https://ozfurnishing.com/a/collect';

  // Persistent anonymous visitor id (first-party only, no PII). Stays
  // across visits so we can tell returning visitors from new ones.
  var VISITOR = (function () {
    try {
      var k = 'oz_v';
      var v = localStorage.getItem(k);
      if (!v) {
        v = 'v' + Math.random().toString(36).slice(2) + Date.now().toString(36);
        localStorage.setItem(k, v);
      }
      return v;
    } catch (e) { return 'anon'; }
  })();

  // Per-visit session id, shared across tabs in a session.
  var SESSION = (function () {
    try {
      var k = 'oz_s';
      var s = sessionStorage.getItem(k);
      if (!s) {
        s = 's' + Math.random().toString(36).slice(2);
        sessionStorage.setItem(k, s);
      }
      return s;
    } catch (e) { return 's' + Math.random().toString(36).slice(2); }
  })();

  // Acquisition attribution, read once from the entry URL.
  var ATTR = (function () {
    var q = new URLSearchParams(location.search);
    var src = q.get('utm_source') || q.get('ref');
    if (!src) src = document.referrer ? 'referral' : 'direct';
    return { source: src, medium: q.get('utm_medium') || '',
             campaign: q.get('utm_campaign') || '' };
  })();

  function beacon(name, params) {
    try {
      if (!navigator.sendBeacon) return;
      var p = Object.assign({ event: name, page: pageKey() }, params || {});
      p.v = VISITOR; p.s = SESSION;
      p.src = ATTR.source; p.med = ATTR.medium; p.cmp = ATTR.campaign;
      navigator.sendBeacon(BEACON_URL,
        new Blob([JSON.stringify(p)], { type: 'application/json' }));
    } catch (e) {}
  }

  function track(name, params) {
    beacon(name, params);                 // first-party, always
    if (typeof window.gtag !== 'function') return;
    window.gtag('event', name, params || {});
  }

  /* Page identity, normalised: extension-less, no trailing slash, so
     /sourcing/home-decor and /sourcing/home-decor.html do not split in GA4. */
  function pageKey() {
    return (location.pathname.replace(/\.html$/, '').replace(/\/$/, '') || '/');
  }

  /* ---------------------------------------------------------------- */
  /* Outbound contact clicks                                           */
  /* ---------------------------------------------------------------- */
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var href = a.getAttribute('href') || '';

    if (/^https?:\/\/(wa\.me|api\.whatsapp\.com)/i.test(href)) {
      track('whatsapp_click', { page: pageKey() });
    } else if (/^tel:/i.test(href)) {
      track('phone_click', { page: pageKey() });
    } else if (/^mailto:/i.test(href)) {
      // Distinguish the header/footer link from the form's fallback button,
      // which is only ever reachable after a submission actually failed.
      track('email_click', {
        page: pageKey(),
        context: a.id === 'mailLink' ? 'form-fallback' : 'direct'
      });
    }
  }, { passive: true });

  /* ---------------------------------------------------------------- */
  /* Enquiry form                                                      */
  /* ---------------------------------------------------------------- */
  /* main.js owns the submission. Rather than reach into it, watch the status
     line the visitor sees:
       class contains 'ok'   -> the enquiry reached the server   = conversion
       class contains 'warn' -> they were handed the fallback     = lost lead
     Reading the DOM keeps this file independent of the form's internals.

     `formMsg` is only ever given a class by main.js's setMsg (which always
     starts from 'form-msg'), so a [class] observer catches every outcome. */
  function watchForm() {
    var form = document.getElementById('inquiryForm');
    var msg = document.getElementById('formMsg');
    if (!form || !msg) return;

    var fired = false;      // one outcome per page view, however busy the visitor
    var started = false;
    var missing = [];

    form.addEventListener('input', function () {
      if (started) return;
      started = true;
      track('quote_form_start', { page: pageKey() });
    }, { passive: true });

    // Snapshot the gaps at the moment of submit, before a success resets the
    // form. A field that is blank on most attempts is either confusing or
    // unnecessary, and that is worth knowing before touching the design.
    form.addEventListener('submit', function () {
      missing = [];
      ['name', 'email', 'country', 'inquiryType', 'details'].forEach(function (k) {
        var el = form.querySelector('[name="' + k + '"]');
        if (el && !String(el.value || '').trim()) missing.push(k);
      });
    }, true);

    var lastClass = msg.className;

    function read() {
      if (fired) return;
      var kind = msg.className || '';
      if (kind.indexOf('ok') !== -1) {
        fired = true;
        track('quote_request', {
          page: pageKey(),
          fields_filled: countFilled(form),
          missing_fields: missing.join(',')
        });
      } else if (kind.indexOf('warn') !== -1) {
        fired = true;
        track('quote_fallback', {
          page: pageKey(),
          missing_fields: missing.join(',')
        });
      }
    }

    // Attribute=class filter plus a value check: MutationObserver does report
    // same-value assignments in current browsers, but the guard costs nothing
    // and keeps this correct if that ever tightens.
    new MutationObserver(function () {
      if (msg.className !== lastClass) {
        lastClass = msg.className;
        read();
      }
    }).observe(msg, { attributes: true, attributeFilter: ['class'] });
  }

  function countFilled(form) {
    var n = 0;
    ['name', 'company', 'email', 'country', 'messenger', 'inquiryType',
     'quantity', 'timeline', 'details', 'reference'].forEach(function (k) {
      var el = form.querySelector('[name="' + k + '"]');
      if (el && String(el.value || '').trim()) n++;
    });
    return n;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watchForm);
  } else {
    watchForm();
  }

  /* First-party page view. GA4 records this separately; this is ours, so the
     visit count and the per-page conversion funnel live in our own D1. */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { beacon('page_view', {}); });
  } else {
    beacon('page_view', {});
  }

  /* Scroll depth: a buyer who reaches 90% of the pillar page has done real
     reading. Useful for telling "nobody reads" from "nobody converts". */
  (function () {
    var marks = [50, 90], hit = {};
    window.addEventListener('scroll', function () {
      var d = document.documentElement;
      var pct = (window.scrollY + window.innerHeight) / d.scrollHeight * 100;
      marks.forEach(function (m) {
        if (!hit[m] && pct >= m) {
          hit[m] = true;
          track('scroll_depth', { page: pageKey(), percent: m });
        }
      });
    }, { passive: true });
  })();
})();
