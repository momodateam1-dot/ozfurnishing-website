# -*- coding: utf-8 -*-
"""Build the /trending pages from data/trending/<YYYY-MM>.json.

Run from the repository root:

    python tools/gen_trending.py

One JSON file per month. The newest file becomes the current edition at
/trending, and every edition also gets a permanent archive page at
/trending/<YYYY-MM>. Nothing is ever overwritten when the month turns: last
month's file simply stops being the newest one.

    data/trending/2026-10.json   -> trending/2026-10.html   (archive)
    data/trending/2026-11.json   -> trending.html           (current)
                                    trending/2026-11.html   (archive, canonical -> /trending)

The newest edition exists at two URLs on purpose: /trending is the live page
readers land on, /trending/<period> is where that same edition retires to when
the next month ships. The archive copy of the newest edition canonicalises to
/trending so the pair is never treated as duplicate content; once a newer
edition arrives it starts canonicalising to itself.

The header and footer are copied out of index.html and patched, so the
navigation and contact block can never drift away from the rest of the site.
Every month: add data/trending/<YYYY-MM>.json, run this file, commit, push.
"""

import io
import json
import math
import os
import re

from ld_common import organization_node

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data', 'trending')
OUT = os.path.join(ROOT, 'trending.html')
OUT_DIR = os.path.join(ROOT, 'trending')
INDEX = os.path.join(ROOT, 'index.html')
SITEMAP = os.path.join(ROOT, 'sitemap.xml')

GOLD = '#c6a76b'
GOLD_DEEP = '#a8874f'
GOLD_SOFT = '#ddc79a'
LINE = '#ded7c8'
MUTED = '#696a63'
FAINT = '#aaa99f'

PLATFORM_LABEL = {
    'tiktok': 'TikTok Shop US',
    'amazon': 'Amazon US',
    'temu': 'Temu',
    'aliexpress': 'AliExpress',
    'shein': 'Shein',
    'tiktok_eu': 'TikTok Shop UK/EU',
}


def e(text):
    """Escape for HTML text nodes and attributes."""
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def read(path):
    with io.open(path, encoding='utf-8') as fh:
        return fh.read()


# --------------------------------------------------------------------------
# editions
# --------------------------------------------------------------------------

def load_editions():
    """Load every monthly file, oldest first.

    Sorting on the period string works because YYYY-MM sorts the same way
    lexicographically and chronologically.
    """
    rows = []
    for name in sorted(os.listdir(DATA_DIR)):
        if not name.endswith('.json'):
            continue
        with io.open(os.path.join(DATA_DIR, name), encoding='utf-8') as fh:
            d = json.load(fh)
        rows.append(d)
    rows.sort(key=lambda d: d['period'])
    if not rows:
        raise SystemExit('no editions found in %s' % DATA_DIR)
    return rows


def edition_summary(d):
    """The numbers shown on the archive list."""
    core = sum(c['share'] for c in d['categories'] if c['match'] == 'core')
    return {
        'period': d['period'],
        'period_label': d['period_label'],
        'updated': d['updated'],
        'core': core,
        'items': len(d['items']),
        'platforms': len(d['platforms']),
    }


def core_share(d):
    return sum(c['share'] for c in d['categories'] if c['match'] == 'core')


# --------------------------------------------------------------------------
# chrome: header and footer lifted from index.html
# --------------------------------------------------------------------------

def build_chrome():
    src = read(INDEX)
    header = src[src.find('<header'):src.find('</header>') + 9]
    footer = src[src.find('<footer'):src.find('</footer>') + 9]

    # Navigation. index.html is itself patched by the nav rollout, so both
    # steps below have to be idempotent or a second run inserts the link twice.
    if 'href="/trending"' not in header:
        header = header.replace(
            '</nav>',
            '<a class="" href="/trending">What\'s Selling</a></nav>')
    header = re.sub(r'<a class="active"', '<a class=""', header)
    header = header.replace(
        '<a class="" href="/trending">',
        '<a class="active" href="/trending">')

    if 'href="/trending"' not in footer:
        footer = footer.replace(
            '<a href="/about">About the Company</a>',
            '<a href="/about">About the Company</a>'
            '<a href="/trending">What\'s Selling Now</a>')
    footer = footer.replace(
        '<a href="/trending">What\'s Selling in China</a>',
        '<a href="/trending">What\'s Selling Now</a>')

    return header, footer


