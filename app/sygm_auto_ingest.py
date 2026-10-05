#!/usr/bin/env python3
"""
app/sygm_auto_ingest.py
Her sabah 10:00'da (veya çağrıldığında) Outlook üzerinden Su Yönetimi Genel Müdürlüğü
tarafından sygmpersonel@tarimorman.gov.tr adresinden gönderilen
'SU YÖNETİMİ GENEL MÜDÜRLÜĞÜ MEDYA RAPORU' e-postasını tespit eder,
içindeki 'Mail içeriğini görmek için lütfen tıklayınız' bağlantısındaki haberleri çeker,
veritabanına kaydeder, statik portalı günceller ve GitHub Pages'e dağıtır.
"""

import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Windows konsolunda UTF-8 çıktısını garantiye al
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Proje kök dizinini ekle
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import config
from app.storage import Storage
from app.sygm_scraper import (
    get_latest_sygm_email_from_outlook,
    extract_report_url_from_html,
    fetch_interpress_media_report,
    scrape_sygm_daily_report
)

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / "sygm_ingest.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(log_file), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("sygm_auto_ingest")

SYNC_HISTORY_FILE = BASE_DIR / "data" / "sygm_sync_history.json"


def load_sync_history() -> dict:
    if SYNC_HISTORY_FILE.exists():
        try:
            return json.loads(SYNC_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_sync_history(history: dict):
    SYNC_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def run_deployment():
    """
    Statik siteyi derler ve GitHub Pages'e yükler.
    """
    logger.info("[*] export_static.py çalıştırılıyor...")
    export_proc = subprocess.run(
        [sys.executable, str(BASE_DIR / "export_static.py")],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if export_proc.returncode != 0:
        logger.error(f"[!] export_static.py başarısız oldu:\n{export_proc.stderr}")
        return False
        
    logger.info("[+] export_static.py başarıyla tamamlandı.")
    
    # Git commit & push
    logger.info("[*] Değişiklikler GitHub'a gönderiliyor...")
    try:
        # Git add - Sadece veri ve kaynak kod dosyaları (dist hariç)
        subprocess.run(
            ["git", "add", "data/", "app/", "export_static.py"],
            cwd=str(BASE_DIR),
            check=True
        )
        today_str = datetime.now().strftime("%Y-%m-%d")
        commit_msg = f"feat(sygm): otomatik SYGM Medya Raporu haberleri yayınlandı ({today_str})"
        
        diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(BASE_DIR))
        if diff_check.returncode != 0:
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(BASE_DIR), check=True)
            logger.info("[+] Git commit oluşturuldu.")
        else:
            logger.info("[-] Commit edilecek yeni veri değişikliği yok.")
            
        # deploy.ps1 ile güvenli GitHub aktarımı
        deploy_script = BASE_DIR / "deploy.ps1"
        if deploy_script.exists():
            logger.info("[*] deploy.ps1 çalıştırılıyor...")
            deploy_proc = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(deploy_script)],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            if deploy_proc.returncode == 0:
                logger.info("[+] deploy.ps1 ile GitHub'a başarıyla aktarıldı!")
                return True
            else:
                logger.warning(f"deploy.ps1 uyarısı: {deploy_proc.stdout}")
                
        # Standart git push yedekleme
        push_proc = subprocess.run(["git", "push", "origin", "main"], cwd=str(BASE_DIR))
        return push_proc.returncode == 0
        
    except Exception as git_err:
        logger.error(f"[!] Git dağıtım hatası: {git_err}")
        return False


def main(wait_for_email_minutes: int = 30):
    logger.info("==================================================")
    logger.info("[*] SYGM Medya Raporu Otonom Yayın Servisi Başlatıldı")
    logger.info("==================================================")
    
    today_key = datetime.now().strftime("%Y-%m-%d")
    history = load_sync_history()
    
    if history.get("last_processed_date") == today_key and not os.getenv("FORCE_RUN"):
        logger.info(f"Bugünün ({today_key}) SYGM medya raporu zaten işlenmiş ve yayında. Çıkılıyor.")
        return 0

    report_url = None
    email_subj = None
    email_date = None
    
    # E-posta henüz gelmediyse belirtilen süre boyunca aralıklarla kontrol et
    start_wait = time.time()
    max_wait_seconds = wait_for_email_minutes * 60
    
    while True:
        email_res = get_latest_sygm_email_from_outlook()
        if email_res:
            subj, rec_time, html_body = email_res
            url = extract_report_url_from_html(html_body)
            if url:
                report_url = url
                email_subj = subj
                email_date = rec_time
                break
                
        elapsed = time.time() - start_wait
        if elapsed >= max_wait_seconds:
            logger.warning(f"Belirtilen bekleme süresi ({wait_for_email_minutes} dk) doldu, e-posta henüz gelmedi.")
            break
            
        logger.info(f"Bugünün e-postası henüz tespit edilemedi. 60 saniye sonra tekrar denenecek... (Geçen: {int(elapsed)} sn)")
        time.sleep(60)

    if not report_url:
        cache_file = BASE_DIR / "data" / "sygm_last_report_url.txt"
        if cache_file.exists():
            report_url = cache_file.read_text(encoding="utf-8").strip()
            logger.info(f"Önbellekteki rapor bağlantısı kullanılıyor: {report_url}")
        else:
            logger.error("[!] Hiçbir SYGM Medya Raporu bağlantısı bulunamadı.")
            return 1

    logger.info(f"[*] Rapor URL'si açılıyor ve haberler çekiliyor: {report_url}")
    items = fetch_interpress_media_report(report_url)
    
    if not items:
        logger.error("[!] Interpress sayfasından haber çekilemedi.")
        return 1
        
    logger.info(f"[+] Çekilen SYGM haber sayısı: {len(items)}")
    
    # Veritabanına kaydet
    storage = Storage(config.DB_PATH)
    new_count = storage.save_items(items)
    logger.info(f"[+] Veritabanına yeni eklenen/güncellenen haber sayısı: {new_count}")
    
    # Dağıtım yap (export_static + git push)
    success = run_deployment()
    
    if success:
        history["last_processed_date"] = today_key
        history["last_report_url"] = report_url
        history["last_item_count"] = len(items)
        history["last_updated_at"] = datetime.now().isoformat()
        save_sync_history(history)
        logger.info(f"[+] TEBRİKLER! {today_key} tarihli SYGM Medya Raporu portalda başarıyla yayınlandı!")
        logger.info("Portal adresi: https://mserman90.github.io/suhaberportali/")
        return 0
    else:
        logger.error("[!] Dağıtım sırasında hata meydana geldi.")
        return 1


if __name__ == "__main__":
    force = "--force" in sys.argv
    if force:
        os.environ["FORCE_RUN"] = "1"
    sys.exit(main(wait_for_email_minutes=0 if force else 30))
