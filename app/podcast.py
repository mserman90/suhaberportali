"""
app/podcast.py
Günlük Su ve Tarımsal Sulama Haberleri Podcast Üreticisi.
1. Güncel haberleri analiz ederek akıcı bir Türkçe sesli bülten metni hazırlar.
2. edge-tts ile yüksek kaliteli nöral Türkçe seslendirme yapar (.mp3).
3. Apple Podcasts, Spotify ve RSS okuyucularıyla %100 uyumlu podcast.xml üretir.
4. Hem son bölümü hem de arşiv bölümlerini saklar.
"""

import os
import sys
import json
import shutil
import asyncio
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup

try:
    import edge_tts
except ImportError:
    edge_tts = None

def clean_for_speech(text: str) -> str:
    """Metni ses sentezleyici için doğal konuşma diline temizler."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'https?://\S+', '', text)
    # Özel sembolleri ve kısaltmaları temizle
    text = text.replace("&", "ve").replace("%", "yüzde ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fetch_full_text_from_link(url: str, timeout: int = 8) -> str:
    """Manşet haberinin web sayfasından tam metnini ayıklar."""
    if not url or not url.startswith("http"):
        return ""
    if "news.google.com" in url or "interpress.com" in url:
        return ""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8"
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
                tag.decompose()
            article_container = (
                soup.find("article")
                or soup.find(class_=re.compile(r'(article-body|news-content|content-text|detail-content|haber-metni|entry-content)', re.I))
                or soup.find("main")
            )
            root = article_container if article_container else soup
            paras = [p.get_text(" ", strip=True) for p in root.find_all("p")]
            valid = [p for p in paras if len(p) > 40 and not any(bad in p.lower() for bad in ["çerez", "cookie", "abone ol", "reklam", "telif hakkı", "bültenimize"])]
            if valid:
                return "\n\n".join(valid[:10])
    except Exception:
        pass
    return ""

def build_podcast_script(items: List[Dict[str, Any]], date_str: str) -> str:
    """
    Sadece günün manşet haberi için haberin tam içeriğiyle podcast bülteni senaryosu oluşturur.
    """
    if not items:
        return (
            f"Merhaba. Su ve Sulama Günlük Bülteni'nin {date_str} tarihli yayınına hoş geldiniz. "
            "Bugün için bültenimizde kayıtlı yeni bir haber bulunmamaktadır. Suyla ve sağlıkla kalın."
        )

    # Yalnızca manşet haberi (items[0])
    headline = items[0]
    title = headline.get("title_tr") or headline.get("title", "")
    source = headline.get("source_feed") or headline.get("author") or "Türkiye Su Gündemi"
    source = source.replace("🇹🇷", "").strip()
    link = headline.get("link", "")

    # Haberin tam metnini çöz: önce web sayfasından tam metin, yoksa zengin açıklama / özet
    full_text = ""
    if link:
        full_text = fetch_full_text_from_link(link)

    if not full_text or len(full_text) < 100:
        desc = headline.get("description") or ""
        sum_tr = headline.get("summary_tr") or ""
        clean_d = BeautifulSoup(desc, "html.parser").get_text(" ", strip=True) if desc else ""
        clean_s = BeautifulSoup(sum_tr, "html.parser").get_text(" ", strip=True) if sum_tr else ""
        
        parts = []
        if clean_d and len(clean_d) > 20:
            parts.append(clean_d)
        if clean_s and clean_s != clean_d and len(clean_s) > 20:
            parts.append(clean_s)
        full_text = "\n\n".join(parts) if parts else title

    clean_title = clean_for_speech(title)
    clean_body = clean_for_speech(full_text)
    clean_source = clean_for_speech(source)

    script_parts = [
        f"Merhaba. Su ve Sulama Günlük Bülteni'nin {date_str} tarihli sesli bültenine hoş geldiniz.",
        f"Günün manşet haberini tüm detaylarıyla aktarıyoruz. Başlığımız: {clean_title}.",
        f"Haberin kaynağı: {clean_source}.",
        f"Haberin tam içeriği ve ayrıntıları şu şekildedir: {clean_body}",
        "Günün manşet haberinin sesli aktarımını tamamladık. Tüm Türkiye ve dünya su yönetimi haberlerine, tarımsal sulama teknolojilerine ve bilimsel araştırmalara su haber bülteni web portalımızdan ulaşabilirsiniz. Bir sonraki bültende görüşmek üzere, suyla ve sağlıkla kalın."
    ]

    return "\n\n".join(script_parts)

async def synthesize_speech(text: str, output_path: Path, voice: str = "tr-TR-AhmetNeural"):
    """Metni MP3 olarak sentezler."""
    if edge_tts is None:
        raise RuntimeError("edge-tts kütüphanesi yüklü değil!")
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))

def generate_podcast_rss(
    episodes: List[Dict[str, Any]],
    feed_title: str,
    feed_description: str,
    public_url: str,
    feed_rss_url: str
) -> str:
    """iTunes ve Spotify uyumlu Podcast RSS 2.0 XML'i üretir."""
    now_rfc822 = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    items_xml = []
    for ep in episodes:
        title = html.escape(ep.get("title", "Günlük Sesli Bülten"))
        desc = html.escape(ep.get("description", ""))
        audio_url = ep.get("audio_url", "")
        file_size = ep.get("file_size_bytes", 0)
        pub_date = ep.get("rfc822_date", now_rfc822)
        guid = ep.get("guid", audio_url)
        duration = ep.get("duration", "04:30")

        items_xml.append(f"""    <item>
      <title>{title}</title>
      <description>{desc}</description>
      <link>{audio_url}</link>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{pub_date}</pubDate>
      <enclosure url="{audio_url}" length="{file_size}" type="audio/mpeg" />
      <itunes:author>Su Haber Bülteni</itunes:author>
      <itunes:summary>{desc}</itunes:summary>
      <itunes:duration>{duration}</itunes:duration>
      <itunes:explicit>no</itunes:explicit>
    </item>""")

    joined_items = "\n".join(items_xml)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{html.escape(feed_title)}</title>
    <link>{public_url}</link>
    <atom:link href="{feed_rss_url}" rel="self" type="application/rss+xml" />
    <language>tr</language>
    <itunes:author>Su Haber Bülteni</itunes:author>
    <itunes:summary>{html.escape(feed_description)}</itunes:summary>
    <description>{html.escape(feed_description)}</description>
    <itunes:owner>
      <itunes:name>Su Haber Bülteni</itunes:name>
      <itunes:email>podcast@suhaberportali.local</itunes:email>
    </itunes:owner>
    <itunes:category text="Science">
      <itunes:category text="Earth Sciences"/>
    </itunes:category>
    <itunes:category text="Technology"/>
    <itunes:explicit>no</itunes:explicit>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <image>
      <url>https://images.unsplash.com/photo-1544717305-2782549b5136?w=600&amp;q=80</url>
      <title>{html.escape(feed_title)}</title>
      <link>{public_url}</link>
    </image>
{joined_items}
  </channel>