# --------------------------------------------------------------------------
# charts
# --------------------------------------------------------------------------

def platform_bars(platforms):
    row_h = 44
    top = 26
    bar_x = 168
    bar_max = 430
    w = 680
    h = top + row_h * len(platforms) + 14
    out = ['<svg class="tr-svg" viewBox="0 0 %d %d" role="img" '
           'aria-label="Relative platform momentum this month">' % (w, h)]
    for i, p in enumerate(platforms):
        y = top + i * row_h
        bw = max(6, int(bar_max * p['heat'] / 100.0))
        t = p['heat'] / 100.0
        fill = GOLD if t >= 0.85 else (GOLD_DEEP if t >= 0.7 else GOLD_SOFT)
        out.append('<text class="tr-svg-label" x="0" y="%d">%s</text>'
                   % (y + 18, e(p['name'])))
        out.append('<text class="tr-svg-sub" x="0" y="%d">%s</text>'
                   % (y + 32, e(p['region'])))
        out.append('<rect x="%d" y="%d" width="%d" height="22" rx="3" fill="%s"/>'
                   % (bar_x, y + 4, bar_max, LINE))
        out.append('<rect x="%d" y="%d" width="%d" height="22" rx="3" fill="%s"/>'
                   % (bar_x, y + 4, bw, fill))
        out.append('<text class="tr-svg-val" x="%d" y="%d">%s</text>'
                   % (bar_x + bar_max + 14, y + 20, e(p['delta'])))
    out.append('</svg>')
    return ''.join(out)


def category_donut(categories):
    cx = cy = 170
    r = 122
    sw = 34
    circ = 2 * math.pi * r
    offset = 0.0
    out = ['<svg class="tr-svg" viewBox="0 0 340 340" role="img" '
           'aria-label="Share of demand by product category">']
    out.append('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" '
               'stroke-width="%d"/>' % (cx, cy, r, LINE, sw))
    out.append('<g transform="rotate(-90 %d %d)">' % (cx, cy))
    for c in categories:
        seg = circ * c['share'] / 100.0
        fill = {'core': GOLD, 'adjacent': GOLD_SOFT, 'off': '#c9c3b4'}[c['match']]
        out.append('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" '
                   'stroke-width="%d" stroke-dasharray="%.2f %.2f" '
                   'stroke-dashoffset="%.2f"/>'
                   % (cx, cy, r, fill, sw, seg, circ - seg, -offset))
        offset += seg
    out.append('</g>')
    core = sum(c['share'] for c in categories if c['match'] == 'core')
    out.append('<text class="tr-donut-num" x="%d" y="%d">%d%%</text>'
               % (cx, cy + 2, core))
    out.append('<text class="tr-donut-cap" x="%d" y="%d">CORE FOR OZ</text>'
               % (cx, cy + 24))
    out.append('</svg>')
    return ''.join(out)


def price_columns(bands):
    w = 680
    base = 196
    max_h = 150
    n = len(bands)
    bw = 78
    gap = (w - 40 - 40 - n * bw) / float(n - 1)
    top = max(b['share'] for b in bands)
    out = ['<svg class="tr-svg" viewBox="0 0 %d 236" role="img" '
           'aria-label="Share of listings by retail price band">' % w]
    out.append('<line x1="20" y1="%d" x2="%d" y2="%d" stroke="%s" '
               'stroke-width="1"/>' % (base + 2, w - 20, base + 2, LINE))
    for i, b in enumerate(bands):
        x = 40 + i * (bw + gap)
        bh = int(max_h * b['share'] / float(top))
        y = base - bh
        out.append('<rect x="%.1f" y="%d" width="%d" height="%d" rx="2" '
                   'fill="%s"/>' % (x, y, bw, bh, GOLD))
        out.append('<text class="tr-col-val" x="%.1f" y="%d">%d%%</text>'
                   % (x + bw / 2.0, y - 10, b['share']))
        out.append('<text class="tr-col-lab" x="%.1f" y="%d">%s</text>'
                   % (x + bw / 2.0, base + 24, e(b['label'])))
    out.append('</svg>')
    return ''.join(out)


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------

