"""
app/sygm_scraper.py
Tarım ve Orman Bakanlığı Su Yönetimi Genel Müdürlüğü (SYGM)
Günlük Medya Raporu e-postalarını Outlook üzerinden okuyup
Interpress medya takibindeki su haberlerini ayrıştıran ve veritabanına ekleyen modül.
"""

import re
import json
import logging
import email.utils
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("sygm_scraper")

def tr_lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()

def tr_upper(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()

def turkish_title_case(text: str) -> str:
    """
    Türkçe karakter kurallarına uygun Başlık Düzeni (Title Case).
    Ör: 'HAVZA SU KURULU TOPLANTISI' -> 'Havza Su Kurulu Toplantısı'
    """
    if not text:
        return ""
    
    preserve_words = {
        "DSİ", "SYGM", "OSB", "MESKİ", "İSKİ", "ASKİ", "İZSU", "TÜBİTAK", "GAP",
        "AB", "ABD", "BM", "UNESCO", "WRI", "IWMI", "ASCE", "OECD", "WWF", "TEMA"
    }
    
    words = text.strip().split()
    res = []
    for w in words:
        clean_w = "".join(c for c in w if c.isalnum()).upper()
        if clean_w in preserve_words:
            res.append(w.upper())
            continue
            
        if not w:
            continue
            
        first = tr_upper(w[0]) if w else ""
        rest = tr_lower(w[1:]) if len(w) > 1 else ""
        res.append(first + rest)
        
    return " ".join(res)


def categorize_sygm_news(title: str, tags: List[str]) -> str:
    """
    Haber başlığı ve SYGM etiketlerine göre portal kategorisini belirler.
    """
    text = (title + " " + " ".join(tags)).lower()
    
    if any(k in text for k in ["sulama", "tarımsal sulama", "damla sulama", "çiftçi", "hasat", "ürün"]):
        return "Sulama"
    if any(k in text for k in ["arıtma", "atıksu", "teknoloji", "desalinasyon", "sensör", "otomasyon", "membran"]):
        return "Su Teknolojileri"
    if any(k in text for k in ["iklim", "kuraklık", "yağış", "sıcaklık", "sel", "taşkın", "küresel ısınma"]):
        return "İklim & Kuraklık"
    if any(k in text for k in ["politika", "kanun", "mevzuat", "şura", "bakan", "bakanlık", "yönetmelik", "havza kurulu", "genel müdür"]):
        return "Su Politikaları"
    if any(k in text for k in ["baraj", "göl", "yeraltı suyu", "akifer", "nehir", "akarsu", "kaynak"]):
        return "Su Kaynakları"
        
    return "Türkiye"


def get_latest_sygm_email_from_outlook() -> Optional[Tuple[str, str, str]]:
    """
    Yerel Windows Outlook MAPI oturumu üzerinden Su Yönetimi Genel Müdürlüğü
    tarafından gönderilen son medya raporu e-postasını bulur.
    
    Dönüş: (subject, received_time_str, html_body) veya None
    """
    try:
        import win32com.client
    except ImportError:
        logger.warning("win32com modülü yüklü değil; Outlook üzerinden e-posta okunamıyor.")
        return None

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        inbox = namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
        
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)  # En yeniden en eskiye sırala
        
        target_subject_needle = "MEDYA RAPORU"
        
        for item in items:
            try:
                subj = str(getattr(item, "Subject", ""))
                sender_email = str(getattr(item, "SenderEmailAddress", "")).lower()
                sender_name = str(getattr(item, "SenderName", "")).lower()
                
                # Konu ve gönderen filtresi
                if target_subject_needle in subj.upper():
                    if "sygm" in sender_email or "sygm" in sender_name or "su yönetimi" in sender_name or "tarimorman" in sender_email or "tarimorman" in sender_name:
                        html_body = str(getattr(item, "HTMLBody", ""))
                        rec_time = str(getattr(item, "ReceivedTime", ""))
                        logger.info(f"SYGM Medya Raporu e-postası bulundu: {subj} (Tarih: {rec_time})")
                        return subj, rec_time, html_body
            except Exception:
                continue
                
    except Exception as e:
        logger.error(f"Outlook MAPI erişim hatası: {e}")
        
    return None


def extract_report_url_from_html(html_body: str) -> Optional[str]:
    """
    E-posta HTML içeriğindeki 'Mail içeriğini görmek için lütfen tıklayınız'
    veya Interpress stream bağlantısını çıkarır.
    """
    if not html_body:
        return None
        
    soup = BeautifulSoup(html_body, "html.parser")
    
    # 1. Öncelik: 'içeriğini görmek için' metnini içeren <a> etiketi
    for a in soup.find_all("a"):
        text = a.get_text(separator=" ", strip=True).lower()
        href = a.get("href", "")
        if ("içeriğini görmek için" in text or "icerigini gormek icin" in text or "lütfen tıklayınız" in text) and href.startswith("http"):
            return href
                
    # 2. Öncelik: Doğrudan interpress temp stream URL'si
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if "stream.interpress.com/temp/" in href:
            return href
            
    # 3. Regex ile HTML içinde arama
    match = re.search(r'https?://stream\.interpress\.com/temp/[a-zA-Z0-9\-]+\.html', html_body)
    if match:
        return match.group(0)
        
    return None


