# -*- coding: utf-8 -*-
"""Build the /sourcing category pages from data/categories/<slug>.json.

Run from the repository root:

    python tools/gen_category.py

One JSON file per sourcing category. Every file produces a permanent page at
/sourcing/<slug>, and the generator also maintains the /sourcing index page
that lists them all:

    data/categories/furniture-interiors.json -> sourcing/furniture-interiors.html
    ...                                      -> sourcing.html (index)

Adding a category: drop in a new JSON file and re-run. Removing one: delete
the file, delete the leftover HTML, re-run (the sitemap block is rebuilt, so
the URL disappears from sitemap.xml too).

The header and footer are copied out of index.html and patched, so navigation
and contact details can never drift from the rest of the site. The sitemap
block for /sourcing is rebuilt rather than appended to, which keeps repeat
runs idempotent.
"""

import datetime
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data', 'categories')
OUT_DIR = os.path.join(ROOT, 'sourcing')
OUT_INDEX = os.path.join(ROOT, 'sourcing.html')
INDEX = os.path.join(ROOT, 'index.html')
SITEMAP = os.path.join(ROOT, 'sitemap.xml')

SITE = 'https://ozfurnishing.com'


def e(text):
    """Escape for HTML text nodes and attributes."""
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def read(path):
    with io.open(path, encoding='utf-8') as fh:
        return fh.read()


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def load_categories():
    rows = []
    if os.path.isdir(DATA_DIR):
        for name in sorted(os.listdir(DATA_DIR)):
            if not name.endswith('.json'):
                continue
            with io.open(os.path.join(DATA_DIR, name), encoding='utf-8') as fh:
                rows.append(json.load(fh))
    if not rows:
        raise SystemExit('no categories found in %s' % DATA_DIR)
    rows.sort(key=lambda d: d.get('order', 99))
    return rows


def by_slug(rows):
    return {d['slug']: d for d in rows}


# --------------------------------------------------------------------------
# chrome: header and footer lifted from index.html
# --------------------------------------------------------------------------

def build_chrome():
    src = read(INDEX)
    header = src[src.find('<header'):src.find('</header>') + 9]
    footer = src[src.find('<footer'):src.find('</footer>') + 9]

    # Category pages are not one of the six nav items, so nothing is active.
    header = re.sub(r'<a class="active"', '<a class=""', header)

    # Idempotent footer patch, same guard as gen_trending.py.
    if 'href="/sourcing"' not in footer:
        footer = footer.replace(
            '<a href="/c-sourcing">',
            '<a href="/sourcing">Sourcing Categories</a>'
            '<a href="/c-sourcing">')
    return header, footer


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------

def hero(d):
    badges = ''.join('<span class="mini-badge">%s</span>' % e(b)
                     for b in d['badges'])
    return (
        '<section class="page-hero"><div class="wrap">'
        '<div class="eyebrow">%s</div>'
        '<h1>%s</h1>'
        '<p>%s</p>'
        '<div class="actions">'
        '<a class="btn gold" href="/inquiry?category=%s">Request a Quote '
        '<span class="arrow">&#8599;</span></a>'
        '<a class="btn light" href="#what-we-source">See What We Source '
        '<span class="arrow">&#8595;</span></a>'
        '</div>'
        '<div class="badge-row">%s</div>'
        '<div class="page-kicker">%02d</div>'
        '</div></section>'
    ) % (e(d['eyebrow']), d['h1'], e(d['lead']),
         d['query_category'].replace(' ', '%20').replace('&', '%26'),
         badges, d.get('order', 1))


def subcategories(d):
    cards = ''.join(
        '<div class="service-card"><div class="n">%s</div>'
        '<h3>%s</h3><p>%s</p></div>'
        % (e(s['n']), e(s['name']), e(s['desc']))
        for s in d['subcategories'])
    return (
        '<section class="section" id="what-we-source"><div class="wrap">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">What we source in this category</div>'
        '<h2>%s<br><em>%s</em></h2>'
        '</div><p>%s</p></div>'
        '<div class="cards3">%s</div>'
        '</div></section>'
    ) % (e(d['sub_h2_a']), e(d['sub_h2_em']), e(d['sub_intro']), cards)


def materials(d):
    rows = ''.join(
        '<div class="capability-row"><div class="num">%s</div>'
        '<div><h3>%s</h3><p>%s</p></div>'
        '<div class="plus">&#8599;</div></div>'
        % (e(m['n']), e(m['name']), e(m['note']))
        for m in d['materials'])
    return (
        '<section class="section panel"><div class="wrap">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">Materials and construction</div>'
        '<h2>%s<br><em>%s</em></h2>'
        '</div><p>%s</p></div>'
        '<div class="capability-list">%s</div>'
        '</div></section>'
    ) % (e(d['mat_h2_a']), e(d['mat_h2_em']), e(d['mat_intro']), rows)


