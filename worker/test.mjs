// Local smoke test for the real worker module using an in-memory fake D1.
// No Cloudflare token needed. Run:  node worker/_test.mjs
import worker from './src/index.js';

const DAY = 86400000;
const DATE = '2026-10-23';
const start = Date.parse(DATE + 'T00:00:00Z');
const end = start + DAY;

// seed some first-party events for that day
const events = [
  { ts: start + 1000,  type: 'page_view',      path: '/sourcing/home-decor', session: 's1', source: 'google' },
  { ts: start + 2000,  type: 'page_view',      path: '/sourcing/home-decor', session: 's2', source: 'google' },
  { ts: start + 3000,  type: 'page_view',      path: '/about',               session: 's3', source: 'direct' },
  { ts: start + 4000,  type: 'page_view',      path: '/about',               session: 's4', source: 'direct' },
  { ts: start + 5000,  type: 'page_view',      path: '/about',               session: 's5', source: 'referral' },
  { ts: start + 6000,  type: 'quote_request',  path: '/sourcing/home-decor', session: 's1', source: 'google' },
  { ts: start + 7000,  type: 'whatsapp_click', path: '/sourcing/home-decor', session: 's2', source: 'google' },
  { ts: start + 8000,  type: 'email_click',    path: '/about',               session: 's3', source: 'direct' },
  { ts: start + 9000,  type: 'scroll_depth',   path: '/about',               session: 's4', source: 'direct' },
];

function rowsInRange() { return events.filter(e => e.ts >= start && e.ts < end); }

const fakeDB = {
  prepare(sql) {
    return {
      bind(...args) {
        return {
          async first() {
            if (sql.includes('payload')) return undefined;          // no cache yet
            if (sql.includes('COUNT(DISTINCT session)')) {
              const r = rowsInRange().filter(e => e.type === 'page_view');
              return { rows: r.length, sessions: new Set(r.map(e => e.session)).size };
            }
            return {};
          },
          async all() {
            const r = rowsInRange();
            if (sql.includes('type, COUNT')) {
              const m = {};
              r.forEach(e => m[e.type] = (m[e.type] || 0) + 1);
              return { results: Object.entries(m).map(([type, c]) => ({ type, c })) };
            }
            if (sql.includes("type = 'page_view'") && sql.includes('GROUP BY path') && !sql.includes('DISTINCT')) {
              const m = {};
              r.filter(e => e.type === 'page_view').forEach(e => m[e.path] = (m[e.path] || 0) + 1);
              return { results: Object.entries(m).map(([path, c]) => ({ path, c })) };
            }
            if (sql.includes('COALESCE(NULLIF(source')) {
              const m = {};
              r.filter(e => e.type === 'page_view').forEach(e => {
                const s = e.source || 'direct'; m[s] = (m[s] || 0) + 1;
              });
              return { results: Object.entries(m).map(([s, c]) => ({ s, c })) };
            }
            if (sql.includes('type IN')) {
              const m = {};
              r.filter(e => ['quote_request','whatsapp_click','email_click','phone_click'].includes(e.type))
               .forEach(e => m[e.path] = (m[e.path] || 0) + 1);
              return { results: Object.entries(m).map(([path, c]) => ({ path, c })) };
            }
            if (sql.includes('DISTINCT path')) {
              const set = new Set(r.filter(e => e.type === 'page_view').map(e => e.path));
              return { results: [...set].map(path => ({ path })) };
            }
            return { results: [] };
          },
          async run() { return {}; },
        };
      },
    };
  },
};

const env = { DB: fakeDB };

// 1) collect endpoint returns 204 and never throws
const c = await worker.fetch(new Request('https://x/a/collect', {
  method: 'POST',
  headers: { 'content-type': 'application/json', 'user-agent': 'Mozilla/5.0 (iPhone)', 'referer': 'https://google.com' },
  body: JSON.stringify({ event: 'page_view', page: '/test', v: 'v1', s: 's9', src: 'google', med: '', cmp: '' }),
}), env, {});
console.log('collect status =', c.status, '(expect 204)');

// 2) report endpoint returns valid JSON with expected shape
const r = await worker.fetch(new Request('https://x/a/report?date=' + DATE), env, {});
const json = await r.json();
console.log('report date =', json.date, '| visits =', json.visits,
            '| pageviews =', json.pageviews, '| conversions =', json.conversions,
            '| conv_rate =', json.conv_rate + '%');
console.log('top_pages =', JSON.stringify(json.top_pages));
console.log('top_sources =', JSON.stringify(json.top_sources));
console.log('insights.suggestions =', JSON.stringify(json.insights.suggestions, null, 2));
console.log('empty =', json.empty);

// 3) scheduled aggregation runs without error
const sc = await worker.scheduled({}, env, {});
console.log('scheduled =', await sc.text());

// assertions
const ok = c.status === 204 && json.date === DATE && json.visits === 5 &&
           json.conversions === 3 && json.top_pages.length === 2 &&
           json.insights.suggestions.length >= 1;
console.log(ok ? '\nALL CHECKS PASSED' : '\nCHECK FAILED');
process.exit(ok ? 0 : 1);
