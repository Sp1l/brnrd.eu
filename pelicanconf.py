#!/usr/bin/env python
# -*- coding: utf-8 -*- #

AUTHOR = "Bernard Spil"
SITENAME = "brnrd - Bernard Spil"
SITEURL = "https://brnrd.eu"

PATH = "content"

TIMEZONE = "Europe/Amsterdam"

DEFAULT_LANG = "en"

DIRECT_TEMPLATES = ["index", "categories", "authors", "archives", "search"]

# Feed generation is usually not desired when developing
FEED_ATOM = "feed.atom"
FEED_RSS = "feed.rss"
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (
    ("FreeBSD", "http://freebsd.org/"),
    ("HSLnet", "http://hslnet.nl/"),
    ("PrivacyCafe", "https://privacycafe.bof.nl/"),
)

# Social widget
SOCIAL = (
    ("<i class=\"fa-li fa fa-mastodon\"></i> Fediverse", "https://bsd.network/brnrd"),
    ("<i class=\"fa-li fa fa-github\"></i> Github", "https://github.com/Sp1l"),
    ("<i class=\"fa-li fa\"></i> FreeBSD", "https://wiki.freebsd.org/BernardSpil"),
)

DISPLAY_PAGES_ON_MENU = False

DEFAULT_PAGINATION = False

ARTICLE_URL     = "{category}/{date:%Y-%m-%d}/{slug}.html"
ARTICLE_SAVE_AS = "{category}/{date:%Y-%m-%d}/{slug}.html"

STATIC_PATHS = ["img", "favicon.ico"]

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

# Modified clone of https://github.com/Samael500/w3-personal-blog
# Repo incl modifications at https://github.com/Sp1l/w3-personal-blog
THEME = "./themes/w3-personal-blog"

# ./plugins is a symlink to a repo clone of https://github.com/getpelican/pelican-plugins
PLUGIN_PATHS= ["./plugins",]
PLUGINS = [
    "pelican-toc",
    "bootstrapify",
    "sitemap"
]

NOMARKDOWN = {
    "extension_configs": {
       "markdown.extensions.toc": {},
       "markdown.extensions.codehilite": {"css_class": "highlight"},
       "markdown.extensions.admonition": {},
       "markdown.extensions.extra": { "tables": {}, },
    },
    "output_format": "html5",
}

TOC_RUN = False
TOC_HEADERS = "^h[1-2]"

SITEMAP = {
    "format": "xml",
}

LOAD_CONTENT_CACHE = True
CHECK_MODIFIED_METHOD = "mtime"