def buying_notes(d):
    rows = ''.join(
        '<div class="buy-price-row"><b>%s</b><span>%s</span>'
        '<em>%s</em></div>'
        % (e(b['label']), e(b['note']), e(b['tag']))
        for b in d['buying'])
    return (
        '<section class="section ivory"><div class="wrap">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">What to expect when buying</div>'
        '<h2>%s<br><em>%s</em></h2>'
        '</div><p>%s</p></div>'
        '<div class="buy-price">%s</div>'
        '<p class="buy-lead" style="margin-top:26px">%s</p>'
        '</div></section>'
    ) % (e(d['buy_h2_a']), e(d['buy_h2_em']), e(d['buy_intro']), rows,
         e(d['buy_footnote']))


def checklist(d):
    items = ''.join('<div class="check">%s</div>' % e(c)
                    for c in d['checklist'])
    return (
        '<section class="section"><div class="wrap">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">Before you send the enquiry</div>'
        '<h2>%s<br><em>%s</em></h2>'
        '</div><p>%s</p></div>'
        '<div class="check-grid">%s</div>'
        '<p class="buy-lead" style="margin-top:28px">%s</p>'
        '</div></section>'
    ) % (e(d['check_h2_a']), e(d['check_h2_em']), e(d['check_intro']), items,
         e(d['check_footnote']))


def compare(d):
    diy = ''.join('<li>%s</li>' % e(x) for x in d['compare']['diy'])
    oz = ''.join('<li>%s</li>' % e(x) for x in d['compare']['oz'])
    return (
        '<section class="section ivory"><div class="wrap">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">%s</div>'
        '<h2>%s<br><em>%s</em></h2>'
        '</div><p>%s</p></div>'
        '<div class="buy-compare">'
        '<div class="buy-compare-col"><span class="tag">On your own</span>'
        '<h3>%s</h3><ul>%s</ul></div>'
        '<div class="buy-compare-col gold"><span class="tag">Through OZ</span>'
        '<h3>%s</h3><ul>%s</ul></div>'
        '</div></div></section>'
    ) % (e(d['compare']['eyebrow']), e(d['compare']['h2_a']),
         e(d['compare']['h2_em']), e(d['compare']['intro']),
         e(d['compare']['diy_title']), diy, e(d['compare']['oz_title']), oz)


def faq(d):
    rows = ''.join(
        '<details><summary>%s</summary><p>%s</p></details>'
        % (e(q['q']), e(q['a'])) for q in d['faq'])
    return (
        '<section class="section"><div class="wrap">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">Common questions</div>'
        '<h2>%s<br><em>%s</em></h2>'
        '</div><p>%s</p></div>'
        '<div class="faq-list">%s</div>'
        '</div></section>'
    ) % (e(d['faq_h2_a']), e(d['faq_h2_em']), e(d['faq_intro']), rows)


def related(d, lookup):
    cards = []
    for slug in d.get('related', []):
        other = lookup.get(slug)
        if not other:
            continue
        cards.append(
            '<a class="service-card" href="/sourcing/%s">'
            '<div class="n">%02d</div><h3>%s</h3><p>%s</p>'
            '<span class="text-link">View Category <span>&#8599;</span></span>'
            '</a>' % (other['slug'], other.get('order', 1),
                      e(other['name']), e(other['card_desc'])))
    return (
        '<section class="section ivory"><div class="wrap">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">Other categories we buy</div>'
        '<h2>One category is<br><em>rarely the whole order.</em></h2>'
        '</div><p>Most buyers mix categories in the same shipment. These sit '
        'next to %s most often.</p></div>'
        '<div class="cards3">%s</div>'
        '</div></section>'
    ) % (e(d['name']), ''.join(cards))


def cta(d):
    return (
        '<section class="cta-band"><div class="wrap"><div>'
        '<div class="eyebrow">Start with the requirement</div>'
        '<h2>Have a %s brief?<br><em>Let’s price it.</em></h2>'
        '<p>%s</p>'
        '</div><a class="btn gold" href="/inquiry?category=%s">Request a %s '
        'Quote <span class="arrow">&#8599;</span></a></div></section>'
    ) % (e(d['short_name']), e(d['cta_note']),
         d['query_category'].replace(' ', '%20').replace('&', '%26'),
         e(d['short_name']))


def build_body(d, lookup):
    return (hero(d) + subcategories(d) + materials(d) + buying_notes(d)
            + checklist(d) + compare(d) + faq(d) + related(d, lookup)
            + cta(d))


