/* OZ first-party analytics worker (Cloudflare Workers + D1).
 *
 * Why this exists: track.js already fires 7 event types into GA4, but those
 * rows live in Google's warehouse. We own nothing we can join, attribute or
 * replay. This worker captures the same events as first-party rows in our own
 * D1, aggregates them on a daily Cron, and serves the result back to the local
 * daily-SEO board via /a/report. That is the "self-built data loop": collect
 * -> store -> aggregate -> back-feed the board -> decide -> publish -> collect.
 *
 * Endpoints
 *   POST /a/collect                 beacon from assets/track.js
 *   GET  /a/report?date=YYYY-MM-DD  JSON report for _daily_seo.py pull
 * Schedule
 *   30 0 * * *  (00:30 UTC = 08:30 Beijing) aggregates the UTC day just ended.
 */

const DAY = 86400000;

function fmtDate(d) {
  return d.toISOString().slice(0, 10); // YYYY-MM-DD (UTC)
}

function deviceFrom(ua) {
  ua = (ua || '').toLowerCase();
  if (/bot|spider|crawl|slurp|bingpreview|facebookexternalhit/.test(ua)) return 'bot';
  if (/ipad|tablet/.test(ua)) return 'tablet';
  if (/mobile|android|iphone|ipod/.test(ua)) return 'mobile';
  return 'desktop';
}