def fetch_interpress_media_report(report_url: str) -> List[Dict[str, Any]]:
    """
    Interpress medya takip raporu sayfasından haberleri ve küpürleri çeker.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        )
    }
    
    try:
        resp = requests.get(report_url, headers=headers, timeout=20)
        if resp.status_code != 200:
            logger.error(f"Interpress raporu yüklenemedi. HTTP Durumu: {resp.status_code}")
            return []
            
        resp.encoding = "utf-8"
        content = resp.text
        
        # HTML içindeki var jsonData = [...] değişkenini yakala
        match = re.search(r'var\s+jsonData\s*=\s*(\[\s*\{[\s\S]*?\}\s*\])\s*;', content)
        if not match:
            logger.error("Interpress sayfasında 'jsonData' değişkeni bulunamadı.")
            return []
            
        data = json.loads(match.group(1))
        
        items: List[Dict[str, Any]] = []
        now_dt = datetime.now(timezone.utc)
        
        for cat in data:
            for sub in cat.get("subCategories", []):
                for doc in sub.get("documents", []):
                    raw_title = doc.get("t", "").strip()
                    if not raw_title:
                        continue
                        
                    clean_title = turkish_title_case(raw_title)
                    newspaper_name = doc.get("mn", "Ulusal Basın").strip()
                    newspaper_name_clean = turkish_title_case(newspaper_name)
                    
                    # Tarih çözümleme: doc['d'] '05.10.2026' biçimindedir
                    raw_date = doc.get("d", "").strip()
                    pub_ts = int(now_dt.timestamp())
                    pub_rfc = email.utils.format_datetime(now_dt)
                    if raw_date:
                        try:
                            d_parsed = datetime.strptime(raw_date, "%d.%m.%Y").replace(hour=10, minute=0, second=0, tzinfo=timezone.utc)
                            pub_ts = int(d_parsed.timestamp())
                            pub_rfc = email.utils.format_datetime(d_parsed)
                        except Exception:
                            pass
                            
                    # Küpür görseli
                    fs = doc.get("fs", [])
                    image_url = fs[0] if (fs and isinstance(fs, list) and str(fs[0]).startswith("http")) else ""
                    
                    # Görüntüleyici bağlantısı
                    viewer_url = doc.get("il") or doc.get("ils") or report_url
                    doc_id = str(doc.get("id") or doc.get("uuid"))
                    
                    # Konu etiketleri
                    category_tags = [c.get("n", "") for c in doc.get("cs", []) if isinstance(c, dict) and c.get("n")]
                    category_tr = categorize_sygm_news(clean_title, category_tags)
                    
                    page_no = doc.get("pn", 1)
                    circulation = doc.get("sl", "-")
                    
                    desc = (
                        f"Tarım ve Orman Bakanlığı Su Yönetimi Genel Müdürlüğü (SYGM) Günlük Medya Takip Raporu. "
                        f"Yayın: {newspaper_name_clean} Gazetesi (Sayfa: {page_no}, Tiraj: {circulation}). "
                        f"Konu Başlığı: {clean_title}. "
                        f"Orijinal gazete küpürü ve interaktif haber detayları için bağlantıyı ziyaret ediniz."
                    )
                    
                    item_dict = {
                        "guid": f"sygm:{doc_id}",
                        "title": clean_title,
                        "title_tr": clean_title,
                        "link": viewer_url,
                        "author": newspaper_name_clean,
                        "source_feed": f"🏛️ SYGM Medya • {newspaper_name_clean}",
                        "description": desc,
                        "summary_tr": desc,
                        "category_tr": category_tr,
                        "is_turkey": 1,
                        "image_url": image_url,
                        "pub_date": pub_rfc,
                        "pub_date_ts": pub_ts,
                        "raw_date_str": raw_date,
                    }
                    items.append(item_dict)
                    
        logger.info(f"Interpress raporundan {len(items)} haber başarıyla ayıklandı.")
        return items
        
    except Exception as e:
        logger.error(f"Interpress raporu çekme ve işleme hatası: {e}")
        return []


def scrape_sygm_daily_report() -> List[Dict[str, Any]]:
    """
    Outlook üzerinden son SYGM raporunu tespit eder, bağlantıyı açar ve haberleri döner.
    """
    logger.info("Outlook üzerinden SYGM Medya Raporu e-postası aranıyor...")
    email_res = get_latest_sygm_email_from_outlook()
    
    report_url = None
    if email_res:
        subj, rec_time, html_body = email_res
        report_url = extract_report_url_from_html(html_body)
        
    cache_file = Path(__file__).resolve().parent.parent / "data" / "sygm_last_report_url.txt"
    if not report_url and cache_file.exists():
        report_url = cache_file.read_text(encoding="utf-8").strip()
        logger.info(f"Önbellekten SYGM Rapor URL'si kullanılıyor: {report_url}")
        
    if not report_url:
        logger.warning("SYGM Medya Raporu bağlantısı tespit edilemedi.")
        return []
        
    logger.info(f"Kullanılan Medya Raporu URL'si: {report_url}")
    
    # URL'i yerel önbelleğe kaydet
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(report_url, encoding="utf-8")
    except Exception:
        pass
        
    return fetch_interpress_media_report(report_url)