CAT_SLUG = {'home': '/sourcing/home-decor',
            'kitchen': '/sourcing/kitchen-tableware',
            'textiles': '/sourcing/bedding-textiles'}


def product_card(item, cat_name):
    delta_cls = {'rising': 'up', 'new': 'new', 'steady': 'flat'}.get(
        item['delta'], 'flat')
    delta_txt = {'rising': 'Rising', 'new': 'New entry', 'steady': 'Holding'}
    badge = ''
    if item['category'] in ('home', 'kitchen', 'textiles'):
        badge = '<span class="tr-flag">OZ core category</span>'
    slug = CAT_SLUG.get(item['category'])
    cat_html = ('<a href="%s">%s</a>' % (slug, e(cat_name)) if slug
                else e(cat_name))
    return (
        '<article class="tr-card" id="product-%d">'
        '<div class="tr-card-top">'
        '<span class="tr-rank">%02d</span>'
        '<span class="tr-plat tr-plat-%s">%s</span>'
        '<span class="tr-delta %s">%s</span>'
        '</div>'
        '<h3 class="tr-name">%s</h3>'
        '<div class="tr-cat">%s · Made in %s</div>'
        '<div class="tr-figs">'
        '<div class="tr-fig"><span>%s</span><strong>%s</strong>'
        '<em>%s</em></div>'
        '<div class="tr-fig"><span>Retail</span><strong>%s</strong>'
        '<em>Sourcing %s</em></div>'
        '</div>'
        '<div class="tr-heatrow"><span class="tr-heatlab">Momentum</span>'
        '<div class="tr-heat"><span style="width:%d%%"></span></div>'
        '<span class="tr-heatval">%d</span></div>'
        '<p class="tr-note">%s</p>'
        '%s'
        '</article>'
    ) % (item['rank'], item['rank'], e(item['platform']),
         e(PLATFORM_LABEL.get(item['platform'], item['platform'])),
         delta_cls, e(delta_txt.get(item['delta'], item['delta'])),
         e(item['name']), cat_html, e(item['origin']),
         e(item['metric_label']), e(item['metric_value']), e(item['metric_sub']),
         e(item['price']), e(item['sourcing']),
         int(item['heat']), int(item['heat']), e(item['note']), badge)


def archive_list(summaries, current_period):
    """Every edition, newest first. The current one points at /trending."""
    rows = []
    for s in reversed(summaries):
        is_now = s['period'] == current_period
        url = '/trending' if is_now else '/trending/%s' % s['period']
        rows.append(
            '<li%s><a href="%s">'
            '<span class="tr-ed-per">%s</span>'
            '<span class="tr-ed-meta">%d products · %d platforms · '
            '%d%% core</span>'
            '<span class="tr-ed-tag">%s</span>'
            '<span class="tr-ed-arr">&rarr;</span>'
            '</a></li>'
            % (' class="current"' if is_now else '', url,
               e(s['period_label']), s['items'], s['platforms'], s['core'],
               'Current' if is_now else 'Archive'))
    return (
        '<section class="section ivory">'
        '<div class="wrap">'
        '<span class="tr-eyebrow dark">Archive</span>'
        '<h2 class="tr-h2">Past editions</h2>'
        '<p class="tr-sub">Every edition stays online after the month turns, '
        'so you can read what was moving when you first looked — and see how '
        'far it has run since.</p>'
        '<ul class="tr-editions">%s</ul>'
        '</div></section>'
    ) % ''.join(rows)


