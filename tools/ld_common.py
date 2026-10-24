# -*- coding: utf-8 -*-
"""Shared JSON-LD building blocks for the page generators.

Centralises the site's Organisation entity so every *generated* page carries
the same @id / name / sameAs as the hand-written pages (index, about, the two
sourcing flows, etc.). This is the root-cause fix for the 2026-10-24 incident
where re-running a generator wiped the sameAs block that _inject_analytics.py
had bolted on afterwards: now the entity lives in the generated source, so a
rerun keeps it, and the injector's re-render becomes a no-op.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://ozfurnishing.com'

# Mirror of seo-keys.json's sameAs. Used only if that file is missing or empty,
# so a generator run never crashes and always emits a usable entity.
_FALLBACK_SAMEAS = [
    "https://www.instagram.com/ozfurnishing/",
    "https://www.facebook.com/profile.php?id=61590202000316",
]


def load_sameas():
    """Read sameAs from seo-keys.json (one level above the repo root).

    Returns the list of URLs, or the hard fallback when the file is absent or
    the field is empty. Single source of truth is seo-keys.json; this loader
    only falls back so the generators stay runnable on their own.
    """
    keys = os.path.join(ROOT, '..', 'seo-keys.json')
    if os.path.isfile(keys):
        try:
            with open(keys, encoding='utf-8') as fh:
                cfg = json.load(fh)
            urls = [u for u in cfg.get('sameAs', []) if u]
            if urls:
                return urls
        except (ValueError, OSError):
            pass
    return list(_FALLBACK_SAMEAS)


def organization_node():
    """The site's Organization entity, identical to index.html's.

    Includes sameAs so every generated page is itself a sameAs anchor and the
    _inject_analytics.py re-render stays idempotent once present.
    """
    return {
        '@type': 'Organization',
        '@id': SITE + '/#organization',
        'name': 'OZ International',
        'url': SITE + '/',
        'logo': {
            '@type': 'ImageObject',
            'url': SITE + '/assets/favicon.svg',
            'width': 512,
            'height': 512,
        },
        'description': ('China sourcing agent and buying partner for furniture, '
                        'home decor, home textiles and project procurement.'),
        'sameAs': load_sameas(),
        'email': '807735000@qq.com',
        'telephone': '+86-180-2586-5699',
        'address': {
            '@type': 'PostalAddress',
            'addressCountry': 'CN',
        },
        'areaServed': ['AU', 'US', 'GB', 'SG', 'AE', 'DE', 'FR'],
        'contactPoint': [{
            '@type': 'ContactPoint',
            'contactType': 'sales',
            'telephone': '+86-180-2586-5699',
            'email': '807735000@qq.com',
            'availableLanguage': ['en', 'zh'],
        }],
    }
