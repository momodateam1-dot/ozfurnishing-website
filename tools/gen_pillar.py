#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render the China furniture sourcing pillar page.

Same contract as gen_category.py / gen_trending.py:
  - chrome (header + footer) is lifted out of index.html and patched
  - the /china-furniture-sourcing sitemap entry is rebuilt, never appended
  - FAQ answers are emitted once and reused verbatim by the visible markup
    and by the FAQPage structured data

The page is the parent node for the six /sourcing/<slug> category pages, so it
links down to every one of them and they link back up to it.
"""

from __future__ import print_function

import datetime
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://ozfurnishing.com'
SLUG = 'china-furniture-sourcing'
URL = '%s/%s' % (SITE, SLUG)
OUT = os.path.join(ROOT, '%s.html' % SLUG)
SITEMAP = os.path.join(ROOT, 'sitemap.xml')

TITLE = 'China Furniture Sourcing: Factories, Costs & Compliance | OZ'
DESC = ('Where Chinese furniture is made, what each material costs and where it '
        'fails, container maths, and US/EU/UK compliance. From the buying desk.')

CATS = [
    ('/sourcing/furniture-interiors', 'Furniture &amp; interiors',
     'Sofas, casegoods, storage, bedroom sets and contract seating'),
    ('/sourcing/home-decor', 'Home decor',
     'Wall decor, storage, soft furnishings and decorative accessories'),
    ('/sourcing/bedding-textiles', 'Bedding &amp; home textiles',
     'Sheets, duvets, pillows, towels and blankets'),
    ('/sourcing/lighting', 'Lighting',
     'Pendants, table and floor lamps, architectural and commercial'),
    ('/sourcing/kitchen-tableware', 'Kitchenware &amp; tableware',
     'Dinnerware, glassware, cookware, cutlery and kitchen tools'),
    ('/sourcing/hotel-ffe', 'Hotel FF&amp;E',
     'Guest rooms, public areas, F&amp;B and resort fit-outs'),
]

# --------------------------------------------------------------------------
# content
# --------------------------------------------------------------------------

CLUSTERS = [
    ('Foshan, Guangdong<br><span class="micro">Shunde · Lecong · Longjiang</span>',
     'Casegoods, upholstery, beds, mattresses, custom fixed furniture',
     'Shenzhen / Guangzhou<br><span class="micro">~120 km</span>',
     'Hotels, apartments, mixed FF&amp;E packages'),
    ('Nankang, Ganzhou<br><span class="micro">Jiangxi</span>',
     'Solid wood: beds, tables, chairs, wardrobes',
     'Ganzhou inland port<br><span class="micro">onward to Shenzhen</span>',
     'Resorts, schools, restaurants, solid-timber specs'),
    ('Dongguan<br><span class="micro">Guangdong</span>',
     'High-end casegoods, office systems, contract seating',
     'Shenzhen<br><span class="micro">~60 km</span>',
     'Offices, branded hotels, strict-spec FF&amp;E'),
    ('Anji<br><span class="micro">Zhejiang</span>',
     'Office chairs, task and conference seating',
     'Shanghai<br><span class="micro">~200 km</span>',
     'Office fit-outs, schools, call centres'),
    ('Bazhou &amp; Shengfang<br><span class="micro">Hebei</span>',
     'Metal, glass, MDF, banquet and event seating',
     'Tianjin<br><span class="micro">~100 km</span>',
     'Budget programmes, banquet and event furniture'),
    ('Chengdu / Chongzhou<br><span class="micro">Sichuan</span>',
     'Panel furniture, wardrobes, bedroom sets',
     'Inland<br><span class="micro">China–Europe rail</span>',
     'Western China programmes, rail destinations'),
]

MATERIALS = [
    ('Solid wood',
     'Species, moisture content, kiln-drying record, grade',
     'Colour drift across one container, and timber that moves after it '
     'reaches a drier climate. Rubberwood, ash, oak and pine are the '
     'volume species; anything rarer needs the origin declared.'),
    ('Engineered board &amp; veneer',
     'Board grade, formaldehyde class, veneer thickness, edge banding',
     'The single most common place to quietly cut cost. Swelling at unsealed '
     'edges, delamination, and veneer that is too thin to sand back.'),
    ('Metal',
     'Gauge and wall thickness, weld finish, coating system',
     'Thin-wall tube dents in transit, and powder coat flakes first at the '
     'welds. Ask for wall thickness in millimetres, not a photograph.'),
    ('Rattan &amp; cane',
     'Natural or PE, weave density, frame material, grade consistency',
     'Natural material needs consistent grading or the colour drifts piece '
     'to piece — the defect that shows up in one container, not one sample.'),
    ('Upholstery',
     'Foam density and ILD, fabric weight in gsm, rub count, leather cut',
     'Foam density is the spec most often downgraded: 25D becomes 18D and '
     'the sofa feels different after ninety days. Put density, ILD and gsm '
     'in the spec sheet, not in an email.'),
    ('Stone &amp; glass',
     'Thickness, edge finish, tempering, sealing',
     'Untempered glass and unsealed stone top the damage list. Both are '
     'cheap to specify correctly and expensive to replace after arrival.'),
]

COSTS = [
    ('Material',
     'Board, timber, metal, fabric, leather, foam, stone',
     'The largest single line. Moves with commodity markets, so a quote '
     'held open for weeks is a quote that will be renegotiated.'),
    ('Labour &amp; finishing',
     'Cutting, welding, sanding, upholstery, spray, veneer matching',
     'Where most of the gap between two quotes actually sits. Hand-matched '
     'veneer and multi-stage finishing are the difference between them.'),
    ('Tooling &amp; samples',
     'Jigs, moulds, prototype, corrected pre-production sample',
     'One-off cost, usually credited back once the bulk order is placed. '
     'Budget for two sample rounds, not one.'),
    ('Packaging',
     'Cartons, corner protection, crates, flat-pack engineering',
     'Under-invested by default. Damage claims on poorly packed furniture '
     'commonly run 3–8% of shipment value.'),
    ('Consolidation &amp; inland trucking',
     'Factory to warehouse to port',
     'Falls sharply when your factories share a cluster — which is the '
     'practical reason not to spread an order across four provinces.'),
    ('Freight &amp; duty',
     'Charged on volume, not on value',
     'A badly packed container can cost more per unit than a well-packed '
     'one, which is why packing is a cost line and not an afterthought.'),
]

COMPLIANCE = [
    ('United States', 'Composite wood',
     'CARB Phase 2 and TSCA Title VI formaldehyde limits',
     'A third-party test report from SGS, BV or Intertek on the board '
     'supplier — not a factory certificate.'),
    ('United States', 'Upholstered goods',
     'California TB 117-2013 flammability',
     'Foam density, ILD and fabric gsm written into the spec sheet.'),
    ('United States', 'Office seating',
     'ANSI/BIFMA X5.1',
     'Cycle-test results on the gas lift and tilt mechanism, which is where '
     'low-cost chairs fail first.'),
    ('United States', 'Mattresses',
     '16 CFR 1632 and 1633',
     'Ignition resistance plus the label. Missing label requirements can get '
     'goods refused even when the product itself passes.'),
    ('European Union', 'Timber and wood-based furniture',
     'EU Deforestation Regulation',
     'Geolocation-based due diligence on the timber. The compliance date has '
     'been deferred more than once — confirm the current one for your '
     'company size before you plan a launch.'),
    ('European Union', 'All consumer products',
     'General Product Safety Regulation',
     'Traceability records and an EU-based responsible person.'),
    ('United Kingdom', 'Domestic upholstered furniture',
     'Furniture and Furnishings (Fire) (Safety) Regulations',
     'UKFR test reports and the correct permanent labels.'),
    ('All markets', 'Wood sourcing claims',
     'FSC chain of custody',
     'A certificate number you can look up, not a logo on a catalogue.'),
]

ROUTES = [
    ('Factory direct',
     'You hold the relationship, the verification and the risk',
     ['Best unit price on one high-volume item',
      'You check the licence, capacity and export rights yourself',
      'You arrange inspection, consolidation and the document set',
      'Works well when you already know the factory and reorder the same SKU']),
    ('Trading company',
     'One counterparty, less visibility',
     ['Bundles several SKUs into one container and handles paperwork',
      'Often cheaper to deal with than five separate factories',
      'You may not learn which factory actually made your goods',
      'Harder to hold quality accountable when something goes wrong']),
    ('Buying agent — OZ',
     'You keep the factory relationship, we carry the work',
     ['Three or more factories quoted on identical terms',
      'Licences, capacity and export rights checked before quoting',
      'Balance released only after a photo-backed AQL inspection',
      'Everything consolidated into one container and one document set']),
]

CHECKS = [
    'Drawings or dimensioned photos with tolerances',
    'Material and finish spec, written down',
    'Quantity per SKU and total target volume',
    'Destination port and delivery window',
    'Compliance list for your market',
    'Sample budget for two rounds',
    'Packing requirement: flat-pack or assembled',
    'Inspection standard you will accept (AQL level)',
]

FAQ = [
    ('What is a realistic MOQ for custom furniture from China?',
     'Minimums are set by the factory, not by us. Stocked items can often '
     'ship from a single carton. Custom upholstery usually starts at one '
     '20GP container or five to ten pieces per colour, because the cutting '
     'and fabric setup costs the same whether five or fifty are made. Solid '
     'wood runs higher, often twenty to fifty pieces. We confirm the real '
     'figure with each factory before you commit.'),
    ('How long does a first furniture order take end to end?',
     'Production runs 30–45 days when the factory can draw components from '
     'inside its own cluster, and 45–60 days when the specification needs '
     'custom veneer or imported timber. Add 7–20 days for sampling before '
     'that, and 3–7 days for consolidation, loading and export. Sea transit '
     'then depends on the lane: roughly 15–25 days to the US West Coast and '
     '25–40 days to northern Europe.'),
    ('Can I mix furniture from several factories in one container?',
     'Yes, and for most project orders it is the only way the maths works. '
     'A 40ft high-cube holds about 65–68 m³, and a packed guest-room FF&E '
     'set runs 3–5 m³, so one container typically carries output from three '
     'or four factories. The catch is distance: factories far apart add a '
     'trucking leg and a separate inspection each. Consolidation is cheap '
     'inside one cluster and expensive across provinces.'),
    ('Should I buy flat-pack or assembled?',
     'Assembled furniture is safer to receive and roughly doubles the volume '
     'you pay to ship. Flat-pack halves the freight but moves the risk to '
     'the last mile, so it needs ISTA-tested packaging and clear assembly '
     'instructions. The usual split: assembled for hotel and project '
     'handover, flat-pack for e-commerce and anything a customer assembles '
     'at home.'),
    ('Which Incoterm should a first order use?',
     'FOB is the sensible default for container orders — we deliver to the '
     'port and load the vessel, and you control the ocean leg with your own '
     'forwarder. EXW looks cheaper but leaves you managing inland trucking '
     'and export declaration from abroad. CIF and DDP make sense once you '
     'want fewer moving parts and are happy with a longer quoting cycle.'),
    ('How do you check that a factory is legitimate?',
     'We check the business licence and its registered scope, confirm export '
     'rights, review the certifications your market needs, and visit or '
     'video-audit the production line. We report what we found including the '
     'weaknesses, because a factory that is excellent at upholstery is often '
     'quietly subcontracting your office chairs to somebody else.'),
    ('Do I need my own inspector, or is yours enough?',
     'Ours is enough for most orders. We run a mid-production check and a '
     'pre-shipment inspection against AQL 2.5, with AQL 4.0 accepted on some '
     'categories and tighter levels where your market requires it, and we '
     'send the photo report before you release the balance. If you have your '
     'own inspector we will coordinate with them rather than replace them.'),
    ('Which certifications do I need for the US and the EU?',
     'For the US: composite wood must meet CARB Phase 2 and TSCA Title VI, '
     'upholstery sold in California must meet TB 117-2013, office seating is '
     'usually specified to ANSI/BIFMA X5.1, and mattresses fall under 16 CFR '
     '1632 and 1633. For the EU: the Deforestation Regulation requires '
     'geolocation due diligence on timber, and the General Product Safety '
     'Regulation requires traceability and an EU-based responsible person. '
     'Build the checklist per SKU and get test reports before production — '
     'retrofitting compliance onto a finished container is not possible.'),
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def build_chrome():
    src = io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    header = src[src.find('<header'):src.find('</header>') + 9]
    footer = src[src.find('<footer'):src.find('</footer>') + 9]
    header = re.sub(r'<a class="active"', '<a class=""', header)
    # Idempotent footer patch, same guard as the other generators.
    if 'href="/sourcing"' not in footer:
        footer = footer.replace(
            '<div class="footer-links"><a href="/c-sourcing">',
            '<div class="footer-links"><a href="/sourcing">'
            'Sourcing Categories</a><a href="/c-sourcing">')
    return header, footer


def rows(blocks, tmpl):
    return ''.join(tmpl % b for b in blocks)


def build_body():
    cat_links = ', '.join(
        '<a href="%s">%s</a>' % (h, t) for h, t, _n in CATS[:-1])
    cat_links += ' and <a href="%s">%s</a>' % CATS[-1][:2]

    p = []
    a = p.append

    # ---- hero -----------------------------------------------------------
    a('<section class="page-hero"><div class="wrap">'
      '<div class="eyebrow">Pillar guide · Clusters, materials, costs, '
      'compliance</div>'
      '<h1>China Furniture Sourcing<br><em>Factories, Materials, Costs</em>'
      '</h1>'
      '<p>Furniture is the hardest category to buy from China and the easiest '
      'to get wrong, because volume, weight and finish all move against you '
      'at the same time. This guide covers where each type of furniture is '
      'actually made, what each material costs and where it fails, the '
      'container maths that decides your landed price, and the compliance '
      'stack for the US, EU and UK. It is written from the buying desk, not '
      'from a supplier directory.</p>'
      '<div class="actions">'
      '<a class="btn gold" href="/inquiry?type=product">Send a Furniture '
      'Brief <span class="arrow">↗</span></a>'
      '<a class="btn light" href="#clusters">Start with the clusters '
      '<span class="arrow">↓</span></a>'
      '</div>'
      '<div class="badge-row"><span class="mini-badge">6 Manufacturing '
      'Clusters</span><span class="mini-badge">Material Failure Points</span>'
      '<span class="mini-badge">Compliance by Market</span></div>'
      '<div class="page-kicker">P1</div></div></section>')

    # ---- why China ------------------------------------------------------
    a('<section class="section"><div class="wrap"><div class="section-header">'
      '<div><div class="eyebrow">The short answer</div>'
      '<h2>Why furniture, and why China<br><em>still wins on the maths.</em>'
      '</h2></div>'
      '<p>Not because labour is cheap — that gap has been closing for a '
      'decade — but because the supply chain is dense.</p></div>'
      '<div class="prose"><p>In Foshan, hardware, foam, fabric, glass and '
      'stone tops are bought inside roughly a 50 km radius, which is what '
      'keeps a production cycle at 30–45 days instead of stretching while a '
      'factory waits on parts. It also means a well-planned day in Shunde or '
      'Nankang covers five or six factory audits; the same shortlist spread '
      'across provinces would take a week of travel.</p>'
      '<p>Density is also what makes mixed containers work. A 40ft high-cube '
      'holds about 65–68 m³ and a packed guest-room set runs 3–5 m³, so one '
      'container usually carries goods from three or four factories — but '
      'only when those factories are close enough to truck to one loading '
      'point cheaply. That single constraint shapes every sourcing decision '
      'below.</p>'
      '<p>The trade-off is that density hides variation. Two workshops on the '
      'same street can differ enormously in finishing quality, and the gap '
      'does not show up in a quotation. It shows up in a container, which is '
      'why inspection before the balance payment matters more here than in '
      'almost any other category.</p></div></div></section>')

    # ---- clusters -------------------------------------------------------
    a('<section class="section panel" id="clusters"><div class="wrap">'
      '<div class="section-header"><div>'
      '<div class="eyebrow">Where it is made</div>'
      '<h2>Six clusters.<br><em>Each makes something different.</em></h2>'
      '</div><p>A factory that is excellent at upholstery will still accept '
      'your office chair order and subcontract it. Start from the cluster '
      'that makes your product, not from whoever replied fastest.</p></div>'
      '<div class="buy-price pillar-cols-4">'
      '<div class="buy-price-row"><b>Cluster</b><b>Core products</b>'
      '<b>Nearest port</b><b>Best fit</b></div>')
    a(rows(CLUSTERS,
           '<div class="buy-price-row"><b>%s</b><span>%s</span><em>%s</em>'
           '<span>%s</span></div>'))
    a('</div>'
      '<p class="buy-lead" style="margin-top:26px">The working rule is one '
      'primary cluster plus at most one satellite. Add a second cluster when '
      'a category is worth a container of its own, or when the primary '
      'cluster genuinely does not make it well — solid wood volume points to '
      'Nankang, task seating volume points to Anji. Spreading a mid-size '
      'order across four regions because each line looked marginally cheaper '
      'adds an inspection trip, a trucking leg and a coordination failure '
      'point per region, and on a two or three container project those costs '
      'eat whatever the line items saved.</p></div></section>')

    # ---- materials ------------------------------------------------------
    a('<section class="section"><div class="wrap"><div class="section-header">'
      '<div><div class="eyebrow">Materials</div>'
      '<h2>Six material families.<br><em>And how each one fails.</em></h2>'
      '</div><p>Every line below is a specification that has to be written '
      'down before production. If it is only in an email, it is not in the '
      'order.</p></div><div class="cards3">')
    a(rows([(n, s, f) for n, s, f in MATERIALS],
           '<div class="service-card"><h3>%s</h3>'
           '<p><strong style="color:var(--gold)">Specify</strong> · %s</p>'
           '<p>%s</p></div>'))
    a('</div></div></section>')

    # ---- costs ----------------------------------------------------------
    a('<section class="section ivory"><div class="wrap">'
      '<div class="section-header"><div>'
      '<div class="eyebrow">Cost structure</div>'
      '<h2>Six lines.<br><em>Only one is the unit price.</em></h2></div>'
      '<p>Comparing two quotations on unit price alone is the most common '
      'and most expensive mistake in this category.</p></div>'
      '<div class="buy-price">')
    a(rows(COSTS,
           '<div class="buy-price-row"><b>%s</b><span>%s</span>'
           '<em>%s</em></div>'))
    a('</div>'
      '<p class="buy-lead" style="margin-top:26px">A worked example that gets '
      'cited across the industry: a mid-range fabric sofa, 50 units, full '
      'container to the US West Coast. Bought direct, the unit price is '
      'around $180 FOB with the container filled to roughly 48 m³, which '
      'puts freight and surcharges near $88 per unit. Managed for packing and '
      'consolidation, the same sofa lands at about $166 with 65.5 m³ filled '
      'and freight near $58 per unit. The unit price moved 8%; the landed '
      'cost moved far more, and almost all of it came from volume.</p>'
      '</div></section>')

    # ---- moq / samples / lead time -------------------------------------
    a('<section class="section"><div class="wrap"><div class="section-header">'
      '<div><div class="eyebrow">Order mechanics</div>'
      '<h2>MOQ, samples<br><em>and realistic lead times.</em></h2></div>'
      '<p>These three numbers decide whether a project is viable long before '
      'price does.</p></div><div class="cards3">'
      '<div class="service-card"><div class="n">01</div><h3>Minimum order '
      'quantity</h3><p>Set by the factory, not by us. Stocked items can ship '
      'from one carton. Custom upholstery usually starts at one 20GP or five '
      'to ten pieces per colour. Solid wood typically runs twenty to fifty '
      'pieces. We confirm the real figure with each factory before you '
      'commit.</p></div>'
      '<div class="service-card"><div class="n">02</div><h3>Sampling</h3>'
      '<p>A real upholstered sofa prototype runs $300–900 and takes 15–25 '
      'days. Chairs and flat-pack pieces are $80–200. Budget two rounds: a '
      'prototype and a corrected pre-production sample. Keep a sealed '
      'approved sample as the reference production must match.</p></div>'
      '<div class="service-card"><div class="n">03</div><h3>Lead time</h3>'
      '<p>30–45 days when components come from inside the cluster, 45–60 '
      'days when the spec needs custom veneer or imported timber. Add 7–20 '
      'days for sampling before that, and 3–7 days for consolidation, '
      'loading and export.</p></div></div></div></section>')

    # ---- packaging ------------------------------------------------------
    a('<section class="section panel"><div class="wrap">'
      '<div class="section-header"><div>'
      '<div class="eyebrow">Packing and volume</div>'
      '<h2>Container maths.<br><em>Where margin actually hides.</em></h2>'
      '</div><p>Freight is charged on volume. Packing is therefore a cost '
      'line, not an afterthought.</p></div>'
      '<div class="duo-grid">'
      '<div class="duo-card"><span class="tag">The numbers</span>'
      '<h3>What fits</h3><ul class="duo-list">'
      '<li>A 40ft high-cube holds about 65–68 m³ usable</li>'
      '<li>A packed guest-room FF&amp;E set runs 3–5 m³</li>'
      '<li>One container usually carries three or four factories</li>'
      '<li>Assembled furniture roughly doubles the shipped volume</li>'
      '<li>Flat-pack halves freight and moves risk to the last mile</li>'
      '</ul></div>'
      '<div class="duo-card gold"><span class="tag">The failure</span>'
      '<h3>What it costs</h3><ul class="duo-list">'
      '<li>Damage claims on poorly packed furniture run 3–8% of value</li>'
      '<li>On a $40,000 shipment that is $2,000 — more than haggling 3% off '
      'the unit price saves</li>'
      '<li>Corner protection and crates are cheap; a replacement is not</li>'
      '<li>E-commerce parcels need ISTA-tested packaging, not export cartons'
      '</li>'
      '<li>Loading should be supervised and photographed, every time</li>'
      '</ul></div></div></div></section>')

    # ---- compliance -----------------------------------------------------
    a('<section class="section"><div class="wrap"><div class="section-header">'
      '<div><div class="eyebrow">Compliance</div>'
      '<h2>Not one rule.<br><em>A stack, by destination.</em></h2></div>'
      '<p>This is where importers get hurt, because the requirement depends '
      'on the product and the market, not on the factory.</p></div>'
      '<div class="buy-price pillar-cols-4">'
      '<div class="buy-price-row"><b>Market</b><b>Product</b>'
      '<b>What applies</b><b>What to ask for</b></div>')
    a(rows(COMPLIANCE,
           '<div class="buy-price-row"><b>%s</b><span>%s</span><em>%s</em>'
           '<span>%s</span></div>'))
    a('</div>'
      '<p class="buy-lead" style="margin-top:26px">Build the checklist per '
      'SKU and get the test reports before production starts. Retrofitting '
      'compliance onto a finished container is not a thing — and a missing '
      'label can get goods refused even when the product itself passes every '
      'test.</p></div></section>')

    # ---- routes ---------------------------------------------------------
    a('<section class="section ivory"><div class="wrap">'
      '<div class="section-header"><div>'
      '<div class="eyebrow">How to buy</div>'
      '<h2>Three routes.<br><em>Different risk, not different price.</em>'
      '</h2></div><p>All three can be correct. The question is which risks '
      'you want to carry yourself.</p></div><div class="cards3">')
    for name, sub, bullets in ROUTES:
        a('<div class="service-card"><h3>%s</h3><p>%s</p>'
          '<ul class="duo-list">%s</ul></div>'
          % (name, sub, ''.join('<li>%s</li>' % b for b in bullets)))
    a('</div></div></section>')

    # ---- checklist ------------------------------------------------------
    a('<section class="section"><div class="wrap split-columns"><div>'
      '<div class="eyebrow">Before you send the brief</div>'
      '<h2>Eight things.<br><em>None of them optional.</em></h2>'
      '<p>You do not need every answer to start. You do need the ones that '
      'change which factory we approach.</p></div>'
      '<div class="check-grid">')
    a(''.join('<div class="check">%s</div>' % c for c in CHECKS))
    a('</div></div></section>')

    # ---- down-links -----------------------------------------------------
    a('<section class="section panel"><div class="wrap">'
      '<div class="section-header"><div>'
      '<div class="eyebrow">Go deeper</div>'
      '<h2>Six categories.<br><em>One buying desk.</em></h2></div>'
      '<p>Each category page carries its own sub-categories, materials and '
      'failure points, indicative MOQ and lead times, and the packaging and '
      'compliance notes specific to that product.</p></div>'
      '<div class="cards3">')
    for href, name, note in CATS:
        a('<div class="service-card"><h3>%s</h3><p>%s</p>'
          '<a class="text-link" href="%s">Open the category page '
          '<span>↗</span></a></div>' % (name, note, href))
    a('</div>'
      '<p class="buy-lead" style="margin-top:26px">Not sure which route fits? '
      '<a href="/c-sourcing">Personal shopping</a> handles one-off buys from '
      'Taobao, 1688 and Tmall. <a href="/b2b-procurement">B2B buying</a> '
      'handles BOQs, factory shortlists and container consolidation. Both '
      'start the same way — with a conversation.</p>'
      '</div></section>')

    # ---- faq ------------------------------------------------------------
    a('<section class="section ivory"><div class="wrap">'
      '<div class="section-header"><div>'
      '<div class="eyebrow">Common questions</div>'
      '<h2>Before the first order.<br><em>Answered plainly.</em></h2></div>'
      '<p>These are the questions buyers ask us before they send a furniture '
      'brief.</p></div><div class="faq-list">')
    a(''.join('<details><summary>%s</summary><p>%s</p></details>' % (q, answ)
              for q, answ in FAQ))
    a('</div></div></section>')

    # ---- cta ------------------------------------------------------------
    a('<section class="cta-band"><div class="wrap"><div>'
      '<div class="eyebrow">The first step is simple</div>'
      '<h2>Have a furniture brief?<br><em>Let’s go through it.</em></h2>'
      '<p>Send drawings, a reference photo or a BOQ. We will tell you which '
      'cluster should make it, what it will realistically cost landed, and '
      'where the risks sit before any money moves.</p></div>'
      '<a class="btn gold" href="/inquiry?type=product">Send a Furniture '
      'Brief <span class="arrow">↗</span></a></div></section>')

    return '\n'.join(p)


def build_ld():
    graph = [
        {
            '@type': 'BreadcrumbList',
            '@id': URL + '#breadcrumb',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home',
                 'item': SITE + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Sourcing',
                 'item': SITE + '/sourcing'},
                {'@type': 'ListItem', 'position': 3,
                 'name': 'China Furniture Sourcing', 'item': URL},
            ],
        },
        {
            '@type': 'Service',
            '@id': URL + '#service',
            'name': 'China furniture sourcing',
            'serviceType': 'Furniture sourcing and buying agent service',
            'provider': {'@id': SITE + '/#organization'},
            'areaServed': ['AU', 'US', 'GB', 'SG', 'AE', 'DE', 'FR'],
            'description': DESC,
            'url': URL,
            'hasOfferCatalog': {
                '@type': 'OfferCatalog',
                'name': 'Furniture sourcing categories',
                'itemListElement': [
                    {'@type': 'Offer',
                     'itemOffered': {'@type': 'Service', 'name': n,
                                     'url': SITE + h}}
                    for h, n, _note in CATS
                ],
            },
        },
        {
            '@type': 'FAQPage',
            '@id': URL + '#faq',
            'mainEntity': [
                {'@type': 'Question', 'name': q,
                 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
                for q, a in FAQ
            ],
        },
    ]
    return json.dumps({'@context': 'https://schema.org', '@graph': graph},
                      ensure_ascii=False, indent=2)


def update_sitemap(today):
    """Rebuild the pillar entry instead of appending it."""
    sm = io.open(SITEMAP, encoding='utf-8').read()
    sm = re.sub(
        r'[ \t]*<url>\s*<loc>https://ozfurnishing\.com/%s</loc>.*?</url>\n?'
        % SLUG, '', sm, flags=re.S)
    entry = ('  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n'
             '  </url>\n' % (URL, today))
    sm = sm.replace('</urlset>', entry + '</urlset>')
    with io.open(SITEMAP, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(sm)
    return sm.count('<loc>')


PAGE = u"""<!doctype html><html lang="en"><head><meta charset="utf-8">\
<meta name="viewport" content="width=device-width,initial-scale=1">\
<meta name="description" content="%(desc)s"><meta name="theme-color" \
content="#090a09">
    <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="OZ International">
    <meta property="og:title" content="%(title)s">
    <meta property="og:description" content="%(desc)s">
    <meta property="og:image" content="%(site)s/assets/img/product-3.jpg">
    <meta property="og:url" content="%(url)s">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="canonical" href="%(url)s">\