def build_body(d, summaries, is_live):
    cat_name = {c['key']: c['name'] for c in d['categories']}
    core = core_share(d)

    # An archive page is a snapshot. Say so, and point back to the live page.
    if is_live:
        eyebrow = 'Monthly market signal'
        archbar = ''
        date_label, date_value = 'Next update', e(d['next_update'])
    else:
        eyebrow = 'Archive · Monthly market signal'
        archbar = (
            '<div class="tr-archbar">'
            '<span>This is the <strong>%s</strong> edition, kept exactly as it '
            'was published. The list has moved on since.</span>'
            '<a href="/trending">Read the current edition &rarr;</a>'
            '</div>'
        ) % e(d['period_label'])
        date_label, date_value = 'Published', e(d['updated'])

    hero = (
        '<section class="section tr-hero">'
        '<div class="wrap">'
        '<span class="tr-eyebrow">%s</span>'
        '<h1 class="tr-h1">What\'s Selling from China — %s</h1>'
        '%s'
        '<p class="tr-lede">Every month we read the public sales data from the '
        'marketplaces where Chinese-made goods actually move, and publish the '
        'short list worth sourcing. %d platforms, %d products, one question '
        'each: is this still worth buying into?</p>'
        '<div class="tr-metarow">'
        '<div><span>Updated</span><strong>%s</strong></div>'
        '<div><span>%s</span><strong>%s</strong></div>'
        '<div><span>Platforms read</span><strong>%d</strong></div>'
        '<div><span>Core-category share</span><strong>%d%%</strong></div>'
        '</div></div></section>'
    ) % (eyebrow, e(d['period_label']), archbar,
         len(d['platforms']), len(d['items']),
         e(d['updated']), date_label, date_value,
         len(d['platforms']), core)

    plat_rows = ''.join(
        '<li><span class="tr-legend-swatch" style="background:%s"></span>'
        '<strong>%s</strong> %s</li>'
        % (GOLD if p['heat'] >= 85 else (GOLD_DEEP if p['heat'] >= 70
                                         else GOLD_SOFT),
           e(p['name'] + ' ' + p['region']), e(p['note']))
        for p in d['platforms'])

    platform = (
        '<section class="section ivory">'
        '<div class="wrap">'
        '<span class="tr-eyebrow dark">Signal 01</span>'
        '<h2 class="tr-h2">Where the momentum is</h2>'
        '<p class="tr-sub">Relative heat by platform, normalised to 100 at the '
        'strongest marketplace. Percentages are year-on-year movement reported '
        'in public category summaries.</p>'
        '<div class="tr-chart">%s</div>'
        '<ul class="tr-legend">%s</ul>'
        '</div></section>'
    ) % (platform_bars(d['platforms']), plat_rows)

    cat_rows = ''.join(
        '<li><span class="tr-legend-swatch" style="background:%s"></span>'
        '<strong>%s</strong> <span class="tr-share">%d%%</span>'
        '<span class="tr-delta %s">%s</span></li>'
        % ({'core': GOLD, 'adjacent': GOLD_SOFT, 'off': '#c9c3b4'}[c['match']],
           e(c['name']), c['share'],
           'up' if c['delta'].startswith('+') and c['delta'] != '+0' else 'flat',
           e(c['delta'] + ' pts'))
        for c in d['categories'])

    demand = (
        '<section class="section">'
        '<div class="wrap">'
        '<span class="tr-eyebrow">Signal 02</span>'
        '<h2 class="tr-h2">What people are actually buying</h2>'
        '<div class="tr-split">'
        '<div><p class="tr-sub">Demand by category. Gold segments are the three '
        'OZ core categories — home, kitchen and home textiles — where we '
        'already hold supplier depth.</p>'
        '<div class="tr-chart donut">%s</div></div>'
        '<div><p class="tr-sub">Retail price bands across the ranked list. The '
        '$10–$50 corridor carries the majority of volume: cheap enough to be '
        'an impulse buy, expensive enough to leave room for QC and freight.</p>'
        '<div class="tr-chart">%s</div></div>'
        '</div>'
        '<ul class="tr-legend">%s</ul>'
        '</div></section>'
    ) % (category_donut(d['categories']), price_columns(d['price_bands']),
         cat_rows)

    cards = ''.join(product_card(it, cat_name.get(it['category'], ''))
                    for it in d['items'])

    ranking = (
        '<section class="section ivory">'
        '<div class="wrap">'
        '<span class="tr-eyebrow dark">Signal 03</span>'
        '<h2 class="tr-h2">The short list for %s</h2>'
        '<p class="tr-sub">Ranked on reported sales velocity, not on how good '
        'the product looks in a video. Sourcing ranges are indicative factory '
        'gate prices for a first order, before freight and duty. The momentum '
        'score is our read on how much of the curve is still ahead, not how '
        'much has already been sold.</p>'
        '<div class="tr-grid">%s</div>'
        '</div></section>'
    ) % (e(d['period_label']), cards)

    method = (
        '<section class="section">'
        '<div class="wrap">'
        '<span class="tr-eyebrow">How to read this</span>'
        '<h2 class="tr-h2">Method, and its limits</h2>'
        '<div class="prose tr-prose">'
        '<p class="note">%s</p>'
        '<p>We publish this because most sourcing advice is written after the '
        'trend has already peaked. This list is deliberately short. If a '
        'product is here it means the sales data is public and the supplier '
        'landscape around it is real — not that it will still be moving in '
        'six months.</p>'
        '<p>Two things we will not do: quote a factory price we have not '
        'checked, or recommend a product we cannot sample. Use this page as a '
        'starting conversation, not a purchase order.</p>'
        '</div>'
        '<p class="tr-sub" style="margin-top:24px">Buying into any of these? '
        'We source across <a href="/sourcing/furniture-interiors">furniture '
        '&amp; interiors</a>, <a href="/sourcing/home-decor">home decor</a>, '
        '<a href="/sourcing/bedding-textiles">bedding &amp; home textiles</a>, '
        '<a href="/sourcing/lighting">lighting</a>, '
        '<a href="/sourcing/kitchen-tableware">kitchenware &amp; tableware</a> '
        'and <a href="/sourcing/hotel-ffe">hotel FF&amp;E</a>. Our '
        '<a href="/china-furniture-sourcing">China furniture sourcing '
        'guide</a> covers the clusters and materials behind them.</p>'
        '<a class="btn gold tr-cta" href="/inquiry">'
        'Ask us to source any of these <span class="arrow">↗</span></a>'
        '</div></section>'
    ) % e(d['methodology'])

    return hero + platform + demand + ranking + method \
        + archive_list(summaries, d['period'])