def build_ld(d, url):
    return json.dumps({
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'BreadcrumbList',
                'itemListElement': [
                    {'@type': 'ListItem', 'position': 1, 'name': 'Home',
                     'item': SITE + '/'},
                    {'@type': 'ListItem', 'position': 2,
                     'name': 'Sourcing Categories',
                     'item': SITE + '/sourcing'},
                    {'@type': 'ListItem', 'position': 3, 'name': d['name'],
                     'item': url},
                ],
            },
            {
                '@type': 'Service',
                'name': d['ld_service_name'],
                'serviceType': d['ld_service_type'],
                'description': d['desc'],
                'provider': {'@id': SITE + '/#organization'},
                'areaServed': ['AU', 'US', 'GB', 'SG', 'AE', 'DE', 'FR'],
                'url': url,
                'hasOfferCatalog': {
                    '@type': 'OfferCatalog',
                    'name': d['name'] + ' sub-categories',
                    'itemListElement': [
                        {'@type': 'Offer',
                         'itemOffered': {'@type': 'Service',
                                         'name': s['name']}}
                        for s in d['subcategories']
                    ],
                },
            },
            {
                '@type': 'FAQPage',
                'mainEntity': [
                    {'@type': 'Question', 'name': q['q'],
                     'acceptedAnswer': {'@type': 'Answer', 'text': q['a']}}
                    for q in d['faq']
                ],
            },
        ],
    }, ensure_ascii=False, indent=2)


def render(d, lookup, header, footer):
    url = '%s/sourcing/%s' % (SITE, d['slug'])
    title = d['title']
    desc = e(d['desc'])
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
%(header)s<div class="nav-overlay" id="navOverlay" aria-hidden="true"></div><main>
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
        'ld': build_ld(d, url),
        'header': header,
        'footer': footer,
        'body': build_body(d, lookup),
    }


# --------------------------------------------------------------------------
# index page
# --------------------------------------------------------------------------

def render_index(cats, header, footer):
    cards = ''.join(
        '<a class="service-card" href="/sourcing/%s">'
        '<div class="n">%02d</div><h3>%s</h3>'
        '<span class="product-sub" style="display:block;font-size:10px;'
        'letter-spacing:.12em;text-transform:uppercase;color:var(--gold);'
        'margin:-6px 0 12px">%s</span>'
        '<p>%s</p>'
        '<span class="text-link">View Category <span>&#8599;</span></span>'
        '</a>' % (d['slug'], d.get('order', 1), e(d['name']),
                  e(d['sub']), e(d['card_desc']))
        for d in cats)
    body = (
        '<section class="page-hero"><div class="wrap">'
        '<div class="eyebrow">Sourcing categories · Furniture, home &amp; '
        'outdoor</div>'
        '<h1>What We Source from China<br><em>Six Categories, One Buying '
        'Desk</em></h1>'
        '<p>Furniture, home and outdoor products are where our supplier '
        'network is deepest. Pick a category to see what we buy in it, which '
        'materials and finishes are realistic, and what the first order '
        'usually looks like.</p>'
        '<div class="actions">'
        '<a class="btn gold" href="/inquiry">Start an Inquiry '
        '<span class="arrow">&#8599;</span></a>'
        '<a class="btn light" href="/trending">See What’s Selling '
        '<span class="arrow">&#8599;</span></a>'
        '</div>'
        '<div class="badge-row"><span class="mini-badge">Factory Direct</span>'
        '<span class="mini-badge">Sample Before Bulk</span>'
        '<span class="mini-badge">Consolidated Shipping</span></div>'
        '<div class="page-kicker">06</div>'
        '</div></section>'
        '<section class="section"><div class="wrap">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">The six categories</div>'
        '<h2>Start where<br><em>your brief fits.</em></h2>'
        '</div><p>Every category page covers the same ground: what we buy, '
        'what it is made of, what the first order realistically costs and '
        'how long it takes.</p></div>'
        '<div class="cards3">%s</div>'
        '</div></section>'
        '<section class="section ivory"><div class="wrap">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">Two ways to buy</div>'
        '<h2>Same categories.<br><em>Two buying routes.</em></h2>'
        '</div><p>The category tells us what to buy. The route tells us how '
        'the order is handled.</p></div>'
        '<div class="buy-compare">'
        '<div class="buy-compare-col"><span class="tag">Personal shopping</span>'
        '<h3>A few items, bought for you</h3><ul>'
        '<li>You send a link, photo or screenshot from a Chinese platform</li>'
        '<li>We buy it, inspect it and photograph it in our warehouse</li>'
        '<li>Everything ships together as one consolidated parcel</li>'
        '<li>Best for households, small sellers and one-room projects</li>'
        '</ul><a class="text-link" href="/c-sourcing">See the personal '
        'shopping flow <span>&#8599;</span></a></div>'
        '<div class="buy-compare-col gold"><span class="tag">B2B buying '
        'agent</span>'
        '<h3>A list, bought to specification</h3><ul>'
        '<li>You send a BOQ, drawings, spec sheet or supplier list</li>'
        '<li>We shortlist factories, compare quotes and arrange samples</li>'
        '<li>Pre-shipment inspection before the balance is released</li>'
        '<li>Best for hotels, retailers, wholesalers and project buyers</li>'
        '</ul><a class="text-link" href="/b2b-procurement">See the B2B buying '
        'flow <span>&#8599;</span></a></div>'
        '</div></div></section>'
        '<section class="cta-band"><div class="wrap"><div>'
        '<div class="eyebrow">Not sure which category?</div>'
        '<h2>Send what you have.<br><em>We’ll tell you where it fits.</em></h2>'
        '<p>A photo, a link or a half-finished list is enough for us to say '
        'whether this is a personal shopping order or a B2B brief.</p>'
        '</div><a class="btn gold" href="/inquiry">Make an Inquiry '
        '<span class="arrow">&#8599;</span></a></div></section>'
    ) % cards
    url = SITE + '/sourcing'
    ld = json.dumps({
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'BreadcrumbList', 'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home',
                 'item': SITE + '/'},
                {'@type': 'ListItem', 'position': 2,
                 'name': 'Sourcing Categories', 'item': url},
            ]},
            {'@type': 'ItemList', 'name': 'Sourcing categories',
             'numberOfItems': len(cats),
             'itemListElement': [
                 {'@type': 'ListItem', 'position': i,
                  'item': {'@type': 'Service', 'name': d['name'],
                           'url': '%s/sourcing/%s' % (SITE, d['slug'])}}
                 for i, d in enumerate(cats, 1)]},
        ],
    }, ensure_ascii=False, indent=2)
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
%(header)s<div class="nav-overlay" id="navOverlay" aria-hidden="true"></div><main>
%(body)s
</main>
%(footer)s
        <script src="/assets/main.js" defer></script>
  </body></html>
