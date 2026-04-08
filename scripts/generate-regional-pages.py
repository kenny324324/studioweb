#!/usr/bin/env python3
"""
從 toilets.json 產生地區頁面 (縣市 + 區域)，用於長尾 SEO。
同時自動重建 sitemap.xml。

用法: python3 scripts/generate-regional-pages.py
"""

import json
import re
import os
import shutil
from collections import defaultdict
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, '..')
DATA_PATH = os.path.join(ROOT_DIR, 'assets', 'findtoilet', 'toilets.json')
AREA_DIR = os.path.join(ROOT_DIR, 'findtoilet', 'area')
SITEMAP_PATH = os.path.join(ROOT_DIR, 'sitemap.xml')
BASE_URL = 'https://kenny324324.github.io/studioweb'
TODAY = date.today().isoformat()

# 臺 → 台 正規化
def normalize_city(name):
    return name.replace('臺', '台')

# 縣市 → slug 對照
CITY_SLUGS = {
    '台北市': 'taipei', '新北市': 'newtaipei', '桃園市': 'taoyuan',
    '台中市': 'taichung', '台南市': 'tainan', '高雄市': 'kaohsiung',
    '基隆市': 'keelung', '新竹市': 'hsinchu-city', '新竹縣': 'hsinchu',
    '苗栗縣': 'miaoli', '彰化縣': 'changhua', '南投縣': 'nantou',
    '雲林縣': 'yunlin', '嘉義市': 'chiayi-city', '嘉義縣': 'chiayi',
    '屏東縣': 'pingtung', '宜蘭縣': 'yilan', '花蓮縣': 'hualien',
    '台東縣': 'taitung', '澎湖縣': 'penghu', '金門縣': 'kinmen',
    '連江縣': 'lienchiang',
}

# 區域 slug (簡易拼音，用常見翻譯)
def district_slug(district_name):
    """將區域名稱轉為 URL slug"""
    # 去掉鄉鎮市區後綴
    base = re.sub(r'[鄉鎮市區]$', '', district_name)
    # 用 pinyin-like slug (簡化處理：直接用區域名稱作為 slug)
    return base.lower()


GRADE_LABELS = {1: '特優級', 2: '優等級', 3: '普通級', 4: '不合格'}
CATEGORY_ICONS = {
    '交通': 'directions_bus', '商業': 'store', '文教': 'school',
    '公園': 'park', '景點': 'landscape', '社福': 'groups',
    '政府': 'account_balance', '宗教': 'temple_buddhist',
    '休閒': 'sports_esports', '其他': 'more_horiz',
}


def extract_district(address):
    """從地址提取區域名稱"""
    m = re.match(r'^.{3}(.{2,3}[鄉鎮市區])', address)
    if m:
        return m.group(1)
    return None


def group_data(data):
    """將資料依縣市 → 區域分群"""
    cities = defaultdict(lambda: defaultdict(list))

    for d in data:
        addr = d.get('a', '')
        if len(addr) < 3:
            continue
        city = normalize_city(addr[:3])
        if city not in CITY_SLUGS:
            continue
        district = extract_district(addr)
        if district:
            cities[city][district].append(d)
        else:
            cities[city]['其他'].append(d)

    return cities


def category_stats(toilets):
    """統計各類別廁所數量"""
    cats = defaultdict(int)
    for t in toilets:
        c = t.get('c', '其他')
        cats[c] += 1
    return dict(sorted(cats.items(), key=lambda x: -x[1]))


def grade_stats(toilets):
    """統計評等分布"""
    grades = defaultdict(int)
    for t in toilets:
        g = t.get('g', 0)
        if g in GRADE_LABELS:
            grades[GRADE_LABELS[g]] += 1
    return dict(sorted(grades.items()))


def avg_coords(toilets):
    """計算平均座標"""
    if not toilets:
        return 23.7, 120.96
    lat = sum(t['lt'] for t in toilets) / len(toilets)
    lng = sum(t['lg'] for t in toilets) / len(toilets)
    return round(lat, 4), round(lng, 4)