def build_ld(d, url, is_live):
    items = []
    for i, it in enumerate(d['items'], 1):
        items.append({
            '@type': 'ListItem',
            'position': i,
            'item': {
                '@type': 'Product',
                'name': it['name'],
                'description': it['note'],
                'category': it['category'],
            },
        })
    crumbs = [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home',
         'item': 'https://ozfurnishing.com/'},
        {'@type': 'ListItem', 'position': 2,
         'name': "What's Selling from China",
         'item': 'https://ozfurnishing.com/trending'},
    ]
    if not is_live:
        crumbs.append({'@type': 'ListItem', 'position': 3,
                       'name': d['period_label'], 'item': url})
    return json.dumps({
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'BreadcrumbList', 'itemListElement': crumbs},
            {
                '@type': 'ItemList',
                'name': "Best-selling China-made products — %s"
                        % d['period_label'],
                'description': d['methodology'][:300],
                'numberOfItems': len(d['items']),
                'itemListElement': items,
            },
            organization_node(),
        ],
    }, ensure_ascii=False, indent=2)


def render(d, summaries, is_live, canonical_url, header, footer):
    url = 'https://ozfurnishing.com' + canonical_url
    period = d['period_label']
    if is_live:
        title = "What's Selling from China — %s | OZ" % period
        desc = ("Monthly ranking of the best-selling China-made products across "
                "TikTok Shop, Amazon, Temu and AliExpress, with sourcing price "
                "ranges and category demand data.")
    else:
        title = "What Sold from China in %s — Archive | OZ" % period
        desc = ("The %s edition of our China best-seller ranking: %d products "
                "across %d marketplaces, with the sourcing price ranges and "
                "category demand data as published at the time."
                % (period, len(d['items']), len(d['platforms'])))
    desc = e(desc)

    return u"""<!doctype html><html lang="en"><head><meta charset="utf-8">\
<meta name="viewport" content="width=device-width,initial-scale=1">\
<meta name="description" content="%(desc)s">\
<meta name="theme-color" content="#090a09">
    <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="OZ International">
    <meta property="og:title" content="%(ogtitle)s">
    <meta property="og:description" content="%(desc)s">
    <meta property="og:image" content="https://ozfurnishing.com/assets/img/product-1.jpg">
    <meta property="og:url" content="%(url)s">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="canonical" href="%(url)s">\
<title>%(title)s</title><link rel="stylesheet" href="/assets/style.css">
    <script type="application/ld+json">
%(ld)s
    </script>
</head><body><div class="topline"><div class="wrap"><span>OZ INTERNATIONAL &nbsp; / &nbsp; CHINA SOURCING &amp; TRADE</span><span class="right"><span class="accent">A DIRECT LINE TO CHINA</span> &nbsp; · &nbsp; GLOBAL BUYER SUPPORT</span></div></div>
%(header)s<main>
%(body)s
</main>
%(footer)s
        <script src="/assets/main.js" defer></script>
  </body></html>
""" % {
        'desc': desc,
        'ogtitle': e(title),
        'title': e(title),
        'url': url,
        'ld': build_ld(d, url, is_live),
        'header': header,
        'footer': footer,
        'body': build_body(d, summaries, is_live),
    }