""" % {
        'desc': e('Six sourcing categories we buy from China: furniture and '
                  'interiors, home decor, outdoor, lighting, kitchenware and '
                  'hotel FF&E. Materials, MOQ and lead times.'),
        'ogtitle': e('What We Source from China | Six Categories | OZ'),
        'title': e('What We Source from China | Six Categories | OZ'),
        'url': url,
        'ld': ld,
        'header': header,
        'footer': footer,
        'body': body,
    }


# --------------------------------------------------------------------------
# sitemap
# --------------------------------------------------------------------------

def update_sitemap(cats, today):
    """Rebuild every /sourcing entry instead of appending.

    Appending would leave stale URLs behind when a category is renamed or
    dropped, and would duplicate them on every re-run.
    """
    sm = read(SITEMAP)
    sm = re.sub(
        r'[ \t]*<url>\s*<loc>https://ozfurnishing\.com/sourcing[^<]*</loc>'
        r'.*?</url>\n?',
        '', sm, flags=re.S)
    entries = ('  <url>\n    <loc>%s/sourcing</loc>\n'
               '    <lastmod>%s</lastmod>\n  </url>\n' % (SITE, today))
    for d in cats:
        entries += ('  <url>\n    <loc>%s/sourcing/%s</loc>\n'
                    '    <lastmod>%s</lastmod>\n  </url>\n'
                    % (SITE, d['slug'], today))
    sm = sm.replace('</urlset>', entries + '</urlset>')
    with io.open(SITEMAP, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(sm)
    return sm.count('<loc>')


def main():
    cats = load_categories()
    lookup = by_slug(cats)
    header, footer = build_chrome()
    today = datetime.date.today().isoformat()

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    page = render_index(cats, header, footer)
    with io.open(OUT_INDEX, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(page)
    print('wrote %-38s %6d bytes' % ('sourcing.html',
                                     len(page.encode('utf-8'))))

    for d in cats:
        page = render(d, lookup, header, footer)
        path = os.path.join(OUT_DIR, '%s.html' % d['slug'])
        with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(page)
        print('wrote %-38s %6d bytes' % ('sourcing/%s.html' % d['slug'],
                                         len(page.encode('utf-8'))))

    n = update_sitemap(cats, today)
    print('sitemap: %d urls' % n)
    print('categories: %s' % ', '.join(d['slug'] for d in cats))


if __name__ == '__main__':
    main()