<title>%(title)s</title><link rel="stylesheet" href="/assets/style.css">
    <script type="application/ld+json">
%(ld)s
    </script>
</head><body><div class="topline"><div class="wrap"><span>OZ INTERNATIONAL \
&nbsp; / &nbsp; CHINA SOURCING &amp; TRADE</span><span class="right">\
<span class="accent">A DIRECT LINE TO CHINA</span> &nbsp; · &nbsp; GLOBAL \
BUYER SUPPORT</span></div></div>
%(header)s<div class="nav-overlay" id="navOverlay" aria-hidden="true"></div>\
<main>
%(body)s
</main>
%(footer)s
        <script src="/assets/main.js" defer></script>
  </body></html>
"""


def main():
    header, footer = build_chrome()
    today = datetime.date.today().isoformat()
    page = PAGE % {
        'desc': esc(DESC),
        'title': esc(TITLE),
        'site': SITE,
        'url': URL,
        'ld': build_ld(),
        'header': header,
        'footer': footer,
        'body': build_body(),
    }
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(page)
    print('wrote %-38s %6d bytes  (canonical: /%s)'
          % ('%s.html' % SLUG, len(page.encode('utf-8')), SLUG))
    print('sitemap: %d urls' % update_sitemap(today))


if __name__ == '__main__':
    main()
