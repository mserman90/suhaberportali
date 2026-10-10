#!/usr/bin/env python3
"""
export_static.py
Inoreader akışını çekip 'dist/' dizinine:
- Türkçe gazete temalı 'Su Haber Bülteni' web portalını (dist/index.html)
- Sabit RSS 2.0 yayınını (dist/rss.xml)
- Atom 1.0 yayınını (dist/atom.xml)
- JSON Feed (dist/feed.json)
dosyalarını üretir.
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import config
from app.storage import Storage
from app.scraper import scrape_inoreader, scrape_turkey_water_news, scrape_academic_water_publications
from app.feed import generate_rss_2_xml, generate_atom_xml, generate_json_feed
from app.translator import (
    batch_translate_articles,
    categorize_article,
    translate_to_turkish,
    generate_turkish_editorial_summary,
    is_genuinely_turkish
)
from app.portal import generate_newspaper_portal_html
from app.podcast import generate_daily_podcast
import re

def main():
    dist_dir = Path(os.getenv("DIST_DIR", config.BASE_DIR / "dist"))
    dist_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Inoreader akışı kontrol ediliyor: {config.INOREADER_URL}")
    data = scrape_inoreader(config.INOREADER_URL)
    raw_items = data.get("items", [])
    print(f"[+] Çekilen güncel makale sayısı: {len(raw_items)}")

    print("[*] Türkiye su haberleri taranıyor...")
    turkey_items = scrape_turkey_water_news(limit=25)
    print(f"[+] Çekilen güncel Türkiye su haberi sayısı: {len(turkey_items)}")

    print("[*] Yeni yayınlanan su yönetimi akademik yayınları Google Dorking ile taranıyor...")
    academic_items = scrape_academic_water_publications(limit_per_query=12, max_total=40)
    print(f"[+] Çekilen güncel akademik yayın sayısı: {len(academic_items)}")

    print("[*] Güncel basın haber takibi kontrol ediliyor...")
    try:
        from app.sygm_scraper import scrape_sygm_daily_report
        sygm_items = scrape_sygm_daily_report()
        print(f"[+] Çekilen güncel ulusal basın haberi sayısı: {len(sygm_items)}")
    except Exception as sygm_err:
        print(f"[!] Basın haber takibi tarama hatası: {sygm_err}")
        sygm_items = []

    storage = Storage(config.DB_PATH)
    storage.save_items(raw_items)
    storage.save_items(turkey_items)
    storage.save_items(academic_items)
    storage.save_items(sygm_items)
    storage.prune_items(config.MAX_STORED_ITEMS)

    # Retrieve all stored items
    items = storage.get_items(limit=200)
    print(f"[+] Toplam veritabanı kaydı: {len(items)}")

    from app.image_enricher import resolve_article_image

    # Parallel translation for missing items
    items = batch_translate_articles(items)

    TURKEY_PAT = re.compile(
        r"\b(türkiye|turkey|türk su|türkiye'de|dsi|devlet su işleri|barajı|barajları|baraj doluluk|iski|aski|izsu|gap projesi|güneydoğu anadolu|fırat nehri|dicle nehri|kızılırmak|yeşilırmak|meriç nehri|gediz nehri|büyük menderes|küçük menderes|sakarya nehri|van gölü|tuz gölü|beyşehir gölü|eğirdir gölü|atatürk barajı|keban barajı|karakaya barajı|tarım ve orman bakanlığı|su verimliliği seferberliği)\b",
        re.IGNORECASE
    )
    FOREIGN_PAT = re.compile(
        r"\b(colorado|utah|california|arizona|nevada|mississippi|salt lake|texas|australia|murray-darling|yangtze|yellow river|mekong|ganges|indus|danube|rhine)\b",
        re.IGNORECASE
    )

    # Persist translations, updated categories, Turkey flag and resolved images into SQLite
    for idx, it in enumerate(items):
        title_tr = it.get("title_tr")
        if not title_tr or not is_genuinely_turkish(title_tr):
            title_tr = translate_to_turkish(it["title"])
        it["title_tr"] = title_tr

        source = it.get("source_feed") or ""
        desc = it.get("description") or ""
        full_text = title_tr + " " + it.get("title", "") + " " + desc + " " + source

        # Check if article is an academic publication
        is_academic = 1 if (it.get("is_academic") or it.get("guid", "").startswith("academic:") or "🎓" in source) else 0
        it["is_academic"] = is_academic

        # Check if article genuinely relates to Turkey
        is_tr_scraped = bool(it.get("guid", "").startswith("tr_water:") or it.get("guid", "").startswith("sygm:") or "🇹🇷" in source)
        is_tr_match = bool(TURKEY_PAT.search(full_text) and not FOREIGN_PAT.search(full_text))
        is_turkey = 1 if (is_tr_scraped or is_tr_match) else 0
        it["is_turkey"] = is_turkey

        category_tr = it.get("category_tr")
        if is_turkey:
            category_tr = "Türkiye"
        elif not category_tr or category_tr == "Türkiye":
            category_tr = categorize_article(title_tr + " " + it["title"], desc)
        it["category_tr"] = category_tr

        summary_tr = it.get("summary_tr")
        if not summary_tr or not is_genuinely_turkish(summary_tr):
            summary_tr = generate_turkish_editorial_summary(title_tr, category_tr, source, "")
        it["summary_tr"] = summary_tr

        storage.update_item_translation(
            it["guid"],
            title_tr,
            summary_tr,
            category_tr,
            is_turkey,
            is_academic
        )
        resolved_img = resolve_article_image(it, idx)
        it["image_url"] = resolved_img
        storage.update_item_image(it["guid"], resolved_img)
    print(f"[+] {len(items)} haberin görselleri çözümlendi ve veritabanına işlendi.")

    # Manşet Önceliği: Türkiye su haberleri HER ZAMAN en başta (manşette) yer alsın
    # Güncellik (recency) esastır: Yeni haberler güncellik azalışı (time-decay) sayesinde eski haberleri geride bırakır.
    now_ts = int(datetime.now(timezone.utc).timestamp())

    def turkey_headline_sort_key(x):
        guid = x.get("guid", "")
        source = x.get("source_feed", "")
        title = (x.get("title_tr", "") + " " + x.get("title", "")).lower()

        # Alakasız yabancı göl/nehir haberlerini ele
        if any(bad in title for bad in ["colorado", "utah", "california", "arizona", "nevada", "mississippi", "salt lake"]):
            return (-999999999, 0)

        is_tr = bool(
            guid.startswith("tr_water:")
            or guid.startswith("sygm:")
            or "🇹🇷" in source
            or x.get("is_turkey")
            or x.get("category_tr") == "Türkiye"
        )
        if not is_tr:
            return (-999999999, 0)

        pub_ts = int(x.get("pub_date_ts") or 0)
        # Gün farkı hesabı (time decay)
        age_days = max(0.0, (now_ts - pub_ts) / 86400.0) if pub_ts > 0 else 5.0

        quality = 1000.0
        # Temel su & kuraklık kavramları için ek puan
        if any(k in title for k in ["baraj", "doluluk", "sulama", "su yönetimi", "kuraklık", "dsi", "su krizi", "su verimliliği", "göl", "akarsu"]):
            quality += 300.0
        # Su kesintisi / rutin ihale / personel haberlerinin manşete çıkmasını engelle
        if any(k in title for k in ["kesinti", "ihale", "personel", "kadro", "voleybol", "futbol"]):
            quality -= 800.0

        # Her geçen gün için 500 puan düşür (Eski haberler bugünkü yeni haberin önüne geçemez)
        final_score = quality - (age_days * 500.0)
        return (final_score, pub_ts)

    tr_candidates = [it for it in items if turkey_headline_sort_key(it)[0] > -500000]
    tr_sorted = sorted(tr_candidates, key=turkey_headline_sort_key, reverse=True)
    if tr_sorted:
        top_tr = tr_sorted[0]
        items = [top_tr] + [it for it in items if it.get("guid") != top_tr.get("guid")]
        print(f"[+] Manşet Türkiye su haberi olarak belirlendi: {top_tr.get('title_tr')} (Tarih: {top_tr.get('pub_date')})")

    public_url = config.PUBLIC_BASE_URL or "https://mserman90.github.io/suhaberportali"
    rss_self = f"{public_url}/rss.xml"
    atom_self = f"{public_url}/atom.xml"
    json_self = f"{public_url}/feed.json"
    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    # Format RSS items with 100% Turkish titles & rich Turkish descriptions
    import html
    rss_items = []
    for it in items:
        r_item = dict(it)
        title_tr = it.get("title_tr") or it["title"]
        category_tr = it.get("category_tr", "Su Kaynakları")
        r_item["title"] = f"[{category_tr}] {title_tr}"

        # Construct Turkish description for RSS / Atom feeds
        desc_parts = []
        if it.get("image_url"):
            desc_parts.append(f'<p><img src="{html.escape(it["image_url"])}" alt="{html.escape(title_tr)}" style="max-width:100%; border-radius:6px;" /></p>')
        if it.get("category_tr"):
            desc_parts.append(f'<p><strong>Kategori:</strong> {html.escape(category_tr)}</p>')
        if it.get("source_feed"):
            desc_parts.append(f'<p><strong>Kaynak:</strong> {html.escape(it["source_feed"])}</p>')
        if it.get("title") and it.get("title") != title_tr:
            desc_parts.append(f'<p><strong>Orijinal Başlık:</strong> {html.escape(it["title"])}</p>')
        if it.get("summary_tr"):
            desc_parts.append(f'<p>{html.escape(it["summary_tr"])}</p>')
        desc_parts.append(f'<p><a href="{html.escape(it["link"])}" target="_blank" rel="noopener noreferrer">Makalenin Tamamını Oku &rarr;</a></p>')

        r_item["description"] = "\n".join(desc_parts)
        rss_items.append(r_item)

    # 1. Generate RSS 2.0
    rss_content = generate_rss_2_xml(
        feed_title="Su Haber Bülteni - Su & Sulama Gazetesi",
        feed_description="Türkiye ve Dünya Su, Sulama, Çevre ve Hidroloji Araştırmaları Gazetesi",
        feed_link=public_url,
        self_rss_url=rss_self,
        items=rss_items,
        language="tr"
    )
    (dist_dir / "rss.xml").write_text(rss_content, encoding="utf-8")
    print(f"[+] Üretildi: {dist_dir / 'rss.xml'}")

    # 2. Generate Atom 1.0
    atom_content = generate_atom_xml(
        feed_title="Su Haber Bülteni",
        feed_description="Türkiye ve Dünya Su, Sulama, Çevre ve Hidroloji Araştırmaları Gazetesi",
        feed_link=public_url,
        self_atom_url=atom_self,
        items=rss_items
    )
    (dist_dir / "atom.xml").write_text(atom_content, encoding="utf-8")
    print(f"[+] Üretildi: {dist_dir / 'atom.xml'}")

    # 3. Generate JSON Feed
    json_data = generate_json_feed(
        feed_title="Su Haber Bülteni",
        feed_description="Türkiye ve Dünya Su, Sulama, Çevre ve Hidroloji Araştırmaları Gazetesi",
        feed_link=public_url,
        self_json_url=json_self,
        items=rss_items
    )
    (dist_dir / "feed.json").write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] Üretildi: {dist_dir / 'feed.json'}")

    # 4. Generate Daily Podcast & Podcast RSS Feed (podcast.xml)
    podcast_info = None
    enable_podcast_env = os.getenv("ENABLE_PODCAST", "").strip().lower()
    enable_podcast = enable_podcast_env in ("true", "1", "yes") if enable_podcast_env else True

    try:
        podcast_info = generate_daily_podcast(items, dist_dir, public_url, enable_generation=enable_podcast)
    except Exception as pe:
        print(f"[!] Podcast üretimi sırasında hata: {pe}")

    # 5. Generate Modern Newspaper Theme Portal in dist/index.html with Podcast Player
    portal_html = generate_newspaper_portal_html(items, now_str, rss_self, atom_self, json_self, podcast_info=podcast_info)
    (dist_dir / "index.html").write_text(portal_html, encoding="utf-8")
    print(f"[+] Üretildi: {dist_dir / 'index.html'} ('Su Haber Bülteni' Modern Gazete Portalı & Podcast)")

    # 6. Dispatch Daily Podcast to WhatsApp Group (Yalnızca sabah bülteninde veya zorlandığında)
    if enable_podcast and podcast_info and podcast_info.get("latest_episode"):
        try:
            from app.whatsapp import send_daily_podcast_to_whatsapp
            send_daily_podcast_to_whatsapp(podcast_info, items, public_url)
        except Exception as we:
            print(f"[!] WhatsApp paylaşımı sırasında hata: {we}")
    elif not enable_podcast:
        print("[*] Gün içi periyodik tarama: WhatsApp bülten gönderimi atlandı (Yalnızca sabah 10:00 bülteninde iletilir).")

    print("[*] Tüm gazete portalı, podcast ve yayın dosyaları başarıyla hazırlandı!")

if __name__ == "__main__":
    main()