</rss>
"""

def generate_daily_podcast(
    items: List[Dict[str, Any]],
    dist_dir: Path,
    public_base_url: str,
    enable_generation: bool = True
) -> Dict[str, Any]:
    """
    Günlük podcast bölümünü yönetir.
    Bölümleri data/episodes içinde kalıcı saklar, dist/episodes içine aktarır
    ve yalnızca geçerli/mevcut bölümleri barındıran podcast.xml dosyasını üretir.
    """
    episodes_dir = dist_dir / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    
    data_dir = dist_dir.parent / "data"
    data_episodes_dir = data_dir / "episodes"
    data_episodes_dir.mkdir(parents=True, exist_ok=True)
    meta_path = data_dir / "podcast_episodes.json"

    # 1. data/episodes klasöründeki mevcut tüm bölümleri dist/episodes altına senkronize et
    for cached_mp3 in data_episodes_dir.glob("*.mp3"):
        target_mp3 = episodes_dir / cached_mp3.name
        if not target_mp3.exists() or target_mp3.stat().st_size != cached_mp3.stat().st_size:
            shutil.copy2(cached_mp3, target_mp3)

    # 2. Mevcut bölümleri yükle
    episodes = []
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                episodes = json.load(f)
        except Exception:
            episodes = []

    now = datetime.now(timezone.utc)
    today_key = now.strftime("%Y%m%d")
    date_display = now.strftime("%d.%m.%Y")
    rfc822_date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    filename_dated = f"podcast_{today_key}.mp3"
    filepath_data = data_episodes_dir / filename_dated
    filepath_dist = episodes_dir / filename_dated
    filepath_latest_data = data_episodes_dir / "podcast_latest.mp3"
    filepath_latest_dist = episodes_dir / "podcast_latest.mp3"

    headline = items[0] if items else {}
    headline_title = headline.get("title_tr") or headline.get("title") or "Günün Manşeti"
    clean_headline_title = clean_for_speech(headline_title)

    # 3. Ses dosyasını kontrol et veya gerekiyorsa sentezle
    # Eğer önbellekteki bölüm bugünün manşet başlığıyla uyuşmuyorsa manşet için yeniden üret
    needs_regen = False
    if episodes and episodes[0].get("date_key") == today_key:
        cached_title = episodes[0].get("title", "")
        if clean_headline_title[:30].lower() not in cached_title.lower():
            needs_regen = True

    if filepath_data.exists() and filepath_data.stat().st_size > 1000 and not needs_regen:
        print(f"[*] Bugünün manşet podcast ses dosyası önbellekte mevcut: {filename_dated} ({filepath_data.stat().st_size} bayt)")
        shutil.copy2(filepath_data, filepath_dist)
        shutil.copy2(filepath_data, filepath_latest_dist)
        shutil.copy2(filepath_data, filepath_latest_data)
    elif enable_generation:
        print(f"[*] Günün Manşeti sesli bülten metni hazırlanıyor ({date_display}): {clean_headline_title[:50]}...")
        script = build_podcast_script(items, date_display)
        print(f"[*] Edge-TTS ile yeni ses dosyası oluşturuluyor: {filename_dated}...")
        try:
            asyncio.run(synthesize_speech(script, filepath_data))
            if filepath_data.exists() and filepath_data.stat().st_size > 1000:
                shutil.copy2(filepath_data, filepath_dist)
                shutil.copy2(filepath_data, filepath_latest_dist)
                shutil.copy2(filepath_data, filepath_latest_data)
                print(f"[+] Manşet podcast ses dosyası başarıyla üretildi: {filepath_data.stat().st_size} bayt")
        except Exception as e:
            print(f"[!] Podcast ses sentezi hatası: {e}")
    else:
        print("[*] Gün içi tarama: Yeni ses sentezi atlandı. Mevcut bölümler kullanılıyor.")

    # 4. Meta veri kaydı (Bugünün dosyası başarıyla varsa güncelle)
    file_size = filepath_data.stat().st_size if filepath_data.exists() else 0
    audio_public_url = f"{public_base_url}/episodes/{filename_dated}"
    latest_public_url = f"{public_base_url}/episodes/podcast_latest.mp3"

    new_ep = None
    if file_size > 1000:
        new_ep = {
            "guid": f"suhaber-{today_key}",
            "title": f"Günün Manşeti: {clean_headline_title[:75]}",
            "description": f"{date_display} tarihli Günün Manşeti haberinin sesli bülteni: {clean_headline_title}. Kaynak: {headline.get('source_feed', '')}",
            "filename": filename_dated,
            "audio_url": audio_public_url,
            "file_size_bytes": file_size,
            "rfc822_date": rfc822_date,
            "date_key": today_key,
            "duration": "03:15"
        }
        # Listeyi güncelle (en yeni en başta)
        episodes = [ep for ep in episodes if ep.get("date_key") != today_key]
        episodes.insert(0, new_ep)

        # Meta veriyi kaydet (son 30 bölüm)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(episodes[:30], f, ensure_ascii=False, indent=2)

    # 5. Yalnızca dosya olarak fiziksel olarak mevcut olan bölümleri yayına al
    playable_episodes = []
    for ep in episodes:
        fname = ep.get("filename")
        if fname and (episodes_dir / fname).exists() and (episodes_dir / fname).stat().st_size > 1000:
            playable_episodes.append(ep)

    # Eğer oynatılabilir bölüm yok ama latest.mp3 varsa fallback oluştur
    if not playable_episodes and filepath_latest_dist.exists() and filepath_latest_dist.stat().st_size > 1000:
        fallback_ep = (episodes[0] if episodes else {
            "guid": f"suhaber-{today_key}",
            "title": f"Su & Sulama Günlük Bülteni - {date_display}",
            "description": f"{date_display} tarihli güncel su ve sulama sesli özeti.",
            "filename": "podcast_latest.mp3",
            "audio_url": latest_public_url,
            "file_size_bytes": filepath_latest_dist.stat().st_size,
            "rfc822_date": rfc822_date,
            "date_key": today_key,
            "duration": "03:45"
        })
        playable_episodes.append(fallback_ep)

    # 6. Sabit podcast.xml üret
    feed_episodes = playable_episodes if playable_episodes else episodes
    podcast_xml = generate_podcast_rss(
        episodes=feed_episodes,
        feed_title="Su Haber Bülteni - Günlük Podcast",
        feed_description="Türkiye ve Dünya Su, Sulama ve Hidroloji Araştırmaları Günlük Sesli Bülteni",
        public_url=public_base_url,
        feed_rss_url=f"{public_base_url}/podcast.xml"
    )
    podcast_xml_path = dist_dir / "podcast.xml"
    podcast_xml_path.write_text(podcast_xml, encoding="utf-8")
    print(f"[+] Sabit Podcast RSS başarıyla üretildi: {podcast_xml_path} ({len(playable_episodes)} dinlenebilir bölüm)")

    effective_latest = playable_episodes[0] if playable_episodes else (new_ep or (episodes[0] if episodes else None))

    return {
        "latest_episode": effective_latest,
        "latest_audio_url": latest_public_url,
        "podcast_rss_url": f"{public_base_url}/podcast.xml"
    }
