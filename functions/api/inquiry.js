// Cloudflare Pages Function -> POST /api/inquiry
// Persists the submission to a private R2 bucket and optionally emails the sales desk.
//
// Required bindings / env vars (set in Cloudflare Pages > Settings > Environment variables,
// or in wrangler.toml for local dev):
//   INQUIRY_BUCKET        R2 bucket binding  (private bucket, e.g. "oz-inquiries")
//   RESEND_API_KEY        optional - Resend API key
//   NOTIFICATION_EMAIL_TO optional - inbox that receives the notification

const MAX = {
  name: 120,
  company: 160,
  email: 200,
  country: 120,
  messenger: 120,
  quantity: 120,
  timeline: 80,
  inquiryType: 120,
  reference: 500,
  details: 4000,
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function clean(value, limit) {
  if (value === undefined || value === null) return '';
  return String(value).trim().slice(0, limit);
}

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  });
}

const CORS = {
  'Access-Control-Allow-Origin': 'https://ozfurnishing.com',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: CORS });
}

export async function onRequestPost({ request, env }) {
  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ ok: false, error: 'Malformed JSON body.' }, 400);
  }
  if (!payload || typeof payload !== 'object') {
    return json({ ok: false, error: 'Malformed JSON body.' }, 400);
  }

  const record = {};
  for (const [field, limit] of Object.entries(MAX)) {
    record[field] = clean(payload[field], limit);
  }

  const missing = ['name', 'email', 'details'].filter((f) => !record[f]);
  if (missing.length) {
    return json({ ok: false, error: 'Missing required fields: ' + missing.join(', ') }, 400);
  }
  if (!EMAIL_RE.test(record.email)) {
    return json({ ok: false, error: 'Please provide a valid email address.' }, 400);
  }

  record.receivedAt = new Date().toISOString();
  record.userAgent = (request.headers.get('User-Agent') || '').slice(0, 300);
  record.country = record.country || request.headers.get('CF-IPCountry') || '';

  const storedKey = await persist(env, record);
  const mailed = await notify(env, record);

  if (!storedKey && !mailed) {
    console.error('[inquiry] no R2 binding and no email config - submission dropped');
    return json({ ok: false, error: 'Inquiry endpoint is not configured yet.' }, 503);
  }

  if (storedKey) console.log('[inquiry] stored at', storedKey);

  // Only booleans leave the edge - the R2 key stays server-side.
  return json({
    ok: true,
    id: record.receivedAt,
    persisted: Boolean(storedKey),
    notified: mailed,
  }, 200);
}

async function persist(env, record) {
  const bucket = env && env.INQUIRY_BUCKET;
  if (!bucket || typeof bucket.put !== 'function') return false;

  const day = record.receivedAt.slice(0, 10);
  const stamp = record.receivedAt.replace(/[:.]/g, '-');
  const rand = Math.random().toString(36).slice(2, 8);
  const key = `inquiries/${day}/${stamp}-${rand}.json`;

  await bucket.put(key, JSON.stringify(record, null, 2), {
    httpMetadata: { contentType: 'application/json; charset=utf-8' },
  });
  return key;
}

async function notify(env, record) {
  const apiKey = env && env.RESEND_API_KEY;
  const to = env && env.NOTIFICATION_EMAIL_TO;
  if (!apiKey || !to) return false;

  const subject = `[Website Inquiry] ${record.inquiryType || 'General'} - ${record.name}`;
  const text = [
    'New inquiry from ozfurnishing.com',
    '---------------------------------',
    `Received : ${record.receivedAt}`,
    `Type     : ${record.inquiryType || '-'}`,
    `Name     : ${record.name}`,
    `Company  : ${record.company || '-'}`,
    `Email    : ${record.email}`,
    `Messenger: ${record.messenger || '-'}`,
    `Market   : ${record.country || '-'}`,
    `Quantity : ${record.quantity || '-'}`,
    `Timeline : ${record.timeline || '-'}`,
    `Reference: ${record.reference || '-'}`,
    '',
    'Details:',
    record.details,
  ].join('\n');

  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'OZ Website <onboarding@resend.dev>',
        to: [to],
        reply_to: record.email,
        subject,
        text,
      }),
    });
    if (!res.ok) {
      console.error('[inquiry] resend failed', res.status, await res.text());
      return false;
    }
    return true;
  } catch (err) {
    console.error('[inquiry] resend error', err);
    return false;
  }
}
