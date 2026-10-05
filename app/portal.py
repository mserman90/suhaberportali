import html
import re
from datetime import datetime, timezone
from typing import List, Dict, Any

def clean_html_tags(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    return " ".join(clean.split())

def generate_newspaper_portal_html(items: List[Dict[str, Any]], last_updated: str, rss_url: str, atom_url: str, json_url: str, podcast_info: Dict[str, Any] = None) -> str:
    today_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    
    # Podcast HTML Hazırlığı
    podcast_banner_html = ""
    podcast_sidebar_html = ""
    if podcast_info and podcast_info.get("latest_episode"):
        ep = podcast_info["latest_episode"]
        audio_url = ep.get("audio_url") or podcast_info.get("latest_audio_url")
        podcast_rss = podcast_info.get("podcast_rss_url") or f"{rss_url.rsplit('/', 1)[0]}/podcast.xml"
        ep_title = html.escape(ep.get("title", "Günlük Sesli Bülten"))
        ep_desc = html.escape(ep.get("description", ""))
        
        podcast_banner_html = f"""
        <section class="podcast-banner-card">
            <div class="podcast-banner-header">
                <div class="podcast-badge-group">
                    <span class="podcast-pill">🎙️ GÜNLÜK SESLİ BÜLTEN &bull; PODCAST</span>
                    <span class="podcast-time-pill">⏰ Her Gün 10:00'da Yayında</span>
                </div>
                <div class="podcast-rss-quick">
                    <span class="podcast-rss-label">Sabit Podcast RSS:</span>
                    <code id="topPodcastRss">{podcast_rss}</code>
                    <button class="btn-copy-podcast-sm" onclick="navigator.clipboard.writeText('{podcast_rss}'); alert('Sabit Podcast RSS linki kopyalandı!');">📋 Kopyala</button>
                </div>
            </div>
            <div class="podcast-banner-body">
                <div class="podcast-info-col">
                    <h3 class="podcast-title">{ep_title}</h3>
                    <p class="podcast-desc">{ep_desc}</p>
                </div>
                <div class="podcast-player-col">
                    <audio controls preload="none" class="portal-audio-player">
                        <source src="{audio_url}" type="audio/mpeg">
                        Tarayıcınız ses etiketini desteklemiyor.
                    </audio>
                    <div class="podcast-player-footer">
                        <a href="{audio_url}" download class="link-download-ep">📥 Bölümü İndir (MP3)</a>
                        <a href="{podcast_rss}" target="_blank" class="link-rss-ep">📡 Podcast XML Akışı &rarr;</a>
                    </div>
                </div>
            </div>
        </section>
        """

        podcast_sidebar_html = f"""
        <div class="sidebar-card sidebar-podcast-box">
            <h4 style="color:#0284c7; font-size:15px; margin-bottom:6px;">🎙️ Sabit Podcast Yayını</h4>
            <p style="font-size:12px; color:var(--ink-muted); margin-bottom:8px;">Apple Podcasts, Spotify veya Pocket Casts uygulamanıza ekleyin:</p>
            <div class="rss-url-display" id="sidebarPodcastUrl">{podcast_rss}</div>
            <button class="btn-copy-rss" style="background:#0284c7;" onclick="navigator.clipboard.writeText('{podcast_rss}'); alert('Sabit Podcast RSS linki kopyalandı!');">
                📋 Podcast RSS Linkini Kopyala
            </button>
            <div style="margin-top:10px; font-size:11px; text-align:center;">
                <a href="{audio_url}" target="_blank" style="color:#0284c7; font-weight:bold;">▶️ Son Bölümü Dinle</a> &bull; 
                <a href="{podcast_rss}" target="_blank" style="color:#0284c7; font-weight:bold;">XML Akışı</a>
            </div>
        </div>
        """
    
    # Manşet Önceliği: Türkiye su haberlerini her zaman en başa (manşete) al
    def turkey_headline_score(x):
        guid = x.get("guid", "")
        source = x.get("source_feed", "")
        title = (x.get("title_tr", "") + " " + x.get("title", "")).lower()
        score = 0
        if guid.startswith("sygm:") or "SYGM" in source or "🏛️" in source:
            score += 2000
        elif guid.startswith("tr_water:") or "🇹🇷" in source:
            score += 1000
        elif bool(x.get("is_turkey") or x.get("category_tr") == "Türkiye"):
            score += 100
        if any(bad in title for bad in ["colorado", "utah", "california", "arizona", "nevada", "mississippi", "salt lake"]):
            score -= 2000
        return score

    # Sort items by date
    raw_sorted = sorted(items, key=lambda x: x.get("pub_date_ts", 0), reverse=True)
    tr_candidates = [it for it in raw_sorted if turkey_headline_score(it) > 0]
    tr_sorted = sorted(tr_candidates, key=lambda x: (turkey_headline_score(x), x.get("pub_date_ts", 0)), reverse=True)
    if tr_sorted:
        turkey_hero = tr_sorted[0]
        items_sorted = [turkey_hero] + [it for it in raw_sorted if it.get("guid") != turkey_hero.get("guid")]
    else:
        items_sorted = raw_sorted
    
    # Hero article (first item)
    hero_item = items_sorted[0] if items_sorted else None
    secondary_items = items_sorted[1:4] if len(items_sorted) > 1 else []
    remaining_items = items_sorted[4:] if len(items_sorted) > 4 else []

    # Fallback water images for articles without image
    default_water_images = [
        "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80", # Agricultural field with water
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&q=80", # River / valley
        "https://images.unsplash.com/photo-1544717305-2782549b5136?w=800&q=80", # Water drop
        "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=800&q=80", # Waves / reservoir
        "https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=800&q=80", # Irrigation canal
    ]

    CATEGORY_SLUGS = {
        "Akademik Yayınlar": "akademik",
        "Tarımsal Sulama": "sulama",
        "Su Teknolojileri": "teknoloji",
        "Su Arıtma & Kalite": "teknoloji",
        "Su Kaynakları": "kaynak",
        "İklim & Kuraklık": "iklim",
        "Su Politikaları": "politika",
    }

    # JSON payload for modal dialogs
    import json
    from app.image_enricher import resolve_article_image
    from app.translator import categorize_article
    portal_data = []
    for idx, it in enumerate(items_sorted):
        img = it.get("image_url")
        if not img or "inoreader.com/camo" in img:
            img = resolve_article_image(it, idx)
        title_tr = it.get("title_tr") or it.get("title")
        summary_tr = it.get("summary_tr") or "Detaylar ilgili bilimsel araştırma ve haber bülteninde yer almaktadır."
        source = it.get("source_feed") or it.get("author") or "Bilimsel Araştırma"
        is_turkey = bool(it.get("is_turkey") or it.get("category_tr") == "Türkiye" or "🇹🇷" in source)
        is_academic = bool(it.get("is_academic") or it.get("guid", "").startswith("academic:") or "🎓" in source)
        cat_raw = it.get("category_tr")
        if not cat_raw or cat_raw == "Türkiye":
            cat_raw = categorize_article(title_tr, summary_tr)
        category = cat_raw or "Su Kaynakları"
        slug = CATEGORY_SLUGS.get(category, "kaynak")
        portal_data.append({
            "id": idx,
            "title_tr": title_tr,
            "title_en": it.get("title", ""),
            "summary_tr": summary_tr,
            "category": category,
            "slug": slug,
            "source": source,
            "author": it.get("author", ""),
            "date": it.get("pub_date", ""),
            "link": it.get("link", ""),
            "image": img,
            "is_turkey": is_turkey,
            "is_academic": is_academic
        })

    json_portal_data = json.dumps(portal_data, ensure_ascii=False)

    # Secondary headline cards
    secondary_html = ""
    for it in portal_data[1:4]:
        if it.get("is_turkey"):
            badge_cls = "news-badge news-badge-turkey"
            badge_lbl = f"🇹🇷 {html.escape(it['category'])}"
        elif it.get("is_academic"):
            badge_cls = "news-badge news-badge-academic"
            badge_lbl = f"🎓 {html.escape(it['category'])}"
        else:
            badge_cls = "news-badge"
            badge_lbl = html.escape(it['category'])
        secondary_html += f"""
        <div class="sub-headline-card" onclick="openArticleModal({it['id']})" data-slug="{it['slug']}">
            <div class="sub-headline-img" style="background-image: url('{html.escape(it['image'])}');">
                <span class="{badge_cls}" onclick="event.stopPropagation(); filterCategory('{it['slug']}')">{badge_lbl}</span>
            </div>
            <div class="sub-headline-content">
                <span class="news-date">📅 {html.escape(it['date'][:16] if it.get('date') else today_str)}</span>
                <h4>{html.escape(it['title_tr'])}</h4>
                <p>{html.escape(it['summary_tr'][:120])}...</p>
            </div>
        </div>
        """

    # Grid article cards (renders all items; items 0-3 hidden in 'all' view since displayed in hero/subheadlines)
    grid_html = ""
    for it in portal_data:
        is_top = it['id'] < 4
        display_style = ' style="display: none;"' if is_top else ''
        search_corpus = clean_html_tags(f"{it['title_tr']} {it['title_en']} {it['summary_tr']} {it['category']} {it['source']}").lower()
        if it.get("is_turkey"):
            badge_cls = "news-badge news-badge-turkey"
            badge_lbl = f"🇹🇷 {html.escape(it['category'])}"
        elif it.get("is_academic"):
            badge_cls = "news-badge news-badge-academic"
            badge_lbl = f"🎓 {html.escape(it['category'])}"
        else:
            badge_cls = "news-badge"
            badge_lbl = html.escape(it['category'])
        is_tr_str = "true" if it.get("is_turkey") else "false"
        is_acad_str = "true" if it.get("is_academic") else "false"
        grid_html += f"""
        <article class="news-grid-card" data-slug="{it['slug']}" data-is-turkey="{is_tr_str}" data-is-academic="{is_acad_str}" data-category="{html.escape(it['category'])}" data-is-top="{'true' if is_top else 'false'}" data-search="{html.escape(search_corpus)}"{display_style}>
            <div class="card-img-wrap" style="background-image: url('{html.escape(it['image'])}');" onclick="openArticleModal({it['id']})">
                <span class="{badge_cls}" onclick="event.stopPropagation(); filterCategory('{it['slug']}')">{badge_lbl}</span>
            </div>
            <div class="card-body">
                <div class="card-meta">
                    <span>📅 {html.escape(it['date'][:16] if it.get('date') else today_str)}</span>
                    <span>🏛️ {html.escape(it['source'][:32])}</span>
                </div>
                <h3 class="card-title" onclick="openArticleModal({it['id']})">
                    {html.escape(it['title_tr'])}
                </h3>
                {f'<h5 class="card-title-en">Orijinal Başlık: {html.escape(it["title_en"])}</h5>' if (it.get('title_en') and it['title_en'] != it['title_tr']) else ''}
                <p class="card-excerpt">
                    {html.escape(it['summary_tr'][:180])}...
                </p>
                <div class="card-action-bar">
                    <button class="btn-read-more" onclick="openArticleModal({it['id']})">Haberi Oku &rarr;</button>
                    <a href="{html.escape(it['link'])}" target="_blank" rel="noopener noreferrer" class="link-original" title="Orijinal Araştırma Sayfası">
                        🔗 Kaynak
                    </a>
                </div>
            </div>
        </article>
        """

    # Ticker items (Continuous scrolling banner - prioritizing Turkey news)
    turkey_ticker_items = [it for it in portal_data if it.get("is_turkey")]
    merged_ticker = []
    # Take top 3 Turkey items first for high visibility
    merged_ticker.extend(turkey_ticker_items[:3])
    # Then fill up to 18 items with top portal items
    for it in portal_data:
        if it not in merged_ticker and len(merged_ticker) < 18:
            merged_ticker.append(it)

    ticker_elements = []
    for it in merged_ticker:
        if it.get("is_turkey"):
            cat_badge = '<span class="ticker-cat-tag ticker-cat-turkey">[🇹🇷 Türkiye]</span>'
        else:
            cat_badge = f'<span class="ticker-cat-tag">[{html.escape(it["category"])}]</span>'
        ticker_elements.append(
            f'<span class="ticker-item" onclick="openArticleModal({it["id"]})">'
            f'<span class="ticker-icon">⚡</span> '
            f'{cat_badge} '
            f'<span class="ticker-text">{html.escape(it["title_tr"])}</span>'
            f'<span class="ticker-sep">&bull;</span>'
            f'</span>'
        )
    single_track_html = "".join(ticker_elements)
    # Double track ensures seamless infinite loop with zero jump
    ticker_track_content = single_track_html + single_track_html

    # Hero element (Günün Manşeti)
    hero_html = ""
    if portal_data:
        h = portal_data[0]
        is_tr_hero = bool(h.get("is_turkey") or h.get("category") == "Türkiye")
        badge_title = "⭐ GÜNÜN MANŞETİ &bull; 🇹🇷 TÜRKİYE SU GÜNDEMİ" if is_tr_hero else f"⭐ GÜNÜN MANŞETİ &bull; {html.escape(h['category'])}"
        hero_hint = "🏛️ DSİ &bull; Yerel Yönetimler &bull; Ulusal Su &amp; Sulama Gündemi" if is_tr_hero else "ScienceDirect / ASCE / IWMI Akademik Veritabanı Kaynağı"
        hero_html = f"""
        <section class="main-headline-banner" id="heroSection" onclick="openArticleModal({h['id']})" data-slug="{h['slug']}">
            <div class="hero-image-col" style="background-image: url('{html.escape(h['image'])}');">
                <div class="hero-image-overlay">
                    <span class="hero-category-tag" onclick="event.stopPropagation(); filterCategory('{h['slug']}')">{badge_title}</span>
                </div>
            </div>
            <div class="hero-content-col">
                <div class="hero-meta">
                    <span>📅 {html.escape(h['date'][:16] if h.get('date') else today_str)}</span> &bull; 
                    <span>🏛️ {html.escape(h['source'][:40])}</span>
                </div>
                <h2 class="hero-title">{html.escape(h['title_tr'])}</h2>
                {f'<h4 class="hero-title-en">Orijinal Başlık: {html.escape(h["title_en"])}</h4>' if (h.get('title_en') and h['title_en'] != h['title_tr']) else ''}
                <p class="hero-summary">{html.escape(h['summary_tr'][:320])}...</p>
                <div class="hero-footer">
                    <button class="btn-hero-read">Tam Haberi ve Analizi Oku &rarr;</button>
                    <span class="hero-hint">{hero_hint}</span>
                </div>
            </div>
        </section>
        """

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Su Haber Bülteni - Türkiye ve Dünya Su & Sulama Gazetesi</title>
    
    <!-- Meta tags for SEO & Feed Readers -->
    <meta name="description" content="Türkiye ve Dünya genelindeki su kaynakları, tarımsal sulama teknolojileri, hidroloji ve çevre araştırmalarından derlenen modern gazete temalı haber portalı.">
    <link rel="alternate" type="application/rss+xml" title="Su Haber Bülteni (RSS 2.0)" href="{rss_url}">
    <link rel="alternate" type="application/atom+xml" title="Su Haber Bülteni (Atom)" href="{atom_url}">
    <link rel="alternate" type="application/feed+json" title="Su Haber Bülteni (JSON)" href="{json_url}">

    <!-- Google Fonts for Editorial Newspaper Typography -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800;900&family=Merriweather:ital,wght@0,300;0,400;0,700;1,300;1,400&family=Public+Sans:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,800;0,900;1,400;1,700&display=swap" rel="stylesheet">

    <!-- Theme Detection Script (Prevents flash of light theme on load) -->
    <script>
        (function() {{
            const saved = localStorage.getItem('su_portal_theme');
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (saved === 'dark' || (!saved && prefersDark)) {{
                document.documentElement.setAttribute('data-theme', 'dark');
            }} else {{
                document.documentElement.setAttribute('data-theme', 'light');
            }}
        }})();
    </script>

    <style>
        :root {{
            --paper-bg: #fdfdfc;
            --paper-card: #ffffff;
            --ink-black: #111827;
            --ink-dark: #1f2937;
            --ink-muted: #4b5563;
            --ink-light: #6b7280;
            --logo-color: #0b2545;
            --sublogo-color: #134074;
            --newspaper-navy: #0b2545;
            --newspaper-blue: #134074;
            --accent-red: #c1121f;
            --border-line: #d1d5db;
            --border-light: #e5e7eb;
            --border-divider: #111827;
            --border-double: 3px double #111827;
            --top-bar-bg: #0b1a30;
            --top-bar-color: #d1d5db;
            --ticker-bg: #ffffff;
            --nav-bg: #ffffff;
            --cat-btn-bg: #f1f5f9;
            --cat-btn-border: #cbd5e1;
            --cat-btn-color: #1f2937;
            --cat-btn-hover: #e2e8f0;
            --cat-btn-active-bg: #0b2545;
            --cat-btn-active-color: #ffffff;
            --search-bg: #ffffff;
            --search-border: #d1d5db;
            --search-color: #111827;
            --sidebar-card-bg: #ffffff;
            --sidebar-quote-bg: #f8fafc;
            --rss-box-bg: #f0fdf4;
            --rss-box-border: #bbf7d0;
            --modal-bg: #ffffff;
            --modal-header-bg: #f8fafc;
            --modal-text: #262626;
            --modal-footer-bg: #f8fafc;
            --footer-bg: #0b1a30;
            --footer-border: #0b2545;
            --footer-text: #9ca3af;
            --theme-toggle-bg: rgba(255, 255, 255, 0.12);
            --theme-toggle-color: #f1f5f9;
            --theme-toggle-border: rgba(255, 255, 255, 0.25);
            --shadow-subtle: 0 2px 6px rgba(0,0,0,0.03);
            --shadow-hover: 0 8px 18px rgba(0,0,0,0.07);
        }}

        [data-theme="dark"] {{
            --paper-bg: #0a0f1d;
            --paper-card: #131b2e;
            --ink-black: #f8fafc;
            --ink-dark: #e2e8f0;
            --ink-muted: #94a3b8;
            --ink-light: #64748b;
            --logo-color: #f8fafc;
            --sublogo-color: #38bdf8;
            --newspaper-navy: #38bdf8;
            --newspaper-blue: #60a5fa;
            --accent-red: #ef4444;
            --border-line: #1e293b;
            --border-light: #182235;
            --border-divider: #38bdf8;
            --border-double: 3px double #38bdf8;
            --top-bar-bg: #050811;
            --top-bar-color: #94a3b8;
            --ticker-bg: #131b2e;
            --nav-bg: #131b2e;
            --cat-btn-bg: #1a253a;
            --cat-btn-border: #293954;
            --cat-btn-color: #e2e8f0;
            --cat-btn-hover: #23324d;
            --cat-btn-active-bg: #2563eb;
            --cat-btn-active-color: #ffffff;
            --search-bg: #0b1120;
            --search-border: #293954;
            --search-color: #f8fafc;
            --sidebar-card-bg: #131b2e;
            --sidebar-quote-bg: #0e1626;
            --rss-box-bg: #062817;
            --rss-box-border: #14532d;
            --modal-bg: #131b2e;
            --modal-header-bg: #0e1626;
            --modal-text: #e2e8f0;
            --modal-footer-bg: #0e1626;
            --footer-bg: #050811;
            --footer-border: #1e293b;
            --footer-text: #64748b;
            --theme-toggle-bg: rgba(255, 255, 255, 0.15);
            --theme-toggle-color: #f8fafc;
            --theme-toggle-border: rgba(255, 255, 255, 0.25);
            --shadow-subtle: 0 2px 6px rgba(0,0,0,0.3);
            --shadow-hover: 0 8px 20px rgba(0,0,0,0.5);
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--paper-bg);
            color: var(--ink-black);
            font-family: 'Public Sans', -apple-system, sans-serif;
            line-height: 1.6;
            transition: background-color 0.25s ease, color 0.25s ease;
        }}

        /* Top Info Bar */
        .top-masthead-bar {{
            background: var(--top-bar-bg);
            color: var(--top-bar-color);
            font-size: 12px;
            padding: 8px 16px;
            border-bottom: 1px solid var(--border-line);
            transition: background-color 0.25s ease;
        }}
        .top-bar-inner {{
            max-width: 1240px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
        }}
        .top-bar-left {{
            display: flex;
            align-items: center;
            flex-shrink: 0;
            white-space: nowrap;
            gap: 14px;
        }}
        .top-bar-left span, .top-bar-left a {{ margin-right: 0; }}
        .top-stat-link {{
            color: var(--top-bar-color);
            text-decoration: none;
            border-bottom: 1px dotted rgba(255, 255, 255, 0.4);
            padding-bottom: 1px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: all 0.2s ease;
        }}
        .top-stat-link:hover {{
            color: #38bdf8;
            border-bottom: 1px solid #38bdf8;
        }}
        .ext-link-icon {{
            font-size: 10px;
            opacity: 0.75;
            transition: transform 0.15s ease;
        }}
        .top-stat-link:hover .ext-link-icon {{
            transform: translate(1px, -1px);
            opacity: 1;
        }}
        .top-bar-right {{
            display: flex;
            align-items: center;
            flex-shrink: 0;
            gap: 10px;
        }}
        .top-search-box {{
            display: flex;
            align-items: center;
            position: relative;
        }}
        .top-search-box input {{
            padding: 5px 12px;
            background: rgba(255, 255, 255, 0.08);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 20px;
            font-size: 12px;
            width: 190px;
            transition: all 0.25s ease;
        }}
        .top-search-box input::placeholder {{
            color: rgba(255, 255, 255, 0.65);
        }}
        .top-search-box input:focus {{
            outline: none;
            width: 240px;
            background: rgba(255, 255, 255, 0.16);
            border-color: #38bdf8;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25);
        }}
        .top-theme-toggle-btn {{
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.22);
            padding: 5px 11px;
            border-radius: 20px;
            font-size: 13.5px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            user-select: none;
            line-height: 1;
        }}
        .top-theme-toggle-btn:hover {{
            background: rgba(255, 255, 255, 0.22);
            border-color: rgba(255, 255, 255, 0.4);
            transform: translateY(-1px);
        }}
        [data-theme="dark"] .top-search-box input {{
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.15);
        }}
        [data-theme="dark"] .top-theme-toggle-btn {{
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.18);
        }}


        /* Newspaper Header / Masthead */
        .newspaper-header {{
            max-width: 1240px;
            margin: 0 auto;
            padding: 24px 16px 12px;
            text-align: center;
        }}
        .newspaper-motto {{
            font-family: 'Merriweather', serif;
            font-style: italic;
            font-size: 13px;
            color: var(--ink-muted);
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}
        .newspaper-logo {{
            font-family: 'Playfair Display', 'Cinzel', serif;
            font-size: clamp(2.4rem, 6vw, 4.2rem);
            font-weight: 900;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: var(--logo-color);
            margin: 4px 0;
            line-height: 1.1;
            transition: color 0.25s ease;
        }}
        .newspaper-sub-logo {{
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--sublogo-color);
            margin-bottom: 16px;
            transition: color 0.25s ease;
        }}
        .masthead-divider {{
            border-top: 1px solid var(--border-divider);
            border-bottom: 3px solid var(--border-divider);
            height: 4px;
            margin: 12px 0 16px;
            transition: border-color 0.25s ease;
        }}

        /* Breaking News Ticker (Integrated in Top Bar) */
        .top-bar-ticker {{
            flex: 1;
            min-width: 0;
            overflow: hidden;
            height: 28px;
            display: flex;
            align-items: center;
            margin: 0 14px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            padding: 0 10px;
            transition: border-color 0.2s ease, background 0.2s ease;
        }}
        .top-bar-ticker:hover {{
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.22);
        }}
        .ticker-marquee {{
            flex: 1;
            overflow: hidden;
            white-space: nowrap;
            position: relative;
            height: 100%;
            display: flex;
            align-items: center;
            mask-image: linear-gradient(to right, transparent, black 16px, black calc(100% - 16px), transparent);
            -webkit-mask-image: linear-gradient(to right, transparent, black 16px, black calc(100% - 16px), transparent);
        }}
        .ticker-track {{
            display: inline-flex;
            align-items: center;
            white-space: nowrap;
            will-change: transform;
            animation: continuousTickerScroll 68s linear infinite;
        }}
        .ticker-track:hover,
        .top-bar-ticker:hover .ticker-track {{
            animation-play-state: paused;
            cursor: pointer;
        }}
        @keyframes continuousTickerScroll {{
            0% {{
                transform: translateX(0);
            }}
            100% {{
                transform: translateX(-50%);
            }}
        }}
        .ticker-item {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-right: 28px;
            cursor: pointer;
            color: var(--top-bar-color);
            font-size: 12px;
            font-weight: 500;
            text-decoration: none;
            transition: color 0.15s ease;
        }}
        .ticker-item:hover {{
            color: #38bdf8;
        }}
        .ticker-item:hover .ticker-text {{
            text-decoration: underline;
        }}
        .ticker-icon {{
            color: #f59e0b;
            font-size: 11px;
        }}
        .ticker-cat-tag {{
            font-size: 10.5px;
            font-weight: 700;
            color: #38bdf8;
            opacity: 0.95;
        }}
        .ticker-cat-turkey {{
            color: #f87171 !important;
            font-weight: 800 !important;
        }}
        [data-theme="dark"] .ticker-cat-turkey {{
            color: #f87171 !important;
        }}
        .ticker-sep {{
            margin-left: 18px;
            color: rgba(255, 255, 255, 0.3);
            font-size: 12px;
        }}


        /* Navigation Bar */
        .category-nav-bar {{
            max-width: 1240px;
            margin: 0 auto 24px;
            padding: 0 16px;
        }}
        .nav-inner {{
            background: var(--nav-bg);
            border: 1px solid var(--border-line);
            border-radius: 6px;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            flex-wrap: wrap;
            transition: background-color 0.25s ease, border-color 0.25s ease;
        }}
        .category-pills {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: center;
        }}
        .cat-btn {{
            background: var(--cat-btn-bg);
            border: 1px solid var(--cat-btn-border);
            padding: 7px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            color: var(--cat-btn-color);
            cursor: pointer;
            transition: all 0.2s ease;
            user-select: none;
        }}
        .cat-btn:hover {{
            background: var(--cat-btn-hover);
            transform: translateY(-1px);
        }}
        .cat-btn.active {{
            background: var(--cat-btn-active-bg) !important;
            color: var(--cat-btn-active-color) !important;
            border-color: var(--cat-btn-active-bg) !important;
            box-shadow: 0 2px 8px rgba(11, 37, 69, 0.3);
        }}
        .empty-results-box {{
            grid-column: 1 / -1;
            background: var(--paper-card);
            border: 2px dashed var(--border-line);
            border-radius: 8px;
            padding: 48px 24px;
            text-align: center;
            margin: 20px 0;
            width: 100%;
        }}
        .empty-results-box .empty-icon {{
            font-size: 42px;
            margin-bottom: 12px;
        }}
        .empty-results-box h3 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.35rem;
            color: var(--newspaper-navy);
            margin-bottom: 8px;
        }}
        .empty-results-box p {{
            font-size: 13.5px;
            color: var(--ink-muted);
            max-width: 480px;
            margin: 0 auto 20px;
        }}
        .btn-reset-filter {{
            background: var(--newspaper-navy);
            color: white;
            border: none;
            padding: 10px 22px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .btn-reset-filter:hover {{
            background: var(--newspaper-blue);
        }}
        .news-badge {{
            cursor: pointer;
            transition: opacity 0.15s;
        }}
        .news-badge:hover {{
            opacity: 0.85;
        }}
        .hero-category-tag {{
            cursor: pointer;
            transition: opacity 0.15s;
        }}
        .hero-category-tag:hover {{
            opacity: 0.85;
        }}
        .nav-controls {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .search-box {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .search-box input {{
            padding: 6px 12px;
            background: var(--search-bg);
            color: var(--search-color);
            border: 1px solid var(--search-border);
            border-radius: 4px;
            font-size: 13px;
            width: 200px;
            transition: all 0.2s ease;
        }}
        .search-box input:focus {{
            outline: none;
            border-color: var(--newspaper-blue);
        }}
        .theme-toggle-btn-nav {{
            background: var(--cat-btn-bg);
            color: var(--ink-dark);
            border: 1px solid var(--cat-btn-border);
            padding: 6px 11px;
            border-radius: 6px;
            font-size: 15px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            user-select: none;
            line-height: 1;
        }}
        .theme-toggle-btn-nav:hover {{
            background: var(--cat-btn-hover);
            transform: translateY(-1px);
        }}

        /* Main Container */
        .portal-layout {{
            max-width: 1240px;
            margin: 0 auto;
            padding: 0 16px;
        }}

        /* Hero / Main Headline */
        .main-headline-banner {{
            display: grid;
            grid-template-columns: 1.15fr 1fr;
            background: var(--paper-card);
            border: 1px solid var(--border-line);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 28px;
            box-shadow: var(--shadow-subtle);
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s, background-color 0.25s ease, border-color 0.25s ease;
        }}
        .main-headline-banner:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-hover);
        }}
        .hero-image-col {{
            background-size: cover;
            background-position: center;
            min-height: 380px;
            position: relative;
        }}
        .hero-image-overlay {{
            position: absolute;
            bottom: 12px;
            left: 12px;
        }}
        .hero-category-tag {{
            background: var(--accent-red);
            color: white;
            font-size: 11px;
            font-weight: 800;
            padding: 5px 12px;
            border-radius: 3px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        .hero-content-col {{
            padding: 32px 36px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .hero-meta {{
            font-size: 12px;
            color: var(--ink-light);
            margin-bottom: 12px;
            font-weight: 500;
        }}
        .hero-title {{
            font-family: 'Playfair Display', 'Merriweather', serif;
            font-size: clamp(1.4rem, 2.5vw, 2rem);
            font-weight: 800;
            line-height: 1.3;
            color: var(--ink-black);
            margin-bottom: 8px;
        }}
        .hero-title-en {{
            font-size: 12px;
            color: var(--ink-light);
            font-style: italic;
            margin-bottom: 16px;
        }}
        .hero-summary {{
            font-family: 'Merriweather', serif;
            font-size: 14.5px;
            color: var(--ink-dark);
            line-height: 1.65;
            margin-bottom: 24px;
        }}
        .hero-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            border-top: 1px solid var(--border-light);
            padding-top: 16px;
        }}
        .btn-hero-read {{
            background: var(--newspaper-navy);
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 13px;
            font-weight: 700;
            border-radius: 4px;
            cursor: pointer;
        }}
        .hero-hint {{
            font-size: 11.5px;
            color: var(--ink-light);
        }}

        /* Turkey Water News Dedicated Priority Section */
        .turkey-priority-section {{
            background: var(--paper-card);
            border: 1px solid var(--border-line);
            border-top: 4px solid var(--accent-red);
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 32px;
            box-shadow: var(--shadow-subtle);
            transition: background-color 0.25s ease, border-color 0.25s ease;
        }}
        [data-theme="dark"] .turkey-priority-section {{
            background: var(--paper-card);
            border-color: #1e293b;
            border-top-color: #ef4444;
        }}
        .turkey-section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-light);
            padding-bottom: 12px;
        }}
        .turkey-header-title-wrap {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .turkey-header-right {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .turkey-flag-pill {{
            background: #c1121f;
            color: #ffffff;
            font-size: 11px;
            font-weight: 800;
            padding: 4px 10px;
            border-radius: 4px;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }}
        .turkey-section-title {{
            font-family: 'Playfair Display', 'Merriweather', serif;
            font-size: 1.35rem;
            font-weight: 800;
            color: var(--ink-black);
            margin: 0;
            letter-spacing: 0.5px;
        }}
        .turkey-section-subtitle {{
            font-size: 12px;
            color: var(--ink-muted);
            font-weight: 500;
        }}
        .btn-turkey-all {{
            background: transparent;
            border: 1px solid #c1121f;
            color: #c1121f;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
        }}
        .btn-turkey-all:hover {{
            background: #c1121f;
            color: #ffffff;
        }}
        [data-theme="dark"] .btn-turkey-all {{
            border-color: #ef4444;
            color: #f87171;
        }}
        [data-theme="dark"] .btn-turkey-all:hover {{
            background: #ef4444;
            color: #0b1a30;
        }}
        .turkey-cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 18px;
        }}
        .turkey-card {{
            background: var(--paper-bg);
            border: 1px solid var(--border-line);
            border-radius: 6px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            cursor: pointer;
            box-shadow: var(--shadow-subtle);
            transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s, background-color 0.25s;
        }}
        .turkey-card:hover {{
            transform: translateY(-3px);
            box-shadow: var(--shadow-hover);
            border-color: #c1121f;
        }}
        [data-theme="dark"] .turkey-card {{
            background: #0d1527;
            border-color: #1e293b;
        }}
        [data-theme="dark"] .turkey-card:hover {{
            border-color: #ef4444;
        }}
        .turkey-card-img {{
            height: 155px;
            background-size: cover;
            background-position: center;
            position: relative;
        }}
        .turkey-badge {{
            position: absolute;
            top: 8px;
            left: 8px;
            background: rgba(193, 18, 31, 0.92);
            color: #ffffff;
            font-size: 10px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 3px;
            letter-spacing: 0.3px;
        }}
        .turkey-card-body {{
            padding: 14px 16px;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }}
        .turkey-card-meta {{
            font-size: 11px;
            color: var(--ink-light);
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .turkey-card-title {{
            font-family: 'Merriweather', serif;
            font-size: 13.5px;
            font-weight: 700;
            line-height: 1.4;
            color: var(--ink-black);
            margin-bottom: 6px;
        }}
        .turkey-card:hover .turkey-card-title {{
            color: #c1121f;
        }}
        [data-theme="dark"] .turkey-card:hover .turkey-card-title {{
            color: #f87171;
        }}
        .turkey-card-excerpt {{
            font-size: 12px;
            color: var(--ink-muted);
            line-height: 1.45;
            margin-bottom: 12px;
            flex-grow: 1;
        }}
        .turkey-card-footer {{
            display: flex;
            justify-content: flex-end;
            border-top: 1px solid var(--border-light);
            padding-top: 8px;
            margin-top: auto;
        }}
        .turkey-read-btn {{
            font-size: 11.5px;
            font-weight: 700;
            color: #c1121f;
        }}
        [data-theme="dark"] .turkey-read-btn {{
            color: #f87171;
        }}

        /* Secondary Headlines Row */
        .sub-headlines-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 18px;
            margin-bottom: 36px;
        }}
        .sub-headline-card {{
            background: var(--paper-card);
            border: 1px solid var(--border-line);
            border-radius: 6px;
            overflow: hidden;
            display: flex;
            cursor: pointer;
            transition: all 0.2s, background-color 0.25s ease, border-color 0.25s ease;
            box-shadow: var(--shadow-subtle);
        }}
        .sub-headline-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-hover);
        }}
        .sub-headline-img {{
            width: 140px;
            min-width: 140px;
            background-size: cover;
            background-position: center;
            position: relative;
        }}
        .sub-headline-content {{
            padding: 14px 16px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .news-badge {{
            position: absolute;
            top: 8px;
            left: 8px;
            background: rgba(11, 37, 69, 0.9);
            color: white;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 2px;
        }}
        .news-badge-turkey {{
            background: #c1121f !important;
            color: #ffffff !important;
            font-weight: 800 !important;
        }}
        .news-badge-academic {{
            background: #1e3a8a !important;
            color: #ffffff !important;
            font-weight: 800 !important;
            border: 1px solid rgba(255, 255, 255, 0.35);
            box-shadow: 0 1px 4px rgba(30, 58, 138, 0.4);
        }}
        [data-theme="dark"] .news-badge-academic {{
            background: #2563eb !important;
            color: #ffffff !important;
        }}
        .news-date {{
            font-size: 11px;
            color: var(--ink-light);
            margin-bottom: 4px;
        }}
        .sub-headline-content h4 {{
            font-family: 'Merriweather', serif;
            font-size: 14px;
            font-weight: 700;
            line-height: 1.35;
            color: var(--ink-black);
            margin-bottom: 6px;
        }}
        .sub-headline-content p {{
            font-size: 12px;
            color: var(--ink-muted);
            line-height: 1.4;
        }}

        /* 2-Column Newspaper Section */
        .newspaper-columns {{
            display: grid;
            grid-template-columns: 2.3fr 1fr;
            gap: 28px;
        }}

        /* Section Headings */
        .section-headline {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2px solid var(--newspaper-navy);
            padding-bottom: 8px;
            margin-bottom: 20px;
        }}
        .section-headline h3 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.35rem;
            color: var(--newspaper-navy);
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .section-headline span {{
            font-size: 12px;
            color: var(--ink-light);
        }}

        /* Article Cards Grid */
        .articles-news-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .news-grid-card {{
            background: var(--paper-card);
            border: 1px solid var(--border-line);
            border-radius: 6px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: var(--shadow-subtle);
            transition: all 0.2s, background-color 0.25s ease, border-color 0.25s ease;
        }}
        .news-grid-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-hover);
        }}
        .card-img-wrap {{
            height: 170px;
            background-size: cover;
            background-position: center;
            position: relative;
            cursor: pointer;
        }}
        .card-body {{
            padding: 16px;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }}
        .card-meta {{
            font-size: 11px;
            color: var(--ink-light);
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .card-title {{
            font-family: 'Merriweather', serif;
            font-size: 15px;
            font-weight: 700;
            line-height: 1.4;
            color: var(--ink-black);
            margin-bottom: 4px;
            cursor: pointer;
        }}
        .card-title:hover {{
            color: var(--newspaper-blue);
        }}
        .card-title-en {{
            font-size: 11px;
            color: var(--ink-light);
            font-style: italic;
            margin-bottom: 10px;
            line-height: 1.3;
        }}
        .card-excerpt {{
            font-size: 12.5px;
            color: var(--ink-muted);
            line-height: 1.55;
            margin-bottom: 16px;
            flex-grow: 1;
        }}
        .card-action-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border-light);
            padding-top: 10px;
            margin-top: auto;
        }}
        .btn-read-more {{
            background: none;
            border: none;
            color: var(--newspaper-blue);
            font-weight: 700;
            font-size: 12px;
            cursor: pointer;
            padding: 0;
        }}
        .btn-read-more:hover {{ text-decoration: underline; }}
        .link-original {{
            font-size: 11.5px;
            color: var(--ink-light);
            text-decoration: none;
        }}
        .link-original:hover {{ color: var(--ink-black); text-decoration: underline; }}

        /* Sidebar Cards */
        .sidebar-card {{
            background: var(--sidebar-card-bg);
            border: 1px solid var(--border-line);
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-subtle);
            transition: background-color 0.25s ease, border-color 0.25s ease;
        }}
        .sidebar-title {{
            font-family: 'Playfair Display', serif;
            font-size: 1.15rem;
            color: var(--newspaper-navy);
            border-bottom: 2px solid var(--newspaper-navy);
            padding-bottom: 6px;
            margin-bottom: 14px;
        }}
        .editorial-quote {{
            font-family: 'Merriweather', serif;
            font-size: 13.5px;
            font-style: italic;
            color: var(--ink-dark);
            border-left: 3px solid var(--newspaper-navy);
            background: var(--sidebar-quote-bg);
            padding: 12px 14px;
            border-radius: 4px;
            margin-bottom: 12px;
            line-height: 1.6;
        }}
        .editorial-author {{
            font-size: 12px;
            font-weight: 700;
            color: var(--ink-muted);
            text-align: right;
        }}

        /* Data stats infographic */
        .stat-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border-light);
            font-size: 13px;
            color: var(--ink-dark);
        }}
        .stat-value {{
            font-weight: 800;
            color: var(--newspaper-navy);
            font-size: 15px;
        }}

        /* RSS box in sidebar */
        .sidebar-rss-box {{
            background: var(--rss-box-bg);
            border: 1px solid var(--rss-box-border);
            border-radius: 6px;
            padding: 16px;
            text-align: center;
        }}
        .rss-url-display {{
            background: var(--paper-card);
            border: 1px solid var(--rss-box-border);
            color: var(--ink-dark);
            padding: 6px 10px;
            font-family: monospace;
            font-size: 11px;
            border-radius: 4px;
            margin: 8px 0;
            word-break: break-all;
        }}
        .btn-copy-rss {{
            background: #16a34a;
            color: white;
            border: none;
            padding: 8px 14px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
        }}
        .btn-copy-rss:hover {{ background: #15803d; }}

        /* Podcast Banner Card */
        .podcast-banner-card {{
            background: linear-gradient(135deg, #0b2545 0%, #134074 100%);
            color: #ffffff;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 28px;
            box-shadow: 0 8px 24px rgba(11, 37, 69, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        [data-theme="dark"] .podcast-banner-card {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-color: #334155;
        }}
        .podcast-banner-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.15);
            padding-bottom: 12px;
        }}
        .podcast-badge-group {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}
        .podcast-pill {{
            background: #38bdf8;
            color: #0b1a30;
            font-size: 11px;
            font-weight: 800;
            padding: 4px 10px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        }}
        .podcast-time-pill {{
            background: rgba(255, 255, 255, 0.15);
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .podcast-rss-quick {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }}
        .podcast-rss-quick code {{
            background: rgba(0, 0, 0, 0.3);
            padding: 3px 8px;
            border-radius: 4px;
            color: #7dd3fc;
            font-family: monospace;
            font-size: 11px;
        }}
        .btn-copy-podcast-sm {{
            background: #0284c7;
            color: white;
            border: none;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            font-weight: 600;
        }}
        .btn-copy-podcast-sm:hover {{ background: #0369a1; }}
        .podcast-banner-body {{
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 24px;
            align-items: center;
        }}
        @media (max-width: 860px) {{
            .podcast-banner-body {{ grid-template-columns: 1fr; }}
        }}
        .podcast-title {{
            margin: 0 0 6px 0;
            font-size: 1.2rem;
            color: #ffffff;
            font-family: 'Playfair Display', serif;
        }}
        .podcast-desc {{
            margin: 0;
            font-size: 13px;
            color: #cbd5e1;
            line-height: 1.5;
        }}
        .portal-audio-player {{
            width: 100%;
            height: 40px;
            border-radius: 6px;
            outline: none;
        }}
        .podcast-player-footer {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            margin-top: 8px;
        }}
        .podcast-player-footer a {{
            color: #7dd3fc;
            text-decoration: none;
            font-weight: 600;
        }}
        .podcast-player-footer a:hover {{ text-decoration: underline; }}
        .sidebar-podcast-box {{
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        [data-theme="dark"] .sidebar-podcast-box {{
            background: #0f172a;
            border-color: #0369a1;
        }}

        /* Modal / Article Reading Window */
        .modal-backdrop {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(11, 26, 48, 0.75);
            backdrop-filter: blur(4px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            padding: 20px;
        }}
        .modal-window {{
            background: var(--modal-bg);
            width: 100%;
            max-width: 820px;
            max-height: 90vh;
            border-radius: 8px;
            overflow-y: auto;
            border: 1px solid var(--border-line);
            box-shadow: 0 20px 40px rgba(0,0,0,0.35);
            display: flex;
            flex-direction: column;
            transition: background-color 0.25s ease;
        }}
        .modal-header {{
            padding: 16px 24px;
            background: var(--modal-header-bg);
            border-bottom: 1px solid var(--border-line);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-header span {{ font-weight: 700; font-size: 13px; color: var(--newspaper-navy); }}
        .btn-close-modal {{
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: var(--ink-muted);
        }}
        .modal-body {{
            padding: 32px 36px;
        }}
        .modal-category-tag {{
            background: var(--newspaper-navy);
            color: white;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 3px;
            text-transform: uppercase;
            display: inline-block;
            margin-bottom: 12px;
        }}
        .modal-title-tr {{
            font-family: 'Playfair Display', serif;
            font-size: 1.85rem;
            font-weight: 800;
            line-height: 1.3;
            color: var(--ink-black);
            margin-bottom: 8px;
        }}
        .modal-title-en {{
            font-size: 13px;
            color: var(--ink-light);
            font-style: italic;
            margin-bottom: 18px;
        }}
        .modal-meta-bar {{
            display: flex;
            gap: 16px;
            font-size: 12px;
            color: var(--ink-muted);
            border-top: 1px solid var(--border-light);
            border-bottom: 1px solid var(--border-light);
            padding: 10px 0;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }}
        .modal-img {{
            width: 100%;
            max-height: 380px;
            object-fit: cover;
            border-radius: 6px;
            margin-bottom: 24px;
        }}
        .modal-text {{
            font-family: 'Merriweather', serif;
            font-size: 15.5px;
            color: var(--modal-text);
            line-height: 1.8;
            margin-bottom: 30px;
        }}
        .modal-footer {{
            border-top: 1px solid var(--border-line);
            padding: 16px 24px;
            background: var(--modal-footer-bg);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .btn-doi-link {{
            background: var(--newspaper-navy);
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            text-decoration: none;
            font-weight: 700;
            font-size: 13px;
        }}
        .btn-doi-link:hover {{ background: var(--newspaper-blue); }}

        /* Footer */
        .newspaper-footer {{
            border-top: 3px solid var(--footer-border);
            background: var(--footer-bg);
            color: var(--footer-text);
            padding: 40px 16px;
            margin-top: 60px;
            transition: background-color 0.25s ease;
        }}
        .footer-inner {{
            max-width: 1240px;
            margin: 0 auto;
            text-align: center;
            font-size: 13px;
        }}
        .footer-inner h4 {{
            font-family: 'Playfair Display', serif;
            color: var(--ink-black);
            font-size: 1.4rem;
            margin-bottom: 8px;
        }}
        .footer-inner p {{ margin-bottom: 12px; }}

        /* Responsive */
        @media (max-width: 900px) {{
            .main-headline-banner {{ grid-template-columns: 1fr; }}
            .newspaper-columns {{ grid-template-columns: 1fr; }}
        }}
        @media (max-width: 860px) {{
            .top-bar-inner {{
                flex-direction: column;
                align-items: stretch;
                gap: 8px;
            }}
            .top-bar-left {{
                justify-content: space-between;
                width: 100%;
                font-size: 11.5px;
            }}
            .top-bar-ticker {{
                margin: 2px 0;
                width: 100%;
                order: 2;
            }}
            .top-bar-right {{
                justify-content: space-between;
                width: 100%;
                order: 3;
            }}
            .top-search-box {{
                flex: 1;
            }}
            .top-search-box input {{
                width: 100% !important;
            }}
        }}
    </style>
</head>
<body>

    <!-- Top Bar -->
    <div class="top-masthead-bar">
        <div class="top-bar-inner">
            <div class="top-bar-left">
                <span>🗓️ {today_str}</span>
                <a href="https://www.wri.org/applications/aqueduct/water-risk-atlas/" target="_blank" rel="noopener noreferrer" class="top-stat-link" title="Hesaplama Kaynağı: WRI (World Resources Institute) Aqueduct Su Riski ve Stresi Atlası">💧 Türkiye Su Stresi: %64.2 <span class="ext-link-icon">↗</span></a>
            </div>
            <div class="top-bar-ticker">
                <div class="ticker-marquee" title="Akışı durdurmak için imleci üzerine getirebilirsiniz">
                    <div class="ticker-track" id="tickerTrack">
                        {ticker_track_content}
                    </div>
                </div>
            </div>
            <div class="top-bar-right">
                <div class="top-search-box">
                    <input type="text" id="searchInput" placeholder="🔍 Başlıklarda ara..." oninput="filterSearch()" aria-label="Haberlerde ara">
                </div>
                <button type="button" id="themeToggleBtn" class="top-theme-toggle-btn" onclick="toggleTheme()" title="Gece / Gündüz Temasını Değiştir" aria-label="Temayı Değiştir">
                    <span class="theme-icon">🌙</span>
                </button>
            </div>
        </div>
    </div>

    <!-- Masthead -->
    <header class="newspaper-header">
        <div class="newspaper-motto">"Geleceğin dünyasında en stratejik güç sudur."</div>
        <h1 class="newspaper-logo">SU HABER BÜLTENİ</h1>
        <div class="newspaper-sub-logo">Türkiye ve Dünya Su, Sulama ve Çevre Araştırmaları Gazetesi</div>
        <div class="masthead-divider"></div>
    </header>

    <!-- Category Nav Bar -->
    <nav class="category-nav-bar" id="categoryNavBar">
        <div class="nav-inner">
            <div class="category-pills" id="categoryPills">
                <button type="button" class="cat-btn active" data-slug="all" onclick="filterCategory('all')">Tümü</button>
                <button type="button" class="cat-btn" data-slug="akademik" onclick="filterCategory('akademik')">🎓 Akademik Yayınlar</button>
                <button type="button" class="cat-btn" data-slug="sulama" onclick="filterCategory('sulama')">🌾 Tarımsal Sulama</button>
                <button type="button" class="cat-btn" data-slug="teknoloji" onclick="filterCategory('teknoloji')">🔬 Su Teknolojileri</button>
                <button type="button" class="cat-btn" data-slug="kaynak" onclick="filterCategory('kaynak')">💧 Su Kaynakları</button>
                <button type="button" class="cat-btn" data-slug="iklim" onclick="filterCategory('iklim')">🌍 İklim &amp; Kuraklık</button>
                <button type="button" class="cat-btn" data-slug="politika" onclick="filterCategory('politika')">⚖️ Su Politikaları</button>
            </div>
        </div>
    </nav>

    <!-- Main Layout -->
    <main class="portal-layout">
        
        <!-- Hero / Gunun Manseti -->
        {hero_html}

        <!-- Gunluk Podcast Oynatici Karti -->
        {podcast_banner_html}

        <!-- Sub Headlines (Surmansetler) -->
        <section class="sub-headlines-grid" id="subHeadlinesSection">
            {secondary_html}
        </section>

        <!-- Columns Section -->
        <div class="newspaper-columns">
            
            <!-- Left Main Column: News Grid -->
            <div class="main-articles-col">
                <div class="section-headline" id="mainNewsSection">
                    <h3 id="sectionTitle">🌊 Son Bilimsel Araştırmalar &amp; Raporlar</h3>
                    <span id="sectionCount">Toplam <strong>{len(items)}</strong> makale</span>
                </div>
                
                <div class="articles-news-grid" id="newsGrid">
                    <!-- Empty State Box -->
                    <div id="noResultsState" class="empty-results-box" style="display: none;">
                        <div class="empty-icon">💧</div>
                        <h3 id="emptyTitle">Bu kategoride henüz haber bulunmuyor</h3>
                        <p id="emptyDesc">Seçilen kriterlerle eşleşen makale bulunamadı. Yeni bültenler taranmaya devam etmektedir.</p>
                        <button type="button" class="btn-reset-filter" onclick="filterCategory('all')">Tüm Haberleri Göster</button>
                    </div>

                    {grid_html}
                </div>
            </div>

            <!-- Right Sidebar: Editorial & Infographics -->
            <aside class="newspaper-sidebar">
                
                <!-- Editorial Box -->
                <div class="sidebar-card">
                    <h4 class="sidebar-title">Günün Başyazısı</h4>
                    <div class="editorial-quote">
                        "Tarımsal sulamada yapılacak her yüzde 10'luk verimlilik artışı, metropollerin yıllık içme suyu ihtiyacının tamamını karşılayabilecek ölçektedir. Akıllı sensörler ve damla sulama bir tercih değil, milli bir zorunluluktur."
                    </div>
                    <div class="editorial-author">&mdash; Su Haber Bülteni Editör Masası</div>
                </div>

                <!-- Water Stats Infographic -->
                <div class="sidebar-card">
                    <h4 class="sidebar-title">Rakamlarla Su Durumu</h4>
                    <div class="stat-row">
                        <span>Tarımsal Su Kullanım Payı</span>
                        <span class="stat-value">%73</span>
                    </div>
                    <div class="stat-row">
                        <span>Damla Sulamada Tasarruf</span>
                        <span class="stat-value">+%45</span>
                    </div>
                    <div class="stat-row">
                        <span>Kuraklık Tehdidi Altındaki Nüfus</span>
                        <span class="stat-value">2.3 Milyar</span>
                    </div>
                    <div class="stat-row">
                        <span>Yıllık Geri Dönüşüm Hedefi</span>
                        <span class="stat-value">%25 Artış</span>
                    </div>
                </div>

                <!-- Sabit Podcast Akisi (Sidebar) -->
                {podcast_sidebar_html}

                <!-- Live RSS Subscription Card -->
                <div class="sidebar-card sidebar-rss-box">
                    <h4 style="color:#166534; font-size:15px; margin-bottom:6px;">📡 Sabit RSS Kaynağınız</h4>
                    <p style="font-size:12px; color:#14532d;">Feedly, Inoreader, Outlook veya istediğiniz okuyucuya doğrudan ekleyin:</p>
                    <div class="rss-url-display" id="sidebarRssUrl">{rss_url}</div>
                    <button class="btn-copy-rss" onclick="navigator.clipboard.writeText(document.getElementById('sidebarRssUrl').innerText); alert('Sabit RSS linki kopyalandı!');">
                        📋 RSS Linkini Kopyala
                    </button>
                    <div style="margin-top:10px; font-size:11px; color:#15803d;">
                        <a href="{atom_url}" target="_blank" style="color:#15803d; font-weight:bold;">Atom 1.0</a> &bull; 
                        <a href="{json_url}" target="_blank" style="color:#15803d; font-weight:bold;">JSON Feed</a>
                    </div>
                </div>

                <!-- Scientific Sources -->
                <div class="sidebar-card">
                    <h4 class="sidebar-title">Taranan Bilimsel Kaynaklar</h4>
                    <ul style="font-size:12px; color:var(--ink-muted); padding-left:18px; line-height:1.8;">
                        <li>ScienceDirect: Agricultural Water Management</li>
                        <li>ASCE: Journal of Water Resources Planning</li>
                        <li>IWMI: International Water Management Institute</li>
                        <li>Limnologica: Ecology of Inland Waters</li>
                        <li>Water Finance &amp; Management Bülteni</li>
                    </ul>
                </div>

            </aside>
        </div>

    </main>

    <!-- Reading Modal -->
    <div class="modal-backdrop" id="articleModal" onclick="closeArticleModal(event)">
        <div class="modal-window" onclick="event.stopPropagation()">
            <div class="modal-header">
                <span id="modalHeaderCategory">BİLİMSEL YAYIN &bull; SU HABER BÜLTENİ</span>
                <button class="btn-close-modal" onclick="closeArticleModal()">&times;</button>
            </div>
            <div class="modal-body">
                <span class="modal-category-tag" id="modalBadge">Kategori</span>
                <h2 class="modal-title-tr" id="modalTitleTr">Türkçe Başlık</h2>
                <h4 class="modal-title-en" id="modalTitleEn">Orijinal Başlık</h4>
                
                <div class="modal-meta-bar">
                    <span id="modalDate">📅 Tarih</span>
                    <span id="modalSource">🏛️ Kaynak</span>
                    <span id="modalAuthor">✍️ Yazar</span>
                </div>

                <img src="" id="modalImg" class="modal-img" alt="Haber Görseli" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1544717305-2782549b5136?w=900&q=80';">

                <div class="modal-text" id="modalContent">
                    Haber içeriği yükleniyor...
                </div>
            </div>
            <div class="modal-footer">
                <button class="cat-btn" onclick="window.print()">🖨️ Sayfayı Yazdır</button>
                <a href="#" id="modalDoiLink" target="_blank" rel="noopener noreferrer" class="btn-doi-link">
                    Kaynağı Aç
                </a>
            </div>
        </div>
    </div>

    <!-- Newspaper Footer -->
    <footer class="newspaper-footer">
        <div class="footer-inner">
            <h4>SU HABER BÜLTENİ</h4>
            <p>Akademik araştırmalar, hakemli dergiler ve küresel su kurumlarından derlenen günlük dijital su gazetesi.</p>
            <p style="font-size:11.5px; opacity:0.75;">
                Otomasyon: GitHub Actions ile 30 dakikada bir güncellenir &bull; Son Güncelleme: {last_updated} &bull; Depo: mserman90/suhaberportali
            </p>
        </div>
    </footer>

    <!-- Interactive Scripts -->
    <script>
        const articlesData = {json_portal_data};

        function openArticleModal(id) {{
            const it = articlesData.find(a => a.id === id);
            if (!it) return;

            if (it.is_academic) {{
                document.getElementById('modalBadge').innerText = '🎓 ' + it.category;
                document.getElementById('modalHeaderCategory').innerText = '🎓 HAKEMLİ AKADEMİK YAYIN &bull; ' + it.category.toUpperCase() + ' &bull; SU YÖNETİMİ';
            }} else if (it.is_turkey) {{
                document.getElementById('modalBadge').innerText = '🇹🇷 ' + it.category;
                document.getElementById('modalHeaderCategory').innerText = 'TÜRKİYE SU BÜLTENİ &bull; ' + it.category.toUpperCase() + ' &bull; SU HABER BÜLTENİ';
            }} else {{
                document.getElementById('modalBadge').innerText = it.category;
                document.getElementById('modalHeaderCategory').innerText = it.category.toUpperCase() + ' &bull; SU HABER BÜLTENİ';
            }}
            document.getElementById('modalTitleTr').innerText = it.title_tr;
            const titleEnEl = document.getElementById('modalTitleEn');
            if (it.title_en && it.title_en !== it.title_tr) {{
                titleEnEl.innerText = 'Orijinal Başlık: ' + it.title_en;
                titleEnEl.style.display = 'block';
            }} else {{
                titleEnEl.style.display = 'none';
            }}
            document.getElementById('modalDate').innerText = '📅 ' + it.date;
            document.getElementById('modalSource').innerText = '🏛️ ' + it.source;
            document.getElementById('modalAuthor').innerText = it.author ? '✍️ ' + it.author : '✍️ Akademik Kurul';
            
            const imgEl = document.getElementById('modalImg');
            if (it.image) {{
                imgEl.src = it.image;
                imgEl.style.display = 'block';
            }} else {{
                imgEl.style.display = 'none';
            }}

            document.getElementById('modalContent').innerHTML = '<p>' + it.summary_tr.replace(/\\n/g, '</p><p>') + '</p>';
            document.getElementById('modalDoiLink').href = it.link;

            const modal = document.getElementById('articleModal');
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }}

        function closeArticleModal(e) {{
            const modal = document.getElementById('articleModal');
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }}

        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeArticleModal();
        }});

        let currentSlug = 'all';

        const CATEGORY_TITLES = {{
            'all': '🌊 Son Bilimsel Araştırmalar &amp; Raporlar',
            'akademik': '🎓 Yeni Yayınlanan Su Yönetimi Hakemli Akademik Makaleleri',
            'sulama': '🌾 Tarımsal Sulama Araştırmaları',
            'teknoloji': '🔬 Su Teknolojileri &amp; İnovasyon',
            'kaynak': '💧 Su Kaynakları &amp; Havza Yönetimi',
            'iklim': '🌍 İklim &amp; Kuraklık Araştırmaları',
            'politika': '⚖️ Su Politikaları &amp; Yönetişim'
        }};

        function filterCategory(slug) {{
            currentSlug = slug;

            // Clear search input if present
            const searchInput = document.getElementById('searchInput');
            if (searchInput) searchInput.value = '';

            // Update active states on category buttons
            document.querySelectorAll('.cat-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.dataset.slug === slug);
            }});

            const heroEl = document.getElementById('heroSection');
            const subEl = document.getElementById('subHeadlinesSection');
            const titleEl = document.getElementById('sectionTitle');
            const countEl = document.getElementById('sectionCount');
            const noResultsEl = document.getElementById('noResultsState');
            const allCards = document.querySelectorAll('.news-grid-card');

            let visibleCount = 0;

            if (slug === 'all') {{
                // Show Hero and Subheadlines
                if (heroEl) heroEl.style.display = '';
                if (subEl) subEl.style.display = '';

                // Show only non-top cards in grid
                allCards.forEach(card => {{
                    const isTop = card.getAttribute('data-is-top') === 'true';
                    if (!isTop) {{
                        card.style.display = '';
                        visibleCount++;
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});

                if (titleEl) titleEl.innerHTML = CATEGORY_TITLES['all'];
                if (countEl) countEl.innerHTML = `Toplam <strong>${{allCards.length}}</strong> makale`;
                if (noResultsEl) noResultsEl.style.display = 'none';

            }} else if (slug === 'akademik') {{
                if (heroEl) heroEl.style.display = 'none';
                if (subEl) subEl.style.display = 'none';

                allCards.forEach(card => {{
                    const isAcademic = card.getAttribute('data-is-academic') === 'true' || card.dataset.slug === 'akademik';
                    if (isAcademic) {{
                        card.style.display = '';
                        visibleCount++;
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});

                if (titleEl) titleEl.innerHTML = CATEGORY_TITLES['akademik'];
                if (countEl) countEl.innerHTML = `Kategoride <strong>${{visibleCount}}</strong> hakemli makale`;

                if (visibleCount === 0) {{
                    if (noResultsEl) {{
                        document.getElementById('emptyTitle').innerText = 'Akademik su yönetimi yayınları taranıyor...';
                        document.getElementById('emptyDesc').innerText = 'ScienceDirect, MDPI, Springer Nature, Wiley ve DergiPark akademik yayınları taranmaktadır.';
                        noResultsEl.style.display = 'block';
                    }}
                }} else {{
                    if (noResultsEl) noResultsEl.style.display = 'none';
                }}

                const target = document.getElementById('mainNewsSection');
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}

            }} else {{
                // Specific category chosen: hide hero and subheadlines
                if (heroEl) heroEl.style.display = 'none';
                if (subEl) subEl.style.display = 'none';

                // Display all matching cards (including cards 0..3)
                allCards.forEach(card => {{
                    if (card.dataset.slug === slug) {{
                        card.style.display = '';
                        visibleCount++;
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});

                const catTitle = CATEGORY_TITLES[slug] || 'Kategori Haberleri';
                if (titleEl) titleEl.innerHTML = catTitle;
                if (countEl) countEl.innerHTML = `Kategoride <strong>${{visibleCount}}</strong> makale`;

                if (visibleCount === 0) {{
                    if (noResultsEl) {{
                        document.getElementById('emptyTitle').innerText = 'Bu kategoride henüz haber bulunmuyor';
                        document.getElementById('emptyDesc').innerText = 'Seçtiğiniz kategoride yeni bültenler otomatik taranmaya devam etmektedir.';
                        noResultsEl.style.display = 'block';
                    }}
                }} else {{
                    if (noResultsEl) noResultsEl.style.display = 'none';
                }}

                // Smoothly scroll to the articles section
                const target = document.getElementById('mainNewsSection');
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            }}
        }}

        function filterSearch() {{
            const input = document.getElementById('searchInput');
            const query = input.value.trim().toLowerCase();

            if (!query) {{
                filterCategory(currentSlug);
                return;
            }}

            // Deactivate category buttons while search query is active
            document.querySelectorAll('.cat-btn').forEach(btn => btn.classList.remove('active'));

            const heroEl = document.getElementById('heroSection');
            const subEl = document.getElementById('subHeadlinesSection');
            const titleEl = document.getElementById('sectionTitle');
            const countEl = document.getElementById('sectionCount');
            const noResultsEl = document.getElementById('noResultsState');
            const allCards = document.querySelectorAll('.news-grid-card');

            if (heroEl) heroEl.style.display = 'none';
            if (subEl) subEl.style.display = 'none';

            let matchCount = 0;
            allCards.forEach(card => {{
                const searchCorpus = (card.getAttribute('data-search') || '').toLowerCase();
                if (searchCorpus.indexOf(query) > -1) {{
                    card.style.display = '';
                    matchCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            if (titleEl) titleEl.innerHTML = `🔍 Arama Sonuçları: "${{query}}"`;
            if (countEl) countEl.innerHTML = `Eşleşen <strong>${{matchCount}}</strong> makale`;

            if (matchCount === 0) {{
                if (noResultsEl) {{
                    document.getElementById('emptyTitle').innerText = `"${{query}}" ile eşleşen sonuç bulunamadı`;
                    document.getElementById('emptyDesc').innerText = 'Farklı bir arama terimi deneyebilir veya kategorileri seçebilirsiniz.';
                    noResultsEl.style.display = 'block';
                }}
            }} else {{
                if (noResultsEl) noResultsEl.style.display = 'none';
            }}
        }}

        function updateThemeElements(theme) {{
            const isDark = (theme === 'dark');
            const icon = isDark ? '☀️' : '🌙';
            const tooltip = isDark ? 'Gündüz Moduna Geç' : 'Gece Moduna Geç';

            const btn = document.getElementById('themeToggleBtn') || document.getElementById('themeToggleBtnNav');
            if (btn) {{
                btn.innerHTML = `<span class="theme-icon">${{icon}}</span>`;
                btn.title = tooltip;
            }}
        }}

        function toggleTheme() {{
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            const next = (current === 'dark') ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('su_portal_theme', next);
            updateThemeElements(next);
        }}

        // Initialize theme button state as soon as DOM is ready
        (function initThemeUI() {{
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', () => updateThemeElements(current));
            }} else {{
                updateThemeElements(current);
            }}
        }})();

        // Client-side auto-update: Polls feed.json every 90 seconds to check for new articles
        (function initLiveFeedSync() {{
            let knownTopTitle = (articlesData && articlesData.length > 0) ? articlesData[0].title_en : '';

            function escapeHtml(str) {{
                if (!str) return '';
                const p = document.createElement('p');
                p.textContent = str;
                return p.innerHTML;
            }}

            async function checkLiveFeed() {{
                try {{
                    const res = await fetch('feed.json?_=' + Date.now(), {{ cache: 'no-store' }});
                    if (!res.ok) return;
                    const feed = await res.json();
                    const items = feed.items || [];
                    if (!items.length) return;

                    const latest = items[0];
                    const latestTitle = latest.title || latest.id || '';
                    if (latestTitle && knownTopTitle && latestTitle !== knownTopTitle) {{
                        console.log('[Canlı Akış] Yeni su haberleri tespit edildi, ticker güncelleniyor...');
                        knownTopTitle = latestTitle;

                        // Update continuous ticker track seamlessly
                        const track = document.getElementById('tickerTrack');
                        if (track) {{
                            let trackHtml = '';
                            items.slice(0, 15).forEach(item => {{
                                const title = item.title || '';
                                trackHtml += `<span class="ticker-item" onclick="window.location.reload()"><span class="ticker-icon">⚡</span> <span class="ticker-text">${{escapeHtml(title)}}</span> <span class="ticker-sep">&bull;</span></span>`;
                            }});
                            track.innerHTML = trackHtml + trackHtml;
                        }}

                    }}
                }} catch (e) {{
                    // Ignore transient network errors
                }}
            }}

            // Start checking after 45 seconds, then every 90 seconds
            setTimeout(() => {{
                checkLiveFeed();
                setInterval(checkLiveFeed, 90000);
            }}, 45000);
        }})();
    </script>
</body>
</html>"""
