#!/usr/bin/env python3
"""Генератор сайта True Rides Japan.

Источники:  data/cars.json, data/images.json, _src/*.
Результат:  готовые HTML-страницы в корне репозитория (/, /ua/, /en/, страницы моделей и машин),
            sitemap.xml, robots.txt.
Запуск:     python3 _src/build.py
"""
import json, os, re, html, shutil
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_src")
SITE = "https://trueridesjapan.com"
TODAY = date.today().isoformat()

T = json.load(open(os.path.join(SRC, "i18n.json"), encoding="utf-8"))
X = json.load(open(os.path.join(SRC, "texts.json"), encoding="utf-8"))
for lg in T:
    T[lg].update(X["ui"][lg])
D = json.load(open(os.path.join(SRC, "dicts.json"), encoding="utf-8"))
CARS = json.load(open(os.path.join(ROOT, "data", "cars.json"), encoding="utf-8"))
IMGS = json.load(open(os.path.join(ROOT, "data", "images.json"), encoding="utf-8"))
CSS = open(os.path.join(SRC, "page.css"), encoding="utf-8").read() + open(os.path.join(SRC, "extra.css"), encoding="utf-8").read()
MAIN = open(os.path.join(SRC, "main_sections.html"), encoding="utf-8").read()
# Дата последней сверки расписания с BeForward (показывается в карточке машины).
META = json.load(open(os.path.join(ROOT, "data", "meta.json"), encoding="utf-8"))
ARTICLES = json.load(open(os.path.join(SRC, "articles.json"), encoding="utf-8"))
# Коды подтверждения поисковиков (Google Search Console, Яндекс Вебмастер, Bing) и ключ IndexNow.
SEO = json.load(open(os.path.join(SRC, "seo.json"), encoding="utf-8"))
VERIFY_META = "".join(f'<meta name="{n}" content="{html.escape(v, quote=True)}">\n' for n, v in
                      [("google-site-verification", SEO.get("google")), ("yandex-verification", SEO.get("yandex")), ("msvalidate.01", SEO.get("bing"))] if v)