def generate_city_page(city, districts, city_slug):
    """產生縣市頁面 HTML"""
    total = sum(len(ts) for ts in districts.values())
    district_list = sorted(districts.items(), key=lambda x: -len(x[1]))
    cats = category_stats([t for ts in districts.values() for t in ts])
    lat, lng = avg_coords([t for ts in districts.values() for t in ts])

    district_links = '\n'.join(
        f'                <a href="{district_slug(d)}/" class="district-card">'
        f'<span class="district-name">{d}</span>'
        f'<span class="district-count">{len(ts)} 間</span></a>'
        for d, ts in district_list if d != '其他'
    )

    cat_tags = '\n'.join(
        f'                <span class="cat-tag"><span class="mi">{CATEGORY_ICONS.get(c, "wc")}</span>{c} ({n})</span>'
        for c, n in cats.items()
    )

    return f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{city}公共廁所地圖 — 找廁所！Find Toilet</title>
    <meta name="description" content="查詢{city}所有公共廁所位置，共 {total} 間。涵蓋{'、'.join(d for d, _ in district_list[:5])}等地區，支援 GPS 定位、評等查看。">
    <link rel="canonical" href="{BASE_URL}/findtoilet/area/{city_slug}/">

    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="{city}公共廁所地圖 — 找廁所！">
    <meta property="og:description" content="查詢{city}所有公共廁所，共 {total} 間公廁。">
    <meta property="og:url" content="{BASE_URL}/findtoilet/area/{city_slug}/">
    <meta property="og:site_name" content="Kenny Studio">
    <meta property="og:locale" content="zh_TW">
    <meta property="og:image" content="{BASE_URL}/assets/findtoilet/og-image.png">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{city}公共廁所地圖 — 找廁所！">
    <meta name="twitter:description" content="查詢{city}所有公共廁所，共 {total} 間公廁。">
    <meta name="twitter:image" content="{BASE_URL}/assets/findtoilet/og-image.png">

    <meta name="robots" content="index, follow">
    <link rel="alternate" hreflang="zh-Hant" href="{BASE_URL}/findtoilet/area/{city_slug}/">

    <!-- JSON-LD -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "{city}公共廁所",
        "description": "{city}所有公共廁所位置，共 {total} 間",
        "numberOfItems": {total},
        "itemListElement": [
            {', '.join(f'{{"@type": "ListItem", "position": {i+1}, "name": "{d}", "url": "{BASE_URL}/findtoilet/area/{city_slug}/{district_slug(d)}/"}}' for i, (d, _) in enumerate(district_list) if d != '其他')}
        ]
    }}
    </script>
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{ "@type": "ListItem", "position": 1, "name": "找廁所！", "item": "{BASE_URL}/findtoilet/" }},
            {{ "@type": "ListItem", "position": 2, "name": "地區查詢", "item": "{BASE_URL}/findtoilet/area/" }},
            {{ "@type": "ListItem", "position": 3, "name": "{city}", "item": "{BASE_URL}/findtoilet/area/{city_slug}/" }}
        ]
    }}
    </script>

    <!-- Google AdSense -->
    <!-- TODO: 將 ca-pub-9616816354780961 替換為你的 AdSense Publisher ID -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9616816354780961" crossorigin="anonymous"></script>

    <link rel="icon" type="image/png" href="{BASE_URL}/assets/findtoilet/icon.png">

    <!-- Material Symbols -->
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0&display=swap">

    <style>
        :root {{ --blue: #3D87F5; --green: #34C759; --orange: #FA9E47; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #1a1a1a; background: #f8f9fa; }}
        .mi {{ font-family: 'Material Symbols Rounded'; font-size: 20px; vertical-align: -4px; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 0 1.25rem; }}
        nav {{ padding: 1rem 0; font-size: 0.85rem; color: #888; }}
        nav a {{ color: var(--blue); text-decoration: none; }}
        nav a:hover {{ text-decoration: underline; }}
        .hero {{ padding: 2rem 0 1.5rem; }}
        .hero h1 {{ font-size: 1.75rem; font-weight: 700; margin-bottom: 0.5rem; }}
        .hero p {{ color: #555; font-size: 1rem; }}
        .stats {{ display: flex; gap: 1.5rem; margin: 1.5rem 0; flex-wrap: wrap; }}
        .stat {{ background: #fff; padding: 1rem 1.25rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        .stat-number {{ font-size: 1.5rem; font-weight: 700; color: var(--blue); }}
        .stat-label {{ font-size: 0.8rem; color: #888; }}
        .section {{ margin: 2rem 0; }}
        .section h2 {{ font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem; }}
        .district-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.75rem; }}
        .district-card {{ display: flex; justify-content: space-between; align-items: center; padding: 0.875rem 1rem; background: #fff; border-radius: 10px; text-decoration: none; color: #1a1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.06); transition: box-shadow 0.2s; }}
        .district-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.12); }}
        .district-name {{ font-weight: 500; }}
        .district-count {{ font-size: 0.8rem; color: #888; }}
        .cat-tags {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
        .cat-tag {{ display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.4rem 0.75rem; background: #fff; border-radius: 8px; font-size: 0.85rem; color: #555; box-shadow: 0 1px 2px rgba(0,0,0,0.06); }}
        .cat-tag .mi {{ font-size: 18px; color: var(--blue); }}
        .cta-section {{ text-align: center; padding: 2.5rem 1rem; margin: 2rem 0; background: #fff; border-radius: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
        .cta-section h2 {{ margin-bottom: 0.5rem; }}
        .cta-section p {{ color: #555; margin-bottom: 1.25rem; }}
        .cta-btn {{ display: inline-block; padding: 0.75rem 1.5rem; background: var(--blue); color: #fff; text-decoration: none; border-radius: 10px; font-weight: 600; }}
        .cta-btn:hover {{ opacity: 0.9; }}
        .map-link {{ display: inline-flex; align-items: center; gap: 0.3rem; color: var(--blue); text-decoration: none; font-weight: 500; margin-top: 1rem; }}
        .map-link:hover {{ text-decoration: underline; }}
        .ad-slot {{ margin: 1.5rem 0; min-height: 90px; }}
        footer {{ padding: 2rem 0; margin-top: 2rem; border-top: 1px solid #e5e5e5; text-align: center; font-size: 0.8rem; color: #888; }}
        footer a {{ color: var(--blue); text-decoration: none; }}
        .app-banner {{ background: #fff; padding: 0.6rem 1rem; display: flex; align-items: center; gap: 0.75rem; border-bottom: 1px solid #eee; }}
        .app-banner img {{ width: 36px; height: 36px; border-radius: 8px; }}
        .app-banner-text {{ flex: 1; }}
        .app-banner-name {{ font-weight: 600; font-size: 0.85rem; }}
        .app-banner-desc {{ font-size: 0.7rem; color: #888; }}
        .app-banner-btn {{ padding: 0.35rem 0.75rem; background: var(--blue); color: #fff; border-radius: 999px; font-size: 0.75rem; font-weight: 600; text-decoration: none; }}
    </style>
</head>
<body>
    <!-- App Banner -->
    <div class="app-banner">
        <img src="{BASE_URL}/assets/findtoilet/icon.png" alt="找廁所 App">
        <div class="app-banner-text">
            <div class="app-banner-name">找廁所！Find Toilet</div>
            <div class="app-banner-desc">在 App Store 免費下載</div>
        </div>
        <a href="https://apps.apple.com/app/id6752564383" class="app-banner-btn">下載</a>
    </div>

    <div class="container">
        <nav>
            <a href="{BASE_URL}/findtoilet/">找廁所！</a>
            <span> / </span>
            <a href="{BASE_URL}/findtoilet/area/">地區查詢</a>
            <span> / </span>
            <span>{city}</span>
        </nav>

        <div class="hero">
            <h1>{city}公共廁所</h1>
            <p>查詢{city}所有公共廁所位置，涵蓋{'、'.join(d for d, _ in district_list[:5])}等地區。</p>
            <a href="{BASE_URL}/findtoilet/map/?lat={lat}&lng={lng}&zoom=12" class="map-link">
                <span class="mi">map</span> 在地圖上查看{city}公廁
            </a>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-number">{total}</div>
                <div class="stat-label">間公共廁所</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len([d for d in district_list if d[0] != '其他'])}</div>
                <div class="stat-label">個地區</div>
            </div>
        </div>

        <!-- Ad -->
        <div class="ad-slot">
            <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-9616816354780961" data-ad-slot="AREA_SLOT_ID" data-ad-format="auto" data-full-width-responsive="true"></ins>
            <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        </div>

        <div class="section">
            <h2><span class="mi">location_city</span> 各地區公廁</h2>
            <div class="district-grid">
{district_links}
            </div>
        </div>

        <div class="section">
            <h2><span class="mi">category</span> 場所類型</h2>
            <div class="cat-tags">
{cat_tags}
            </div>
        </div>

        <div class="cta-section">
            <h2>下載找廁所 App</h2>
            <p>GPS 即時定位附近公廁，查看評等與無障礙設施</p>
            <a href="https://apps.apple.com/app/id6752564383" class="cta-btn">免費下載 iOS App</a>
        </div>

        <footer>
            <p>&copy; {date.today().year} <a href="{BASE_URL}/">Kenny Studio</a>. 資料來源：環境部公開資料。</p>
        </footer>
    </div>
</body>
</html>'''


def generate_district_page(city, city_slug, district, toilets):
    """產生區域頁面 HTML"""
    total = len(toilets)
    d_slug = district_slug(district)
    cats = category_stats(toilets)
    grades = grade_stats(toilets)
    lat, lng = avg_coords(toilets)

    cat_tags = '\n'.join(
        f'                <span class="cat-tag"><span class="mi">{CATEGORY_ICONS.get(c, "wc")}</span>{c} ({n})</span>'
        for c, n in cats.items()
    )

    # Top 10 toilets by grade
    top_toilets = sorted(toilets, key=lambda t: (t.get('g', 99), -t.get('tc', 1)))[:10]
    toilet_items = '\n'.join(
        f'                <div class="toilet-item">'
        f'<div class="toilet-name">{t["n"]}</div>'
        f'<div class="toilet-meta">{GRADE_LABELS.get(t.get("g", 0), "")} · {t.get("c", "")}</div>'
        f'</div>'
        for t in top_toilets
    )

    return f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{city}{district}公共廁所 — 找廁所！Find Toilet</title>
    <meta name="description" content="查詢{city}{district}的公共廁所位置，共 {total} 間公廁。含評等、無障礙設施資訊，GPS 定位一鍵導航。">
    <link rel="canonical" href="{BASE_URL}/findtoilet/area/{city_slug}/{d_slug}/">

    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="{city}{district}公共廁所 — 找廁所！">
    <meta property="og:description" content="查詢{city}{district}公共廁所，共 {total} 間公廁。">
    <meta property="og:url" content="{BASE_URL}/findtoilet/area/{city_slug}/{d_slug}/">
    <meta property="og:site_name" content="Kenny Studio">
    <meta property="og:locale" content="zh_TW">
    <meta property="og:image" content="{BASE_URL}/assets/findtoilet/og-image.png">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{city}{district}公共廁所 — 找廁所！">
    <meta name="twitter:description" content="查詢{city}{district}公共廁所，共 {total} 間公廁。">
    <meta name="twitter:image" content="{BASE_URL}/assets/findtoilet/og-image.png">

    <meta name="robots" content="index, follow">

    <!-- JSON-LD -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "{city}{district}公共廁所",
        "description": "{city}{district}公共廁所位置，共 {total} 間",
        "numberOfItems": {total}
    }}
    </script>
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{ "@type": "ListItem", "position": 1, "name": "找廁所！", "item": "{BASE_URL}/findtoilet/" }},
            {{ "@type": "ListItem", "position": 2, "name": "地區查詢", "item": "{BASE_URL}/findtoilet/area/" }},
            {{ "@type": "ListItem", "position": 3, "name": "{city}", "item": "{BASE_URL}/findtoilet/area/{city_slug}/" }},
            {{ "@type": "ListItem", "position": 4, "name": "{district}", "item": "{BASE_URL}/findtoilet/area/{city_slug}/{d_slug}/" }}
        ]
    }}
    </script>

    <!-- Google AdSense -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9616816354780961" crossorigin="anonymous"></script>

    <link rel="icon" type="image/png" href="{BASE_URL}/assets/findtoilet/icon.png">

    <!-- Material Symbols -->
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0&display=swap">

    <style>
        :root {{ --blue: #3D87F5; --green: #34C759; --orange: #FA9E47; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #1a1a1a; background: #f8f9fa; }}
        .mi {{ font-family: 'Material Symbols Rounded'; font-size: 20px; vertical-align: -4px; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 0 1.25rem; }}
        nav {{ padding: 1rem 0; font-size: 0.85rem; color: #888; }}
        nav a {{ color: var(--blue); text-decoration: none; }}
        nav a:hover {{ text-decoration: underline; }}
        .hero {{ padding: 2rem 0 1.5rem; }}
        .hero h1 {{ font-size: 1.75rem; font-weight: 700; margin-bottom: 0.5rem; }}
        .hero p {{ color: #555; font-size: 1rem; }}
        .stats {{ display: flex; gap: 1.5rem; margin: 1.5rem 0; flex-wrap: wrap; }}
        .stat {{ background: #fff; padding: 1rem 1.25rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        .stat-number {{ font-size: 1.5rem; font-weight: 700; color: var(--blue); }}
        .stat-label {{ font-size: 0.8rem; color: #888; }}
        .section {{ margin: 2rem 0; }}
        .section h2 {{ font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem; }}
        .cat-tags {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
        .cat-tag {{ display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.4rem 0.75rem; background: #fff; border-radius: 8px; font-size: 0.85rem; color: #555; box-shadow: 0 1px 2px rgba(0,0,0,0.06); }}
        .cat-tag .mi {{ font-size: 18px; color: var(--blue); }}
        .toilet-item {{ padding: 0.875rem 1rem; background: #fff; border-radius: 10px; margin-bottom: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
        .toilet-name {{ font-weight: 500; }}
        .toilet-meta {{ font-size: 0.8rem; color: #888; margin-top: 0.25rem; }}
        .map-link {{ display: inline-flex; align-items: center; gap: 0.3rem; color: var(--blue); text-decoration: none; font-weight: 500; margin-top: 1rem; }}
        .map-link:hover {{ text-decoration: underline; }}
        .cta-section {{ text-align: center; padding: 2.5rem 1rem; margin: 2rem 0; background: #fff; border-radius: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
        .cta-section h2 {{ margin-bottom: 0.5rem; }}
        .cta-section p {{ color: #555; margin-bottom: 1.25rem; }}
        .cta-btn {{ display: inline-block; padding: 0.75rem 1.5rem; background: var(--blue); color: #fff; text-decoration: none; border-radius: 10px; font-weight: 600; }}
        .ad-slot {{ margin: 1.5rem 0; min-height: 90px; }}
        footer {{ padding: 2rem 0; margin-top: 2rem; border-top: 1px solid #e5e5e5; text-align: center; font-size: 0.8rem; color: #888; }}
        footer a {{ color: var(--blue); text-decoration: none; }}
        .app-banner {{ background: #fff; padding: 0.6rem 1rem; display: flex; align-items: center; gap: 0.75rem; border-bottom: 1px solid #eee; }}
        .app-banner img {{ width: 36px; height: 36px; border-radius: 8px; }}
        .app-banner-text {{ flex: 1; }}
        .app-banner-name {{ font-weight: 600; font-size: 0.85rem; }}
        .app-banner-desc {{ font-size: 0.7rem; color: #888; }}
        .app-banner-btn {{ padding: 0.35rem 0.75rem; background: var(--blue); color: #fff; border-radius: 999px; font-size: 0.75rem; font-weight: 600; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="app-banner">
        <img src="{BASE_URL}/assets/findtoilet/icon.png" alt="找廁所 App">
        <div class="app-banner-text">
            <div class="app-banner-name">找廁所！Find Toilet</div>
            <div class="app-banner-desc">在 App Store 免費下載</div>
        </div>
        <a href="https://apps.apple.com/app/id6752564383" class="app-banner-btn">下載</a>
    </div>

    <div class="container">
        <nav>
            <a href="{BASE_URL}/findtoilet/">找廁所！</a>
            <span> / </span>
            <a href="{BASE_URL}/findtoilet/area/">地區查詢</a>
            <span> / </span>
            <a href="{BASE_URL}/findtoilet/area/{city_slug}/">{city}</a>
            <span> / </span>
            <span>{district}</span>
        </nav>

        <div class="hero">
            <h1>{city}{district}公共廁所</h1>
            <p>{city}{district}共有 {total} 間公共廁所。</p>
            <a href="{BASE_URL}/findtoilet/map/?lat={lat}&lng={lng}&zoom=14" class="map-link">
                <span class="mi">map</span> 在地圖上查看{district}公廁
            </a>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-number">{total}</div>
                <div class="stat-label">間公共廁所</div>
            </div>
        </div>

        <div class="section">
            <h2><span class="mi">category</span> 場所類型</h2>
            <div class="cat-tags">
{cat_tags}
            </div>
        </div>

        <!-- Ad -->
        <div class="ad-slot">
            <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-9616816354780961" data-ad-slot="AREA_SLOT_ID" data-ad-format="auto" data-full-width-responsive="true"></ins>
            <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        </div>

        <div class="section">
            <h2><span class="mi">wc</span> 主要公廁</h2>
{toilet_items}
        </div>

        <div class="cta-section">
            <h2>下載找廁所 App</h2>
            <p>GPS 即時定位附近公廁，查看評等與無障礙設施</p>
            <a href="https://apps.apple.com/app/id6752564383" class="cta-btn">免費下載 iOS App</a>
        </div>

        <footer>
            <p>&copy; {date.today().year} <a href="{BASE_URL}/">Kenny Studio</a>. 資料來源：環境部公開資料。</p>
        </footer>
    </div>
</body>
</html>'''


def generate_index_page(cities_data):
    """產生地區索引頁面"""
    sorted_cities = sorted(cities_data.items(), key=lambda x: -sum(len(ts) for ts in x[1].values()))
    total = sum(sum(len(ts) for ts in ds.values()) for _, ds in sorted_cities)

    city_links = '\n'.join(
        f'                <a href="{CITY_SLUGS[c]}/" class="district-card">'
        f'<span class="district-name">{c}</span>'
        f'<span class="district-count">{sum(len(ts) for ts in ds.values())} 間</span></a>'
        for c, ds in sorted_cities if c in CITY_SLUGS
    )

    return f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>全台灣公共廁所地區查詢 — 找廁所！Find Toilet</title>
    <meta name="description" content="依縣市查詢全台灣公共廁所位置，共 {total} 間公廁。台北、台中、高雄、台南等各縣市公廁資訊一次查詢。">
    <link rel="canonical" href="{BASE_URL}/findtoilet/area/">

    <meta property="og:type" content="website">
    <meta property="og:title" content="全台灣公共廁所地區查詢 — 找廁所！">
    <meta property="og:description" content="依縣市查詢全台灣 {total} 間公共廁所。">
    <meta property="og:url" content="{BASE_URL}/findtoilet/area/">
    <meta property="og:site_name" content="Kenny Studio">
    <meta property="og:locale" content="zh_TW">
    <meta property="og:image" content="{BASE_URL}/assets/findtoilet/og-image.png">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="全台灣公共廁所地區查詢 — 找廁所！">
    <meta name="twitter:description" content="依縣市查詢全台灣 {total} 間公共廁所。">
    <meta name="twitter:image" content="{BASE_URL}/assets/findtoilet/og-image.png">

    <meta name="robots" content="index, follow">

    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "全台灣公共廁所地區查詢",
        "numberOfItems": {len(sorted_cities)},
        "itemListElement": [
            {', '.join(f'{{"@type": "ListItem", "position": {i+1}, "name": "{c}", "url": "{BASE_URL}/findtoilet/area/{CITY_SLUGS[c]}/"}}' for i, (c, _) in enumerate(sorted_cities) if c in CITY_SLUGS)}
        ]
    }}
    </script>
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{ "@type": "ListItem", "position": 1, "name": "找廁所！", "item": "{BASE_URL}/findtoilet/" }},
            {{ "@type": "ListItem", "position": 2, "name": "地區查詢", "item": "{BASE_URL}/findtoilet/area/" }}
        ]
    }}
    </script>

    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9616816354780961" crossorigin="anonymous"></script>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0&display=swap">

    <style>
        :root {{ --blue: #3D87F5; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #1a1a1a; background: #f8f9fa; }}
        .mi {{ font-family: 'Material Symbols Rounded'; font-size: 20px; vertical-align: -4px; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 0 1.25rem; }}
        nav {{ padding: 1rem 0; font-size: 0.85rem; color: #888; }}
        nav a {{ color: var(--blue); text-decoration: none; }}
        .hero {{ padding: 2rem 0 1.5rem; }}
        .hero h1 {{ font-size: 1.75rem; font-weight: 700; margin-bottom: 0.5rem; }}
        .hero p {{ color: #555; }}
        .district-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.75rem; margin: 1.5rem 0; }}
        .district-card {{ display: flex; justify-content: space-between; align-items: center; padding: 0.875rem 1rem; background: #fff; border-radius: 10px; text-decoration: none; color: #1a1a1a; box-shadow: 0 1px 3px rgba(0,0,0,0.06); transition: box-shadow 0.2s; }}
        .district-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.12); }}
        .district-name {{ font-weight: 500; }}
        .district-count {{ font-size: 0.8rem; color: #888; }}
        .ad-slot {{ margin: 1.5rem 0; min-height: 90px; }}
        footer {{ padding: 2rem 0; margin-top: 2rem; border-top: 1px solid #e5e5e5; text-align: center; font-size: 0.8rem; color: #888; }}
        footer a {{ color: var(--blue); text-decoration: none; }}
        .app-banner {{ background: #fff; padding: 0.6rem 1rem; display: flex; align-items: center; gap: 0.75rem; border-bottom: 1px solid #eee; }}
        .app-banner img {{ width: 36px; height: 36px; border-radius: 8px; }}
        .app-banner-text {{ flex: 1; }}
        .app-banner-name {{ font-weight: 600; font-size: 0.85rem; }}
        .app-banner-desc {{ font-size: 0.7rem; color: #888; }}
        .app-banner-btn {{ padding: 0.35rem 0.75rem; background: var(--blue); color: #fff; border-radius: 999px; font-size: 0.75rem; font-weight: 600; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="app-banner">
        <img src="{BASE_URL}/assets/findtoilet/icon.png" alt="找廁所 App">
        <div class="app-banner-text">
            <div class="app-banner-name">找廁所！Find Toilet</div>
            <div class="app-banner-desc">在 App Store 免費下載</div>
        </div>
        <a href="https://apps.apple.com/app/id6752564383" class="app-banner-btn">下載</a>
    </div>

    <div class="container">
        <nav>
            <a href="{BASE_URL}/findtoilet/">找廁所！</a>
            <span> / </span>
            <span>地區查詢</span>
        </nav>

        <div class="hero">
            <h1>全台灣公共廁所地區查詢</h1>
            <p>選擇縣市查詢當地公共廁所位置，全台共 {total} 間公廁資料。</p>
        </div>

        <div class="district-grid">
{city_links}
        </div>

        <div class="ad-slot">
            <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-9616816354780961" data-ad-slot="AREA_SLOT_ID" data-ad-format="auto" data-full-width-responsive="true"></ins>
            <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        </div>

        <footer>
            <p>&copy; {date.today().year} <a href="{BASE_URL}/">Kenny Studio</a>. 資料來源：環境部公開資料。</p>
        </footer>
    </div>
</body>
</html>'''


def generate_sitemap(cities_data, existing_urls=None):
    """產生 sitemap.xml"""
    urls = []

    # Existing core pages
    core_pages = [
        (f'{BASE_URL}/', TODAY, None, '0.6'),
        (f'{BASE_URL}/findtoilet/map/', TODAY, 'weekly', '1.0'),
        (f'{BASE_URL}/findtoilet/', TODAY, None, '0.7'),
        (f'{BASE_URL}/packagetracker/', '2026-03-30', None, '0.8'),
    ]
    for loc, lastmod, freq, pri in core_pages:
        entry = f'    <url>\n        <loc>{loc}</loc>\n        <lastmod>{lastmod}</lastmod>'
        if freq:
            entry += f'\n        <changefreq>{freq}</changefreq>'
        entry += f'\n        <priority>{pri}</priority>\n    </url>'
        urls.append(entry)

    # Area index
    urls.append(f'    <url>\n        <loc>{BASE_URL}/findtoilet/area/</loc>\n        <lastmod>{TODAY}</lastmod>\n        <changefreq>monthly</changefreq>\n        <priority>0.6</priority>\n    </url>')

    # City pages
    for city, districts in sorted(cities_data.items()):
        if city not in CITY_SLUGS:
            continue
        slug = CITY_SLUGS[city]
        urls.append(f'    <url>\n        <loc>{BASE_URL}/findtoilet/area/{slug}/</loc>\n        <lastmod>{TODAY}</lastmod>\n        <changefreq>monthly</changefreq>\n        <priority>0.6</priority>\n    </url>')

        # District pages
        for district in sorted(districts.keys()):
            if district == '其他':
                continue
            d_slug = district_slug(district)
            urls.append(f'    <url>\n        <loc>{BASE_URL}/findtoilet/area/{slug}/{d_slug}/</loc>\n        <lastmod>{TODAY}</lastmod>\n        <changefreq>monthly</changefreq>\n        <priority>0.5</priority>\n    </url>')

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
'''


def main():
    # Load data
    with open(DATA_PATH, 'r') as f:
        data = json.load(f)
    print(f'Loaded {len(data)} toilets')

    # Group by city and district
    cities_data = group_data(data)
    print(f'Cities: {len(cities_data)}')

    # Clean output directory
    if os.path.exists(AREA_DIR):
        shutil.rmtree(AREA_DIR)
    os.makedirs(AREA_DIR, exist_ok=True)

    # Generate index page
    index_html = generate_index_page(cities_data)
    with open(os.path.join(AREA_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print('Generated: area/index.html')

    # Generate city and district pages
    page_count = 1
    for city, districts in cities_data.items():
        if city not in CITY_SLUGS:
            print(f'  Skipping unknown city: {city}')
            continue

        city_slug_val = CITY_SLUGS[city]
        city_dir = os.path.join(AREA_DIR, city_slug_val)
        os.makedirs(city_dir, exist_ok=True)

        # City page
        city_html = generate_city_page(city, districts, city_slug_val)
        with open(os.path.join(city_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(city_html)
        page_count += 1

        # District pages
        for district_name, toilets in districts.items():
            if district_name == '其他' or len(toilets) < 3:
                continue
            d_slug = district_slug(district_name)
            d_dir = os.path.join(city_dir, d_slug)
            os.makedirs(d_dir, exist_ok=True)

            d_html = generate_district_page(city, city_slug_val, district_name, toilets)
            with open(os.path.join(d_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(d_html)
            page_count += 1

    print(f'Generated {page_count} pages')

    # Generate sitemap
    sitemap = generate_sitemap(cities_data)
    with open(SITEMAP_PATH, 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f'Generated: sitemap.xml')


if __name__ == '__main__':
    main()
