/* OZ International - site interactions */

var CONTACT_EMAIL = '807735000@qq.com';

/* Where the enquiry form posts.
 *
 * WEB3FORMS (current setup): the access key below is a public identifier, not
 * a secret - it is safe in client-side code and simply routes to our inbox.
 * Free tier is 250 submissions / month.
 *
 * SELF-HOSTED (optional): if you ever bind an R2 bucket to the Pages
 * Function, set INQUIRY_ENDPOINT back to '/api/inquiry'. Nothing else needs
 * to change.
 */
var INQUIRY_ENDPOINT = 'https://api.web3forms.com/submit';
var WEB3FORMS_KEY = '122af944-77ab-49a7-b4a0-fb440fa896ad';

/* Absolute third-party endpoint (Web3Forms) vs our own Pages Function.
 * Controls which fields and headers we send. */
var ENDPOINT_IS_FORM_SERVICE = /^https?:\/\//i.test(INQUIRY_ENDPOINT);

/* Clipboard helper: async API with a legacy execCommand fallback. */
function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise(function (resolve, reject) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
    document.body.removeChild(ta);
    ok ? resolve() : reject(new Error('copy failed'));
  });
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-year]').forEach(function (el) { el.textContent = new Date().getFullYear(); });

  /* ---- Footer WeChat id: click to copy ---- */
  document.querySelectorAll('.wechat-copy').forEach(function (btn) {
    var id = btn.getAttribute('data-copy-id') || btn.textContent.trim();
    var restore = null;
    btn.addEventListener('click', function () {
      copyText(id).then(function () {
        btn.textContent = 'Copied: ' + id;
        btn.classList.add('copied');
        clearTimeout(restore);
        restore = setTimeout(function () {
          btn.textContent = id;
          btn.classList.remove('copied');
        }, 1800);
      }, function () {
        btn.textContent = id;
      });
    });
  });

  /* ---- Mobile navigation: drawer + backdrop ---- */
  var toggle = document.querySelector('.menu-toggle');
  var links = document.querySelector('.links');
  var overlay = document.querySelector('.nav-overlay');

  function setNav(open) {
    if (links) links.classList.toggle('open', open);
    if (overlay) overlay.classList.toggle('show', open);
    if (toggle) {
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.textContent = open ? 'CLOSE −' : 'MENU +';
    }
    document.body.classList.toggle('nav-open', open);
  }

  if (toggle && links) {
    toggle.addEventListener('click', function () { setNav(!links.classList.contains('open')); });
    links.addEventListener('click', function (e) { if (e.target.closest('a')) setNav(false); });
  }
  if (overlay) overlay.addEventListener('click', function () { setNav(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setNav(false); });
  window.addEventListener('resize', function () { if (window.innerWidth > 780) setNav(false); });

  /* ---- FAQ accordion: animated height + rotating icon ---- */
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.querySelectorAll('.faq-list details').forEach(function (item) {
    var summary = item.querySelector('summary');
    var body = item.querySelector('.faq-body');
    if (!summary || !body) return;

    // Run the end-of-animation step on transitionend, with a timer fallback so the
    // panel always settles even when no transition fires (reduced motion, hidden tab).
    function settle(done) {
      var fired = false;
      function handler() {
        if (fired) return;
        fired = true;
        body.removeEventListener('transitionend', handler);
        clearTimeout(timer);
        done();
      }
      var timer = setTimeout(handler, 380);
      body.addEventListener('transitionend', handler);
    }

    function expand() {
      item.open = true;
      if (reduceMotion) { body.style.height = ''; return; }
      body.style.height = '0px';
      var target = body.scrollHeight;
      requestAnimationFrame(function () { body.style.height = target + 'px'; });
      settle(function () { body.style.height = ''; });
    }

    function collapse() {
      if (reduceMotion) { item.open = false; body.style.height = ''; return; }
      body.style.height = body.scrollHeight + 'px';
      requestAnimationFrame(function () { body.style.height = '0px'; });
      settle(function () { item.open = false; body.style.height = ''; });
    }

    summary.addEventListener('click', function (e) {
      e.preventDefault();
      if (item.open) { collapse(); } else { expand(); }
    });
  });

  /* ---- Hero image carousel (homepage) ---- */
  var carousel = document.getElementById('heroCarousel');
  if (carousel) {
    var slides = Array.prototype.slice.call(carousel.querySelectorAll('.slide'));
    var dots = Array.prototype.slice.call(carousel.querySelectorAll('.slide-dots button'));
    var kicker = document.getElementById('slideKicker');
    var title = document.getElementById('slideTitle');
    var serial = document.getElementById('slideSerial');
    var current = 0;
    var timer = null;
    var DELAY = 5500;

    function pad(n) { return (n < 9 ? '0' : '') + (n + 1); }
    function padTotal(n) { return (n < 10 ? '0' : '') + n; }

    function show(i) {
      current = (i + slides.length) % slides.length;
      slides.forEach(function (s, k) { s.classList.toggle('is-active', k === current); });
      dots.forEach(function (d, k) {
        d.classList.toggle('is-active', k === current);
        d.setAttribute('aria-pressed', k === current ? 'true' : 'false');
      });
      var slide = slides[current];
      if (kicker) kicker.textContent = slide.getAttribute('data-kicker') || '';
      if (title) title.innerHTML = slide.getAttribute('data-title') || '';
      if (serial) serial.textContent = pad(current) + ' / ' + padTotal(slides.length);
    }

    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function play() { stop(); if (!reduceMotion) timer = setInterval(function () { show(current + 1); }, DELAY); }

    dots.forEach(function (dot, k) {
      dot.addEventListener('click', function () { show(k); play(); });
    });

    // click anywhere on the visual to advance
    carousel.addEventListener('click', function (e) {
      if (e.target.closest('.slide-dots')) return;
      show(current + 1);
      play();
    });

    carousel.addEventListener('mouseenter', stop);
    carousel.addEventListener('mouseleave', play);
    document.addEventListener('visibilitychange', function () { document.hidden ? stop() : play(); });

    show(0);
    play();
  }

  /* ---- Pre-fill inquiry form from URL parameters ---- */
  var params = new URLSearchParams(window.location.search);
  var type = params.get('type');
  var category = params.get('category');
  var typeMap = { product: 'Small-value product sourcing', business: 'B2B / bulk procurement', project: 'Engineering / project procurement', bulk: 'B2B / bulk procurement', custom: 'OEM / custom product', logistics: 'Logistics / delivery coordination' };
  var select = document.getElementById('inquiryType');
  if (select && type && typeMap[type]) select.value = typeMap[type];
  var field = document.getElementById('productField');
  if (field && category) field.value = 'I am interested in sourcing category: ' + category + '. Please contact me with suitable options.';

  /* ---- Inquiry form: submit to Pages Function, mailto fallback ---- */
  var form = document.getElementById('inquiryForm');
  if (form) {
    var msg = document.getElementById('formMsg');
    var success = document.getElementById('formSuccess');
    var mailLink = document.getElementById('mailLink');
    var copyBtn = document.getElementById('copyBtn');
    var submitBtn = form.querySelector('.form-submit');

    var FIELDS = ['name', 'company', 'email', 'country', 'messenger',
                  'inquiryType', 'quantity', 'timeline', 'details', 'reference'];
    var LABELS = {
      name: 'Name', company: 'Company', email: 'Email',
      country: 'Destination / Market', messenger: 'WhatsApp / WeChat',
      inquiryType: 'Inquiry Type', quantity: 'Estimated Quantity',
      timeline: 'Target Timeline', details: 'Product / Project Details',
      reference: 'Reference Link'
    };

    function collect() {
      var data = new FormData(form);
      var out = {};
      FIELDS.forEach(function (k) {
        var v = data.get(k);
        out[k] = v === null || v === undefined ? '' : String(v).trim();
      });
      return out;
    }

    function draftOf(values) {
      var subject = '[OZ Website Inquiry] ' + (values.inquiryType || 'General inquiry');
      var lines = FIELDS.filter(function (k) { return values[k]; })
                        .map(function (k) { return LABELS[k] + ': ' + values[k]; });
      lines.push('', 'Sent from the OZ International website.');
      return {
        subject: subject,
        body: lines.join('\n\n'),
        text: subject + '\n\n' + lines.join('\n\n')
      };
    }

    function setMsg(text, kind) {
      if (!msg) return;
      msg.textContent = text || '';
      msg.className = 'form-msg' + (text ? ' show' : '') + (kind ? ' ' + kind : '');
    }

    // Always arm the mailto + copy fallback so a visitor is never stranded.
    function armFallback(draft) {
      if (mailLink) {
        mailLink.setAttribute('href',
          'mailto:' + CONTACT_EMAIL +
          '?subject=' + encodeURIComponent(draft.subject) +
          '&body=' + encodeURIComponent(draft.body));
      }
      if (copyBtn) copyBtn.setAttribute('data-copy', draft.text);
    }

    function useFallback(note) {
      setMsg(note, 'warn');
      if (success) {
        success.classList.add('show');
        if (success.scrollIntoView) success.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }

    // The endpoint may legitimately be unconfigured (no R2 bucket bound yet).
    // Never surface that plumbing detail to a buyer - turn it into the same
    // "pick a channel" step they would see on any other failure.
    function friendlyNote(serverError) {
      if (/not configured|unavailable|service|quota|limit/i.test(serverError)) {
        return 'Your enquiry is ready below. Send it by email, or copy the details into WhatsApp or WeChat - whichever suits you.';
      }
      if (serverError) return serverError;
      return 'We could not record your enquiry automatically. Your details are ready below - send them by email or copy them into WhatsApp or WeChat.';
    }

    // Web3Forms takes the access key in the body and understands a handful of
    // reserved names. Our own Pages Function wants the plain values, so the
    // payload differs only by these extra keys.
    function payloadFor(values, draft) {
      if (!ENDPOINT_IS_FORM_SERVICE) return values;
      var out = { access_key: WEB3FORMS_KEY };
      FIELDS.forEach(function (k) { out[k] = values[k]; });
      out.subject = draft.subject;       // email subject line
      out.email = values.email;          // sets the reply-to address
      out.replyto = CONTACT_EMAIL;
      out.botcheck = '';                 // honeypot: must stay empty
      return out;
    }

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      if (!form.reportValidity()) return;

      var values = collect();
      var draft = draftOf(values);
      armFallback(draft);

      // Honeypot tripped -> it is a bot. Show the same success a human would
      // see so it has nothing to learn from the response, and send nothing.
      var gotcha = form.querySelector('[name="botcheck"]') ||
                   form.querySelector('[name="_gotcha"]');
      if (gotcha && gotcha.value) {
        setMsg('Thank you - your enquiry has been received. Our team will reply within one business day.', 'ok');
        form.reset();
        return;
      }

      if (submitBtn) submitBtn.disabled = true;
      setMsg('Preparing your enquiry...', '');

      try {
        var res = await fetch(INQUIRY_ENDPOINT, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(payloadFor(values, draft))
        });
        var data = null;
        try { data = await res.json(); } catch (err) { /* non-JSON error body */ }

        if (res.status === 429) {
          useFallback('We are receiving more enquiries than our plan allows right now. Please send yours by email or copy the details below - we will reply either way.');
          return;
        }

        // Web3Forms answers {success:true, body:{message:...}}.
        // Our own Pages Function answers {ok:true}.
        var good;
        if (ENDPOINT_IS_FORM_SERVICE) {
          good = res.ok && data && data.success !== false;
        } else {
          good = res.ok && data && data.ok;
        }
        if (!good) {
          var serverError = '';
          if (data && data.body && data.body.message) serverError = data.body.message;
          else if (data && data.error) serverError = data.error;
          else if (data && data.errors && data.errors.length) {
            serverError = data.errors.map(function (e) { return e.message || e; }).join(' ');
          }
          useFallback(friendlyNote(serverError));
          return;
        }

        setMsg('Thank you - your inquiry has been received. Our team will reply within one business day.', 'ok');
        if (success) success.classList.remove('show');
        form.reset();
        if (msg && msg.scrollIntoView) msg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } catch (err) {
        useFallback('Your enquiry is ready below. Send it by email, or copy the details into WhatsApp or WeChat - whichever suits you.');
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });

    if (copyBtn) {
      var flash = function () {
        var original = copyBtn.textContent;
        copyBtn.textContent = 'Copied ✓';
        setTimeout(function () { copyBtn.textContent = original; }, 1800);
      };
      copyBtn.addEventListener('click', function () {
        copyText(copyBtn.getAttribute('data-copy') || '').then(flash, flash);
      });
    }
  }
});