LANGS = ["ru", "uk", "en"]
PREFIX = {"ru": "", "uk": "ua/", "en": "en/", "hy": "hy/"}
HREFLANG = {"ru": "ru", "uk": "uk", "en": "en", "hy": "hy"}
LI = {"ru": 0, "uk": 1, "en": 2}
OGLOC = {"ru": "ru_RU", "uk": "uk_UA", "en": "en_GB", "hy": "hy_AM"}
LANG_LABEL = {"ru": "RU", "uk": "UA", "en": "EN", "hy": "HY"}
# Статьи могут быть не на всех языках сайта (поле "langs"); армянский (hy) есть только у отдельных статей.
alangs = lambda a: a.get("langs", LANGS)
ui_lang = lambda lg: lg if lg in LANGS else "ru"
MONTHS = {
    "ru": ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
    "uk": ["січ", "лют", "бер", "квіт", "трав", "черв", "лип", "серп", "вер", "жовт", "лист", "груд"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
FAMILY_SLUG = {"minivan": "toyota-alphard-vellfire", "note": "nissan-note-e-power"}

esc = lambda s: html.escape(str(s), quote=True)
nbsp = " "


def num(n):
    return f"{n:,}".replace(",", nbsp)


def usd(n):
    return "$" + num(n)


def t(lg, k):
    return T[lg].get(k, k)


def url(lg, path=""):
    return "/" + PREFIX[lg] + path


def abs_url(lg, path=""):
    return SITE + url(lg, path)


# ---------- данные машины ----------
def pretty_grade(g):
    g = re.sub(r"^HYBRID\s+", "", g).replace("E-POWER", "e-Power")
    out = []
    for w in g.split(" "):
        if w == "2":
            out.append("II")
        elif re.fullmatch(r"e-Power|X|S|FOUR|240S|2\.4Z|2\.5Z|A|G|AUTECH", w):
            out.append(w)
        else:
            out.append(w[:1] + w[1:].lower())
    return " ".join(out)


def names(c):
    g = pretty_grade(c["grade"])
    if c["fam"] == "note" and "e-Power" not in g:
        g = "e-Power " + g
    model = c["model"] + (" " + c["gen"] if c["fam"] == "minivan" else "")
    return model, g


def engine(c, lg):
    return "1.2 " + t(lg, "epower") if c["fam"] == "note" else f"{c['engine']/1000:.1f} " + t(lg, "petrol")


def color(c, lg):
    return D["COLORS"].get(c["color"], [c["color"]] * 3)[LI[lg]]


def options(c, lg):
    s, out = c["acc"], []
    if "GOLDEN EYES" in c["grade"]:
        out.append(D["OPTS"]["GOLDEN"][LI[lg]])
    for k in ["Power Slide Door", "Body Kit", "Sunroof", "Back Camera", "360 Degree Camera", "Rear Spoiler", "Side Airbag"]:
        if k in s:
            out.append(D["OPTS"][k][LI[lg]])
    if "Push Start" in s and "Keyless" in s:
        out.append(D["OPTS"]["SMART"][LI[lg]])
    elif "Push Start" in s:
        out.append(D["OPTS"]["Push Start"][LI[lg]])
    return out


def dshort(d, lg):
    y, m, dd = map(int, d.split("-"))
    return f"{dd} {MONTHS[lg][m-1]} {y}"


def route(c, lg):
    if not c.get("loading"):
        return {"ru": "Япония → Поти", "uk": "Японія → Поті", "en": "Japan → Poti"}[lg]
    port = D["PORTS"].get(c["loading"], [c["loading"]] * 3)[LI[lg]]
    poti = {"ru": "Поти", "uk": "Поті", "en": "Poti"}[lg]
    # Названия судов (vessel/vessel2) на сайте не показываем — только маршрут; для клиента — номер контейнера.
    return f"{port} → {poti}"


def container_row(c, lg):
    """Строка «Контейнер» на странице машины: номер со ссылкой на отслеживание MSC."""
    cn = (c.get("container") or "").strip().upper()
    if not cn:
        return ""
    url = f"https://www.msc.com/en/track-a-shipment?trackingNumber={cn}"
    return (f"<tr><td>{t(lg,'k_container')}</td><td><a href=\"{url}\" target=\"_blank\" "
            f"rel=\"noopener\">{esc(cn)}</a></td></tr>")


def state(c):
    """prep — судна нет; wait — судно назначено, ещё не отплыло; sail — в пути; arrived — прибыл в Поти."""
    if c.get("eta") and c["eta"] <= TODAY:
        return "arrived"
    if c.get("etd") and c["etd"] <= TODAY:
        return "sail"
    if c.get("etd"):
        return "wait"
    return "prep"


def status_texts(c, lg):
    return {
        "prep": t(lg, "prep"),
        "wait": (f"{t(lg,'st_wait')} · ~{dshort(c['etd'], lg)}"
                 + (f" · {t(lg,'eta')}{dshort(c['eta'], lg)}" if c.get("eta") else "")) if c.get("etd") else t(lg, "prep"),
        "sail": f"{t(lg,'transit')} · {t(lg,'eta')}{dshort(c['eta'], lg)}" if c.get("eta") else t(lg, "transit"),
        "arrived": t(lg, "st_arrived"),
    }


def status(c, lg):
    return status_texts(c, lg)[state(c)]


def status_attrs(c, lg):
    tx = status_texts(c, lg)
    return (f' data-etd="{c.get("etd") or ""}" data-eta="{c.get("eta") or ""}"'
            + "".join(f' data-t-{k}="{esc(v)}"' for k, v in tx.items()))


def deposit(c):
    """Фиксированная бронь по группе (одинаковая для Украины и Грузии): Note HE12 / E13, Alphard·Vellfire 20 / 30."""
    return {"HE12": 3000, "E13": 4500, "20": 4000, "30": 5000}[c["gen"]]


def deposit_text(c, lg):
    return t(lg, "bk_car").format(amt=usd(deposit(c)))


def car_slug(c):
    return f"cars/{c['ref'].lower()}/"


def photos(c):
    return IMGS.get(c["ref"], [])


def img_src(p, depth):
    """Локальные файлы — относительно корня сайта, внешние ссылки как есть."""
    return p if p.startswith("http") else "/" + p


# ---------- общие куски ----------
SHIP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 17l2 3h14l2-3M5 17V11l7-3 7 3v6M12 4v4"/></svg>'
IG_ICO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg>'
TG_ICO = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.9 4.3 18.7 19.4c-.2 1.1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.3-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6.2 13 1.4 11.5c-1-.3-1-1 .2-1.5L20.5 2.8c.9-.3 1.6.2 1.4 1.5z"/></svg>'
SUN = '<svg id="icoSun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
MOON = '<svg id="icoMoon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/></svg>'


def head(lg, path, title, desc, image, ld, alts=True):
    links = ""
    if alts:
        for l2 in (alts if isinstance(alts, list) else LANGS):
            links += f'<link rel="alternate" hreflang="{HREFLANG[l2]}" href="{abs_url(l2, path)}">\n'
        links += f'<link rel="alternate" hreflang="x-default" href="{abs_url("ru", path)}">\n'
    img = image if image.startswith("http") else SITE + "/" + image.lstrip("/")
    return f"""<!doctype html>
<html lang="{HREFLANG[lg]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{abs_url(lg, path)}">
{links}{VERIFY_META}<link rel="icon" href="/assets/logo.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="True Rides Japan">
<meta property="og:locale" content="{OGLOC[lg]}">
<meta property="og:url" content="{abs_url(lg, path)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{esc(img)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;700&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<script>try{{var th=localStorage.getItem("tr_theme");if(th==="light"||th==="dark")document.documentElement.setAttribute("data-theme",th)}}catch(e){{}}</script>
<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}img{{max-width:100%}}
{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
"""


def header(lg, path, langs_list=None, cur=None):
    cur = cur or lg
    langs = "".join(
        f'<a href="{url(l2, path)}" hreflang="{HREFLANG[l2]}" aria-current="{"true" if l2 == cur else "false"}">{LANG_LABEL[l2]}</a>'
        for l2 in (langs_list or LANGS)
    )
    home = url(lg)
    return f"""<header class="top">
  <div class="wrap">
    <a class="brand" href="{home}" aria-label="True Rides Japan"><span class="dot"></span><span><b>TRUE RIDES</b><small>JAPAN</small></span></a>
    <nav class="main">
      <a href="{home}#catalog">{t(lg,'nav_catalog')}</a>
      <a href="{home}#route">{t(lg,'nav_route')}</a>
      <a href="{home}#delivery">{t(lg,'nav_delivery')}</a>
      <a href="{url(lg, 'blog/')}">{t(lg,'nav_blog')}</a>
      <a href="{home}#contacts">{t(lg,'nav_contacts')}</a>
    </nav>
    <nav class="langs" aria-label="Language">{langs}</nav>
    <button class="tbtn" type="button" id="themeBtn" aria-label="Theme">{SUN}{MOON}</button>
  </div>
</header>
"""


def footer(lg):
    home = url(lg)
    models = " · ".join(f'<a href="{url(lg, FAMILY_SLUG[f]+"/")}">{esc(X["models"][f][lg]["h1"])}</a>' for f in ["minivan", "note"])
    return f"""<footer><div class="wrap"><span>© 2026 True Rides Japan</span><span class="fmodels">{models}</span><span class="social"><a href="https://www.instagram.com/true_rides/" target="_blank" rel="noopener" aria-label="Instagram">{IG_ICO}</a><a href="https://t.me/truerides_chat" target="_blank" rel="noopener" aria-label="{t(lg,'ct_chat')}">{TG_ICO}</a></span><span>trueridesjapan.com</span></div></footer>
<div class="bar">
  <a class="btn red" href="https://t.me/+380663666886" target="_blank" rel="noopener">Telegram</a>
  <a class="btn ghost" href="viber://chat?number=%2B380663666886">Viber</a>
  <a class="btn ghost" href="https://wa.me/380663666886" target="_blank" rel="noopener">WhatsApp</a>
</div>
"""


SCRIPT = """<script>
(function(){
var d=document.documentElement;
function isDark(){var a=d.getAttribute("data-theme");if(a)return a==="dark";return !matchMedia("(prefers-color-scheme: light)").matches}
function paint(){var k=isDark();var s=document.getElementById("icoSun"),m=document.getElementById("icoMoon");if(s)s.toggleAttribute("hidden",!k);if(m)m.toggleAttribute("hidden",k)}
var tb=document.getElementById("themeBtn");if(tb)tb.addEventListener("click",function(){var n=isDark()?"light":"dark";d.setAttribute("data-theme",n);try{localStorage.setItem("tr_theme",n)}catch(e){}paint()});
try{matchMedia("(prefers-color-scheme: light)").addEventListener("change",paint)}catch(e){}
paint();
var f=document.getElementById("filters");
if(f){var fam="all",st="all";f.addEventListener("click",function(e){var b=e.target.closest("button");if(!b)return;
 if(b.dataset.fam){fam=b.dataset.fam}else if(b.dataset.st){st=st===b.dataset.st?"all":b.dataset.st}
 f.querySelectorAll("[data-fam]").forEach(function(x){x.setAttribute("aria-pressed",x.dataset.fam===fam)});
 f.querySelectorAll("[data-st]").forEach(function(x){x.setAttribute("aria-pressed",x.dataset.st===st)});
 var G={transit:["sail","arrived"],prep:["wait","prep"]};var n=0;document.querySelectorAll("#grid .card").forEach(function(c){var ok=(fam==="all"||c.dataset.fam===fam)&&(st==="all"||G[st].indexOf(c.dataset.st)>=0);c.hidden=!ok;if(ok)n++});
 var em=document.getElementById("emptyMsg");if(em)em.hidden=n>0;});}
var today=new Date().toISOString().slice(0,10);function stOf(e,d){if(e&&e<=today)return"arrived";if(d&&d<=today)return"sail";if(d)return"wait";return"prep"}
document.querySelectorAll(".js-status").forEach(function(el){var s=stOf(el.dataset.eta,el.dataset.etd);var tx=el.getAttribute("data-t-"+s);if(tx){var i=el.querySelector("i");el.textContent=tx;if(i)el.prepend(i)}el.classList.toggle("wait",s==="wait"||s==="prep");var card=el.closest(".card");if(card)card.dataset.st=s});
var cnt={transit:0,prep:0},sail=0;document.querySelectorAll("#grid .card").forEach(function(c){var s=c.dataset.st;if(s==="sail")sail++;if(s==="sail"||s==="arrived")cnt.transit++;else cnt.prep++});
var ns=document.getElementById("nSail");if(ns)ns.textContent=sail;document.querySelectorAll("[data-cnt]").forEach(function(x){x.textContent=cnt[x.dataset.cnt]});
var g=document.querySelector(".gal");
if(g){g.addEventListener("click",function(e){var b=e.target.closest(".thumbs button");if(!b)return;var big=document.getElementById("big");big.src=b.dataset.src;
 g.querySelectorAll(".thumbs button").forEach(function(x){x.setAttribute("aria-current",x===b)})});}
document.querySelectorAll("img[data-fallback]").forEach(function(im){im.addEventListener("error",function(){var c=im.closest(".ph");if(c)c.classList.add("noimg");im.remove()})});
document.querySelectorAll("[data-copy]").forEach(function(b){b.addEventListener("click",function(){var v=b.dataset.copy;if(navigator.clipboard)navigator.clipboard.writeText(v).then(function(){b.textContent=b.dataset.done}).catch(function(){})})});
})();
</script>
</body>
</html>
"""


PHONE = "+380663666886"
PHONE_TXT = "+380 66 366 68 86"
CALL = "+995511184186"
CALL_TXT = "+995 511 18 41 86"


def contact_buttons(lg, msg="", ref=""):
    from urllib.parse import quote
    wa = "https://wa.me/380663666886" + ("?text=" + quote(msg) if msg else "")
    hint = f'<p class="book">{t(lg,"tg_hint")} <b>№ {ref}</b></p>' if ref else ""
    return f'''<div class="cbtns">
  <a class="btn red" href="https://t.me/+380663666886" target="_blank" rel="noopener">{TG_ICO}Telegram</a>
  <a class="btn ghost" href="viber://chat?number=%2B380663666886">Viber</a>
  <a class="btn ghost" href="{esc(wa)}" target="_blank" rel="noopener">WhatsApp</a>
</div>
<p class="book">{t(lg,'msg_l')} <b class="sel">{PHONE_TXT}</b></p>{hint}'''


def placeholder(c, lg):
    tag = ("NOTE " + c["gen"]) if c["fam"] == "note" else (c["model"].split(" ")[1].upper() + " " + c["gen"])
    return f'<div class="none"><b>{tag}</b><span>{t(lg,"nophoto")}</span></div>'


def badge(c, lg):
    st = state(c)
    cls = "status wait" if st in ("prep", "wait") else "status"
    return f'<span class="{cls} js-status"{status_attrs(c, lg)}><i></i>{esc(status(c, lg))}</span>'


def card(c, lg):
    model, g = names(c)
    ph = photos(c)
    imgs = (f'<img src="{img_src(ph[0],0)}" alt="{esc(model+" "+g)}" loading="lazy" referrerpolicy="no-referrer" data-fallback>' if ph else "")
    awd = '<span class="awd">4WD</span>' if c["drive"] == "4WD" else ""
    st = state(c)
    return f"""<a class="card" href="{url(lg, car_slug(c))}" data-fam="{c['fam']}" data-st="{st}">
  <div class="ph{'' if ph else ' noimg'}">{imgs}{placeholder(c, lg)}{badge(c, lg)}</div>
  <div class="body"><h3>{esc(model)}<small>{esc(g)} · {c['year']}</small></h3>
  <div class="specs"><span>{num(c['mileage'])} {t(lg,'km')}</span><span>{esc(engine(c, lg))}</span>{awd}<span>{esc(color(c, lg))}</span></div>
  <div class="ship">{SHIP}<span>{esc(route(c, lg))}</span></div>
  <div class="price"><div><small>{t(lg,'ua')}, {t(lg,'ua_s')}</small><b>{usd(c['priceUA'])}</b></div><div class="ge">{t(lg,'ge')}<br><strong>{usd(c['priceGE'])}</strong></div></div>
  </div></a>"""


def sort_cars(cs):
    return sorted(cs, key=lambda c: (0 if c.get("eta") else 1, c.get("eta") or "9", c["priceUA"]))


def car_ld(c, lg):
    model, g = names(c)
    brand, mdl = c["model"].split(" ", 1)
    return {
        "@context": "https://schema.org", "@type": "Car",
        "name": f"{model} {g} {c['year']}", "brand": {"@type": "Brand", "name": brand}, "model": mdl,
        "vehicleModelDate": str(c["year"]), "color": color(c, lg),
        "mileageFromOdometer": {"@type": "QuantitativeValue", "value": c["mileage"], "unitCode": "KMT"},
        "driveWheelConfiguration": "https://schema.org/AllWheelDriveConfiguration" if c["drive"] == "4WD" else "https://schema.org/FrontWheelDriveConfiguration",
        "vehicleEngine": {"@type": "EngineSpecification", "engineDisplacement": {"@type": "QuantitativeValue", "value": round(c["engine"] / 1000, 1), "unitCode": "LTR"}},
        "steeringPosition": "https://schema.org/RightHandDriving",
        "image": [p if p.startswith("http") else SITE + "/" + p for p in photos(c)[:6]],
        "url": abs_url(lg, car_slug(c)),
        "offers": {"@type": "Offer", "price": c["priceUA"], "priceCurrency": "USD", "availability": "https://schema.org/PreOrder",
                   "areaServed": "UA", "seller": {"@type": "AutoDealer", "name": "True Rides Japan", "url": SITE}},
    }


def crumbs_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


DEALER = {"@context": "https://schema.org", "@type": "AutoDealer", "name": "True Rides Japan", "url": SITE + "/",
          "logo": SITE + "/assets/logo.png", "image": SITE + "/assets/og.jpg", "telephone": "+995511184186",
          "address": {"@type": "PostalAddress", "addressLocality": "Rustavi", "addressCountry": "GE"},
          "areaServed": ["UA", "GE", "AM", "IE"], "sameAs": ["https://www.instagram.com/true_rides/", "https://t.me/truerides_chat"]}


def write(rel, content):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content)


# ---------- главная ----------
def fill_i18n(markup, lg):
    markup = re.sub(r'(<(\w+)([^>]*?)data-i18n-html="(\w+)"([^>]*)>)(</\2>)', lambda m: m.group(1) + t(lg, m.group(4)) + m.group(6), markup)
    markup = re.sub(r'(<(\w+)([^>]*?)data-i18n="(\w+)"([^>]*)>)(</\2>)', lambda m: m.group(1) + esc(t(lg, m.group(4))) + m.group(6), markup)
    return markup


def page_home(lg):
    cs = sort_cars(CARS)
    transit = sum(1 for c in CARS if state(c) == "sail")
    m = fill_i18n(MAIN, lg)
    m = m.replace('<img class="emblem em-light" src="assets/logo.png"', '<img class="emblem em-light" src="/assets/logo.png"')
    m = m.replace('src="assets/logo-dark.png"', 'src="/assets/logo-dark.png"')
    m = m.replace('<div class="facts" id="facts"></div>',
                  f'<div class="facts" id="facts"><div><b>{len(CARS)}</b><span>{t(lg,"f1")}</span></div><div><b id="nSail">{transit}</b><span>{t(lg,"f2")}</span></div><div><b>~4</b><span>{t(lg,"f3")}</span></div></div>')
    cnt = lambda f: sum(1 for c in CARS if f == "all" or c["fam"] == f)
    grp = {"transit": ("sail", "arrived"), "prep": ("wait", "prep")}
    stc = lambda s: sum(1 for c in CARS if state(c) in grp[s])
    filt = "".join(f'<button class="chip" type="button" data-fam="{f}" aria-pressed="{"true" if f=="all" else "false"}">{t(lg,f)}<span class="n">{cnt(f)}</span></button>' for f in ["all", "minivan", "note"])
    filt += '<span class="sep"></span>' + "".join(f'<button class="chip" type="button" data-st="{s}" aria-pressed="false">{t(lg,s)}<span class="n" data-cnt="{s}">{stc(s)}</span></button>' for s in ["transit", "prep"])
    m = m.replace('<div class="filters" id="filters"></div>', f'<div class="filters" id="filters">{filt}</div>')
    m = m.replace('<div class="grid" id="grid"></div>',
                  f'<div class="grid" id="grid">{"".join(card(c, lg) for c in cs)}</div><p class="empty" id="emptyMsg" hidden>{t(lg,"empty")}</p>'
                  f'<div class="artlinks">{art_links(lg)}</div><p class="modlinks">{" · ".join(f"<a href=\"{url(lg, FAMILY_SLUG[f]+"/")}\">{esc(X["models"][f][lg]["h1"])} →</a>" for f in ["minivan","note"])}</p>')
    m = m.replace('<button class="copy" type="button" id="copyPhone" data-i18n="copy">', f'<button class="copy" type="button" data-copy="+380663666886" data-done="{esc(t(lg,"copied"))}">')
    items = [{"@type": "ListItem", "position": i + 1, "url": abs_url(lg, car_slug(c))} for i, c in enumerate(cs)]
    ld = [DEALER, {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": items}]
    title = X["home"][lg]["title"]
    desc = X["home"][lg]["desc"]
    write(PREFIX[lg] + "index.html", head(lg, "", title, desc, "assets/og.jpg", ld) + header(lg, "") + m + footer(lg) + SCRIPT)


# ---------- страница модели ----------
def page_model(lg, fam):
    M = X["models"][fam][lg]
    cs = sort_cars([c for c in CARS if c["fam"] == fam])
    path = FAMILY_SLUG[fam] + "/"
    minp = min(c["priceUA"] for c in cs)
    paras = "".join(f"<p>{esc(p)}</p>" for p in M["text"])
    crumbs = [(t(lg, "home"), abs_url(lg)), (M["h1"], abs_url(lg, path))]
    ld = [DEALER, crumbs_ld(crumbs), {"@context": "https://schema.org", "@type": "ItemList",
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": abs_url(lg, car_slug(c))} for i, c in enumerate(cs)]}]
    img = next((photos(c)[0] for c in cs if photos(c)), "assets/og.jpg")
    body = f"""<main>
<section class="wrap pagehead">
  <nav class="crumbs"><a href="{url(lg)}">{t(lg,'home')}</a> › <span>{esc(M['h1'])}</span></nav>
  <h1>{esc(M['h1'])}</h1>
  <p class="lead">{esc(M['lead'])}</p>
  <p class="fromprice">{t(lg,'from_price')} <b>{usd(minp)}</b> · {t(lg,'ua_full')}</p>
</section>
<section class="catalog wrap" id="catalog">
  <div class="grid" id="grid">{"".join(card(c, lg) for c in cs)}</div>
</section>
<section class="band"><div class="wrap prose">{paras}
  <div class="artlinks">{art_links(lg, fam)}</div>
  <div class="ctas"><a class="btn red" href="https://t.me/+380663666886" target="_blank" rel="noopener">{TG_ICO}<span>{t(lg,'cta_tg')}</span></a><a class="btn ghost" href="{url(lg)}#catalog">{t(lg,'all_cars')}</a></div>
</div></section>
</main>
"""
    write(PREFIX[lg] + path + "index.html", head(lg, path, M["title"].replace("{price}", usd(minp)), M["desc"].replace("{price}", usd(minp)), img, ld) + header(lg, path) + body + footer(lg) + SCRIPT)


# ---------- страница машины ----------
def page_car(lg, c):
    model, g = names(c)
    path = car_slug(c)
    ph = photos(c)
    fam = c["fam"]
    M = X["models"][fam][lg]
    opts = options(c, lg)
    if ph:
        big = f'<img id="big" src="{img_src(ph[0],0)}" alt="{esc(model+" "+g+" "+str(c["year"]))}" referrerpolicy="no-referrer" data-fallback>'
        thumbs = "".join(f'<button type="button" aria-label="{t(lg,"photo")} {i+1}" data-src="{img_src(p,0)}" aria-current="{"true" if i==0 else "false"}"><img src="{img_src(p,0)}" alt="" loading="lazy" referrerpolicy="no-referrer" data-fallback></button>' for i, p in enumerate(ph))
        gal = f'<div class="gal"><div class="main ph">{big}{placeholder(c, lg)}</div>' + (f'<div class="thumbs">{thumbs}</div>' if len(ph) > 1 else "") + "</div>"
    else:
        gal = f'<div class="gal"><div class="main ph noimg">{placeholder(c, lg)}</div></div>'
    drive = ("4WD, " + t(lg, "awd")) if c["drive"] == "4WD" else t(lg, "fwd")
    msg = f"{t(lg,'msg')} {model} {g} {c['year']}, {num(c['mileage'])} {t(lg,'km')} ({c['ref']})"
    from urllib.parse import quote
    wa = "https://wa.me/380663666886?text=" + quote(msg)
    note = f'<div class="note">{t(lg,"damaged")}</div>' if c.get("damaged") else ""
    # Своё примечание к машине: поле "note" в cars.json — {"ru": ..., "uk": ..., "en": ...}
    if c.get("note"):
        note += f'<div class="note">{esc(c["note"][lg])}</div>'
    optsh = (f'<div><p class="eyebrow" style="margin:0 0 8px">{t(lg,"opts")}</p><div class="opts">' + "".join(f"<span>{esc(o)}</span>" for o in opts) + "</div></div>") if opts else ""
    others = [x for x in sort_cars(CARS) if x["fam"] == fam and x["ref"] != c["ref"]][:4]
    crumbs = [(t(lg, "home"), abs_url(lg)), (M["h1"], abs_url(lg, FAMILY_SLUG[fam] + "/")), (c["ref"], abs_url(lg, path))]
    body = f"""<main>
<section class="wrap pagehead">
  <nav class="crumbs"><a href="{url(lg)}">{t(lg,'home')}</a> › <a href="{url(lg, FAMILY_SLUG[fam]+'/')}">{esc(M['h1'])}</a> › <span>{c['ref']}</span></nav>
</section>
<section class="wrap carpage">
  {gal}
  <div class="info">
    <div><p class="eyebrow">№ {c['ref']} · <span class="js-status"{status_attrs(c, lg)}>{esc(status(c, lg))}</span></p><h1>{esc(model)} {c['year']}</h1><div class="sub">{esc(g)}</div></div>
    <div class="prices"><div class="ua"><small>{t(lg,'ua')}</small><b>{usd(c['priceUA'])}</b><small>{t(lg,'ua_s')}</small></div><div><small>{t(lg,'ge')}</small><b>{usd(c['priceGE'])}</b>{('<small>'+t(lg,'ge_s')+'</small>') if t(lg,'ge_s') else ''}</div></div>
    <p class="book">{esc(deposit_text(c, lg))} <a class="bkl" href="{url(lg)}#booking">{t(lg,'bk_link')}</a></p>
    {note}
    <table class="kv"><tr><td>{t(lg,'k_status')}</td><td><span class="js-status"{status_attrs(c, lg)}>{esc(status(c, lg))}</span></td></tr><tr><td>{t(lg,'k_year')}</td><td>{c['year']}</td></tr><tr><td>{t(lg,'k_mileage')}</td><td>{num(c['mileage'])} {t(lg,'km')}</td></tr><tr><td>{t(lg,'k_engine')}</td><td>{esc(engine(c, lg))}</td></tr><tr><td>{t(lg,'k_drive')}</td><td>{esc(drive)}</td></tr><tr><td>{t(lg,'k_color')}</td><td>{esc(color(c, lg))}</td></tr><tr><td>{t(lg,'k_steer')}</td><td>{t(lg,'steer_v')}</td></tr><tr><td>{t(lg,'k_route')}</td><td>{esc(route(c, lg))}</td></tr>{container_row(c, lg)}</table>
    {f'<p class="book">{t(lg,"upd")} {dshort(META["schedule_updated"], lg)}</p>' if c.get("etd") else ""}
    {optsh}
    <p class="eyebrow" style="margin:0">{t(lg,'write')} · № {c['ref']}</p>
    {contact_buttons(lg, msg, c['ref'])}
  </div>
</section>
{f'''<section class="catalog wrap"><div class="cat-head"><h2>{t(lg,'more_same')}</h2><a class="btn ghost" href="{url(lg, FAMILY_SLUG[fam]+'/')}">{esc(M['h1'])} →</a></div><div class="grid">{"".join(card(x, lg) for x in others)}</div></section>''' if others else ''}
</main>
"""
    title = f"{model} {g} {c['year']}, {num(c['mileage'])} {t(lg,'km')} — {usd(c['priceUA'])} | True Rides Japan"
    desc = f"{status(c, lg)}. {engine(c, lg)}, {drive}, {color(c, lg)}" + (", " + ", ".join(opts[:3]) if opts else "") + f". {t(lg,'ua')}: {usd(c['priceUA'])} ({t(lg,'ua_s')}). {t(lg,'ge')}: {usd(c['priceGE'])}."
    img = ph[0] if ph else "assets/og.jpg"
    ld = [car_ld(c, lg), crumbs_ld(crumbs)]
    write(PREFIX[lg] + path + "index.html", head(lg, path, title, desc, img, ld) + header(lg, path) + body + footer(lg) + SCRIPT)


# ---------- статьи ----------
def art_path(a):
    return f"blog/{a['slug']}/"


def art_links(lg, fam=None):
    items = [a for a in ARTICLES if (fam is None or a["fam"] == fam) and lg in alangs(a)]
    return "".join(f'<a class="artlink" href="{url(lg, art_path(a))}"><span class="eyebrow">{esc(a[lg]["label"])}</span><b>{esc(a[lg]["title"])}</b></a>' for a in items)


def page_blog(lg):
    path = "blog/"
    B = X["blog"][lg]
    crumbs = [(t(lg, "home"), abs_url(lg)), (B["h1"], abs_url(lg, path))]
    ld = [crumbs_ld(crumbs), {"@context": "https://schema.org", "@type": "ItemList",
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": abs_url(lg, art_path(a))} for i, a in enumerate([a for a in ARTICLES if lg in alangs(a)])]}]
    items = ""
    for a in sorted([a for a in ARTICLES if lg in alangs(a)], key=lambda a: a["date"], reverse=True):
        A = a[lg]
        img = a.get("og", "assets/og.jpg")
        items += f'''<a class="postcard" href="{url(lg, art_path(a))}"><div class="pimg"><img src="/{img}" alt="" loading="lazy"></div><div class="pbody"><span class="eyebrow">{esc(A.get("eyebrow") or X["models"][a["fam"]][lg]["h1"])}</span><h2>{esc(A["title"])}</h2><p>{esc(A["desc"])}</p></div></a>'''
    body = f"""<main>
<section class="wrap pagehead">
  <nav class="crumbs"><a href="{url(lg)}">{t(lg,'home')}</a> › <span>{esc(B['h1'])}</span></nav>
  <h1>{esc(B['h1'])}</h1>
  <p class="lead">{esc(B['lead'])}</p>
</section>
<section class="wrap posts">{items}</section>
</main>
"""
    write(PREFIX[lg] + path + "index.html", head(lg, path, B["title"], B["lead"], "assets/og.jpg", ld) + header(lg, path) + body + footer(lg) + SCRIPT)


def page_article(lg, a):
    A = a[lg]
    path = art_path(a)
    M = X["models"][a["fam"]][lg]
    def figs(i, h):
        ph = a.get("photos", {}).get(str(i), [])
        if not ph:
            return ""
        cap = a.get("cap", {}).get(lg, h)
        return '<div class="figs">' + "".join(f'<figure><img src="/{p}" alt="{esc(cap)}" loading="lazy"></figure>' for p in ph) + (f'<p class="figcap">{esc(cap)}</p>' if a.get("cap") else "") + "</div>"
    steps = "".join(f'<li><h2>{esc(h)}</h2><p>{esc(p)}</p>' + figs(i, h) + (f'<p class="kit">{esc(A["kit"])} <a href="{a["kit_url"]}" target="_blank" rel="nofollow noopener">{esc(a["kit_url"].split("/")[2])}</a></p>' if i == 3 and a.get("kit_url") else "") + "</li>" for i, (h, p) in enumerate(A["steps"]))
    methods = (f'<h2>{esc(A["methods_h"])}</h2><ul class="methods">' + "".join(f"<li>{esc(m)}</li>" for m in A["methods"]) + f'</ul><h2>{esc(A["steps_h"])}</h2>') if A.get("methods") else ""
    cs = sort_cars([c for c in CARS if c["fam"] == a["fam"]])[:4]
    crumbs = [(t(lg, "home"), abs_url(lg)), (M["h1"], abs_url(lg, FAMILY_SLUG[a["fam"]] + "/")), (A["label"], abs_url(lg, path))]
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": A["title"], "description": A["desc"], "inLanguage": HREFLANG[lg],
           "datePublished": a["date"], "dateModified": a["date"], "author": {"@type": "Organization", "name": "True Rides Japan", "url": SITE},
           "publisher": {"@type": "Organization", "name": "True Rides Japan", "logo": {"@type": "ImageObject", "url": SITE + "/assets/logo.png"}},
           "image": SITE + "/" + a.get("og", "assets/og.jpg"), "mainEntityOfPage": abs_url(lg, path)}, crumbs_ld(crumbs)]
    body = f"""<main>
<article class="wrap article">
  <nav class="crumbs"><a href="{url(lg)}">{t(lg,'home')}</a> › <a href="{url(lg, FAMILY_SLUG[a['fam']]+'/')}">{esc(M['h1'])}</a> › <span>{esc(A['label'])}</span></nav>
  <h1>{esc(A['title'])}</h1>
  <p class="lead">{esc(A['lead'])}</p>
  {methods}<ol class="steps">{steps}</ol>
  {f'<p class="total">{esc(A["total"])}</p>' if A.get("total") else ""}
  <h2>{esc(A['outro_h'])}</h2>
  <p>{esc(A['outro'])}</p>
  <div class="ctas"><a class="btn red" href="{url(lg, FAMILY_SLUG[a['fam']]+'/')}">{esc(A['cta'])} →</a><a class="btn ghost" href="https://t.me/+380663666886" target="_blank" rel="noopener">{TG_ICO}<span>{t(lg,'cta_tg')}</span></a></div>
</article>
<section class="catalog wrap"><div class="grid">{"".join(card(c, lg) for c in cs)}</div></section>
</main>
"""
    write(PREFIX[lg] + path + "index.html", head(lg, path, A["title"] + " | True Rides Japan", A["desc"], a.get("og", "assets/og.jpg"), ld) + header(lg, path) + body + footer(lg) + SCRIPT)


def page_article_free(lg, a):
    """Статья со свободным текстом: тело — готовый HTML из _src/articles/<slug>.<lg>.html."""
    A = a[lg]
    ui = ui_lang(lg)
    path = art_path(a)
    body_html = open(os.path.join(SRC, "articles", f"{a['slug']}.{lg}.html"), encoding="utf-8").read()
    B = X["blog"][ui]
    crumbs = [(t(ui, "home"), abs_url(ui)), (B["h1"], abs_url(ui, "blog/")), (A["label"], abs_url(lg, path))]
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": A["title"], "description": A["desc"], "inLanguage": HREFLANG[lg],
           "datePublished": a["date"], "dateModified": a.get("updated", a["date"]), "author": {"@type": "Organization", "name": "True Rides Japan", "url": SITE},
           "publisher": {"@type": "Organization", "name": "True Rides Japan", "logo": {"@type": "ImageObject", "url": SITE + "/assets/logo.png"}},
           "image": SITE + "/" + a.get("og", "assets/og.jpg"), "mainEntityOfPage": abs_url(lg, path)}, crumbs_ld(crumbs)]
    if A.get("faq"):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": HREFLANG[lg],
                   "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in A["faq"]]})
    body = f"""<main>
<article class="wrap article free" lang="{HREFLANG[lg]}">
  <nav class="crumbs"><a href="{url(ui)}">{t(ui,'home')}</a> › <a href="{url(ui, 'blog/')}">{esc(B['h1'])}</a> › <span>{esc(A['label'])}</span></nav>
  <h1>{esc(A['title'])}</h1>
{body_html}
</article>
</main>
"""
    write(PREFIX[lg] + path + "index.html", head(lg, path, A["title"] + " | True Rides Japan", A["desc"], a.get("og", "assets/og.jpg"), ld, alts=alangs(a))
          + header(ui, path, langs_list=alangs(a), cur=lg) + body + footer(ui) + SCRIPT)


# ---------- sitemap / robots ----------
def page_404():
    """404.html в корне: Cloudflare Pages отдаёт его с кодом 404 на любой несуществующий адрес."""
    lg = "ru"
    body = f"""<main><section class="wrap pagehead" style="padding:80px 0 120px">
  <p class="eyebrow">404</p>
  <h1>Страница не найдена</h1>
  <p class="lead">Такой страницы нет — возможно, машина уже продана или адрес набран с ошибкой.</p>
  <p class="lead" lang="uk">Сторінку не знайдено. <a href="/ua/">Перейти на головну</a></p>
  <p class="lead" lang="en">Page not found. <a href="/en/">Go to the home page</a></p>
  <p><a class="btn red" href="/#catalog">Смотреть машины</a></p>
</section></main>
"""
    h = head(lg, "", "Страница не найдена — True Rides Japan", "Страница не найдена.", "assets/og.jpg", {"@context": "https://schema.org", "@type": "WebPage", "name": "404"}, alts=False)
    h = h.replace('<link rel="canonical"', '<meta name="robots" content="noindex">\n<link rel="canonical"', 1)
    # Посетитель ошибку не видит: сразу уходит в каталог на главной (для поисковиков код ответа остаётся 404).
    h = h.replace('<meta name="robots"', '<meta http-equiv="refresh" content="0; url=/#catalog">\n<script>location.replace("/#catalog")</script>\n<meta name="robots"', 1)
    write("404.html", h + header(lg, "") + body + footer(lg) + SCRIPT)


def sitemap():
    paths = [(p, LANGS) for p in [""] + [FAMILY_SLUG[f] + "/" for f in ["minivan", "note"]] + ["blog/"]] + [(art_path(a), alangs(a)) for a in ARTICLES] + [(car_slug(c), LANGS) for c in CARS]
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    n = 0
    for p, lgs in paths:
        for lg in lgs:
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{HREFLANG[l2]}" href="{abs_url(l2, p)}"/>' for l2 in lgs)
            out.append(f"  <url><loc>{abs_url(lg, p)}</loc><lastmod>{TODAY}</lastmod>{alts}</url>")
            n += 1
    out.append("</urlset>")
    write("sitemap.xml", "\n".join(out) + "\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /_src/\n\nSitemap: {SITE}/sitemap.xml\n")
    if SEO.get("indexnow"):
        write(SEO["indexnow"] + ".txt", SEO["indexnow"])
    write("llms.txt", llms_txt())
    if SEO.get("yandex"):
        write(f"yandex_{SEO['yandex']}.html", f'<html>\n    <head>\n        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n    </head>\n    <body>Verification: {SEO["yandex"]}</body>\n</html>\n')
    return n


def llms_txt():
    """Краткое описание сайта для ИИ-ассистентов (ChatGPT, Perplexity и т.п.)."""
    arts = "\n".join(f"- [{a[lg]['title']}]({abs_url(lg, art_path(a))})" for a in ARTICLES for lg in alangs(a))
    return f"""# True Rides Japan

> True Rides Japan (trueridesjapan.com) — покупка автомобилей на японских аукционах под заказ и продажа машин в пути: Япония → порт Поти (Грузия) → переделка руля с правого на левый в Грузии → выдача в Грузии, Украине (Одесса, Киев) или для клиентов из Армении. Основные модели: Toyota Alphard / Vellfire, Nissan Note e-Power. Владелец — Виталий, Рустави, Грузия.

## Услуга для Армении
- Покупка авто в Японии под ключ: фиксированная услуга $550, клиент оформляется получателем, переделка руля в Грузии с гарантией 1 год, которая действует в Армении (сервис под Ереваном). Поэтапная оплата, залог $200.
- Контакт: Telegram https://t.me/VTruerides, чат https://t.me/truerides_chat

## Разделы
- [Каталог машин]({SITE}/)
- [Toyota Alphard / Vellfire]({abs_url("ru", FAMILY_SLUG["minivan"] + "/")})
- [Nissan Note e-Power]({abs_url("ru", FAMILY_SLUG["note"] + "/")})
- [Статьи]({abs_url("ru", "blog/")})

## Статьи
{arts}

## Контакты
- Telegram / Viber / WhatsApp: +380663666886
- Чат: https://t.me/truerides_chat
- Instagram: https://www.instagram.com/true_rides/
"""


def clean():
    for d in ["ua", "en", "hy", "cars", "blog"] + list(FAMILY_SLUG.values()):
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            shutil.rmtree(p)


if __name__ == "__main__":
    clean()
    for lg in LANGS:
        page_home(lg)
        for f in ["minivan", "note"]:
            page_model(lg, f)
        for c in CARS:
            page_car(lg, c)
        for a in ARTICLES:
            if lg in alangs(a):
                (page_article_free if "free" in a else page_article)(lg, a)
        page_blog(lg)
    for a in ARTICLES:
        for lg in alangs(a):
            if lg not in LANGS:
                page_article_free(lg, a)
    page_404()
    n = sitemap()
    print(f"OK: {n} страниц")