def update_sitemap(summaries, current_period):
    """List one URL per archived edition, and only editions that are archived.

    The block is rebuilt rather than appended to, because an edition can leave
    the list: the newest one canonicalises to /trending, so listing its archive
    URL would only produce a "discovered, not indexed" entry in Search Console.
    When the month turns it becomes a normal archive with a self-canonical and
    gets listed then. Rebuilding also keeps repeat runs idempotent.
    """
    sm = read(SITEMAP)
    sm = re.sub(
        r'[ \t]*<url>\s*<loc>https://ozfurnishing\.com/trending/[^<]*</loc>'
        r'.*?</url>\n?',
        '', sm, flags=re.S)
    for s in summaries:
        if s['period'] == current_period:
            continue
        entry = ('  <url>\n    <loc>https://ozfurnishing.com/trending/%s</loc>'
                 '\n    <lastmod>%s</lastmod>\n  </url>\n'
                 % (s['period'], s['updated']))
        sm = sm.replace('</urlset>', entry + '</urlset>')
    with io.open(SITEMAP, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(sm)
    return sm.count('<loc>')


def main():
    editions = load_editions()
    summaries = [edition_summary(d) for d in editions]
    latest = editions[-1]
    header, footer = build_chrome()

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    # The live page is always the newest edition.
    page = render(latest, summaries, True, '/trending', header, footer)
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(page)
    print('wrote %-34s %6d bytes  (current: %s)'
          % ('trending.html', len(page.encode('utf-8')), latest['period']))

    # Every edition also gets a permanent archive page. The newest one
    # canonicalises to /trending; older ones canonicalise to themselves.
    for d in editions:
        is_live = d['period'] == latest['period']
        canon = '/trending' if is_live else '/trending/%s' % d['period']
        page = render(d, summaries, False, canon, header, footer)
        path = os.path.join(OUT_DIR, '%s.html' % d['period'])
        with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(page)
        print('wrote %-34s %6d bytes  (canonical: %s)'
              % ('trending/%s.html' % d['period'],
                 len(page.encode('utf-8')), canon))

    n = update_sitemap(summaries, latest['period'])
    print('sitemap: %d urls' % n)
    print('editions: %s' % ', '.join(d['period'] for d in editions))


if __name__ == '__main__':
    main()