/* ---------------------------------------------------------------- */
/* Collect                                                            */
/* ---------------------------------------------------------------- */
async function handleCollect(request, env) {
  // Always 204. A failed beacon must never break the page or the form.
  let body = null;
  try {
    const text = await request.text();
    body = text ? JSON.parse(text) : null;
  } catch (_) { /* ignore malformed */ }
  if (body && body.event) {
    try {
      const ua = request.headers.get('User-Agent') || '';
      const known = new Set(['event', 'page', 'v', 's', 'src', 'med', 'cmp']);
      const extra = {};
      for (const k of Object.keys(body)) if (!known.has(k)) extra[k] = body[k];
      await env.DB.prepare(
        `INSERT INTO events (ts, type, path, referrer, source, medium, campaign,
                             visitor, session, device, country, extra)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      ).bind(
        Date.now(),
        String(body.event).slice(0, 64),
        (body.page || '/').slice(0, 200),
        (request.headers.get('Referer') || '').slice(0, 500),
        (body.src || 'direct').slice(0, 64),
        (body.med || '').slice(0, 64),
        (body.cmp || '').slice(0, 64),
        (body.v || '').slice(0, 64),
        (body.s || '').slice(0, 64),
        deviceFrom(ua),
        (request.cf && request.cf.country) || '',
        JSON.stringify(extra).slice(0, 2000)
      ).run();
    } catch (_) { /* storage failure must not surface to the client */ }
  }
  return new Response(null, { status: 204 });
}

/* ---------------------------------------------------------------- */
/* Report                                                            */
/* ---------------------------------------------------------------- */
async function buildReport(date, env) {
  const start = Date.parse(date + 'T00:00:00Z');
  const end = start + DAY;

  const one = async (sql, ...args) =>
    (await env.DB.prepare(sql).bind(...args).first()) || {};
  const all = async (sql, ...args) =>
    (await env.DB.prepare(sql).bind(...args).all()).results || [];

  const totals = await one(
    `SELECT COUNT(*) AS rows,
            COUNT(DISTINCT session) AS sessions
       FROM events WHERE ts >= ? AND ts < ? AND type = 'page_view'`,
    start, end);
  const pageviews = totals.rows || 0;
  const visits = totals.sessions || 0;

  const breakdown = await all(
    `SELECT type, COUNT(*) AS c FROM events
       WHERE ts >= ? AND ts < ? GROUP BY type ORDER BY c DESC`,
    start, end);
  const events = {};
  for (const r of breakdown) events[r.type] = r.c;

  // "conversion" = any intentional contact action
  const convTypes = ['quote_request', 'whatsapp_click', 'email_click', 'phone_click'];
  const conversions = convTypes.reduce((a, t) => a + (events[t] || 0), 0);

  const topPages = await all(
    `SELECT path, COUNT(*) AS c FROM events
       WHERE ts >= ? AND ts < ? AND type = 'page_view'
       GROUP BY path ORDER BY c DESC LIMIT 10`,
    start, end);
  const topSources = await all(
    `SELECT COALESCE(NULLIF(source,''),'direct') AS s, COUNT(*) AS c
       FROM events WHERE ts >= ? AND ts < ? AND type = 'page_view'
       GROUP BY s ORDER BY c DESC LIMIT 10`,
    start, end);

  // per-page: pageviews vs contact actions, for the insights
  const pvByPage = {};
  for (const r of topPages) pvByPage[r.path] = r.c;
  const contactRows = await all(
    `SELECT path, COUNT(*) AS c FROM events
       WHERE ts >= ? AND ts < ? AND type IN (${convTypes.map(() => '?').join(',')})
       GROUP BY path`,
    start, end, ...convTypes);
  const contactByPage = {};
  for (const r of contactRows) contactByPage[r.path] = r.c;

  const allPages = await all(
    `SELECT DISTINCT path FROM events WHERE ts >= ? AND ts < ? AND type='page_view'`,
    start, end);
  const pages = allPages.map(r => ({
    path: r.path,
    visits: pvByPage[r.path] || 0,
    contact: contactByPage[r.path] || 0,
  })).sort((a, b) => b.visits - a.visits);

  const ranked = pages.filter(p => p.contact > 0).sort((a, b) => b.contact - a.contact);
  const dead = pages
    .filter(p => p.visits >= 20 && p.contact === 0)
    .sort((a, b) => b.visits - a.visits);

  const suggestions = [];
  if (ranked[0]) suggestions.push(
    `转化最高页 ${ranked[0].path}（${ranked[0].contact} 次联系 / ${ranked[0].visits} 访问）—— 复制它的 CTA 写法到其它成交页`);
  for (const p of dead.slice(0, 3)) suggestions.push(
    `高流量零转化：${p.path}（${p.visits} 访问无联系）—— 加显眼询盘入口，或补「为什么选我们」`);

  return {
    date,
    generated: new Date().toISOString(),
    empty: pageviews === 0,
    visits,
    pageviews,
    conversions,
    conv_rate: visits ? +(conversions / visits * 100).toFixed(2) : 0,
    events,
    top_pages: topPages,
    top_sources: topSources,
    by_page: pages,
    insights: {
      top_converting: ranked.slice(0, 5).map(p => p.path),
      high_traffic_no_conversion: dead.slice(0, 5).map(p => p.path),
      suggestions,
    },
  };
}

async function handleReport(request, env) {
  const url = new URL(request.url);
  let date = url.searchParams.get('date');
  if (!date) {
    // default: the UTC day before the request
    date = fmtDate(new Date(Date.now() - DAY));
  }
  // Prefer the precomputed daily_report row (Cron), fall back to live compute.
  const cached = await env.DB.prepare(
    `SELECT payload FROM daily_report WHERE date = ?`).bind(date).first();
  let report = null;
  if (cached && cached.payload) {
    try { report = JSON.parse(cached.payload); } catch (_) {}
  }
  if (!report) report = await buildReport(date, env);
  return new Response(JSON.stringify(report), {
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}

/* ---------------------------------------------------------------- */
/* Daily Cron aggregation                                            */
/* ---------------------------------------------------------------- */
async function aggregate(date, env) {
  const report = await buildReport(date, env);
  await env.DB.prepare(
    `INSERT INTO daily_report (date, generated, payload)
     VALUES (?, ?, ?)
     ON CONFLICT(date) DO UPDATE SET generated = excluded.generated,
                                     payload = excluded.payload`
  ).bind(date, Date.now(), JSON.stringify(report)).run();
  return report;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === 'POST' && url.pathname === '/a/collect') {
      return handleCollect(request, env);
    }
    if (request.method === 'GET' && url.pathname === '/a/report') {
      return handleReport(request, env);
    }
    return new Response('Not found', { status: 404 });
  },

  async scheduled(event, env, ctx) {
    const yesterday = fmtDate(new Date(Date.now() - DAY));
    const report = await aggregate(yesterday, env);
    return new Response('aggregated ' + yesterday +
      ' · visits=' + report.visits + ' conversions=' + report.conversions);
  },
};
