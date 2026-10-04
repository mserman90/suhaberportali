import re
import base64
import requests
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

logger = logging.getLogger("image_enricher")

# Curated, high-resolution water journalism photographs categorized by theme
THEMATIC_IMAGES = {
    "Tarımsal Sulama": [
        "https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=900&q=80",  # Pivot sprinkler
        "https://images.unsplash.com/photo-1592417817098-8f3d69104a47?w=900&q=80",  # Drip irrigation
        "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?w=900&q=80",  # Irrigation canal
        "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=900&q=80",  # Precision moisture monitoring
        "https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=900&q=80",  # Modern watering channel
        "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=900&q=80",  # Sprinklers in crop field
    ],
    "Su Teknolojileri": [
        "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=900&q=80",  # Wastewater aeration tank
        "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=900&q=80",  # Water pipes and filtration
        "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=900&q=80",  # Water quality lab testing
        "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=900&q=80",  # Smart water meters
        "https://images.unsplash.com/photo-1541888946425-d0fbb18f15f7?w=900&q=80",  # Clarifier settlement tanks
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=900&q=80",  # High-pressure desalination
        "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?w=900&q=80",  # Pipeline engineering sensor
    ],
    "İklim & Kuraklık": [
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=900&q=80",  # Cracked soil in drought
        "https://images.unsplash.com/photo-1547683905-f686c993aae5?w=900&q=80",  # Flood river management
        "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?w=900&q=80",  # Dam spillway release
        "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=900&q=80",  # Reservoir low water marks
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=900&q=80",  # River valley weather storm
        "https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=900&q=80",  # Arid climate terrain
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=900&q=80",  # Climate atmosphere view
    ],
    "Su Politikaları": [
        "https://images.unsplash.com/photo-1511578314322-379afb476865?w=900&q=80",  # Conference hall delegates
        "https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=900&q=80",  # Transboundary river bridge
        "https://images.unsplash.com/photo-1497366216548-37526070297c?w=900&q=80",  # Strategic planning boardroom
        "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=900&q=80",  # Climate summit delegates
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=900&q=80",  # Public infrastructure governance
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=900&q=80",  # Environmental policy document
        "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=900&q=80",  # Civic water infrastructure
    ],
    "Su Kaynakları": [
        "https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=900&q=80",  # Mountain river stream
        "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=900&q=80",  # Reservoir lake in forest
        "https://images.unsplash.com/photo-1544717305-2782549b5136?w=900&q=80",  # Pure water droplet rings
        "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=900&q=80",  # Winding river basin
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=900&q=80",  # Freshwater wetland
        "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=900&q=80",  # Clean waterfall basin
        "https://images.unsplash.com/photo-1483921020237-2ff51e8e4b22?w=900&q=80",  # Glacier freshwater melt
        "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=900&q=80",  # River estuary
    ],
    "Türkiye": [
        "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=900&q=80",  # Reservoir dam water
        "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=900&q=80",  # Agricultural field irrigation
        "https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=900&q=80",  # Pivot sprinkler irrigation
        "https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=900&q=80",  # Irrigation canal
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=900&q=80",  # River valley basin
        "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?w=900&q=80",  # Dam spillway
        "https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=900&q=80",  # Anatolian mountain river
        "https://images.unsplash.com/photo-1544717305-2782549b5136?w=900&q=80",  # Clear water droplet
    ],
    "Akademik Yayınlar": [
        "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=900&q=80",  # Scientific laboratory chemistry
        "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=900&q=80",  # Academic microscope research
        "https://images.unsplash.com/photo-1518152006812-edab29b069ac?w=900&q=80",  # Hydrological digital models and data
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=900&q=80",  # Remote sensing earth observation
        "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=900&q=80",  # Water quality laboratory testing
        "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=900&q=80",  # Environmental engineering testing
    ]
}

def unwrap_inoreader_camo(url: str) -> Optional[str]:
    """Decodes Inoreader camo proxy URLs to recover the direct high-res publisher image."""
    if not url or "inoreader.com/camo/" not in url:
        return url if (url and url.startswith("http")) else None

    # Base64 encoded destination in camo URL
    if ",b64/" in url:
        b64_part = url.split(",b64/")[1].split(",")[0].split("?")[0].strip()
        b64_part += "=" * ((4 - len(b64_part) % 4) % 4)
        try:
            decoded = base64.urlsafe_b64decode(b64_part).decode("utf-8")
            if decoded.startswith("http"):
                return decoded
        except Exception:
            pass

    # Direct embedded http/https path in camo URL
    m = re.search(r'/(https?)/([^,]+)', url)
    if m:
        return m.group(1) + "://" + m.group(2)

    return None

def fetch_og_image(url: str, timeout: int = 5) -> Optional[str]:
    """Scrapes OpenGraph or Twitter Card image from the publisher's web page."""
    if not url or not url.startswith("http"):
        return None

    # Skip Google News redirect URLs because they require dynamic JavaScript rendering
    if "news.google.com" in url:
        return None

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            og = (
                soup.find("meta", property="og:image") or
                soup.find("meta", attrs={"name": "og:image"}) or
                soup.find("meta", attrs={"name": "twitter:image"}) or
                soup.find("meta", property="twitter:image")
            )
            if og and og.get("content"):
                img_url = og["content"].strip()
                if img_url.startswith("http"):
                    return img_url
    except Exception as e:
        logger.debug("Failed to fetch og:image from %s: %s", url, e)

    return None

def get_thematic_image(title: str, category: str, seed_index: int = 0) -> str:
    """Selects a topic-matched high-definition photograph based on title keywords and category."""
    title_lower = (title or "").lower()

    # Sub-keyword refinement for precise visual matching
    if category == "Akademik Yayınlar" or re.search(r'\b(akademik|makale|hakemli|sciencedirect|springer|mdpi|wiley|dergipark|journal|paper|study|thesis|research)\b', title_lower):
        category = "Akademik Yayınlar"
    elif category == "Türkiye" or re.search(r'\b(türkiye|turkey|türk|dsi|baraj|iski|aski|izsu|gap|anadolu|fırat|dicle|kızılırmak|meriç|gediz|menderes|sakarya|van gölü|tuz gölü|beyşehir|eğirdir)\b', title_lower):
        category = "Türkiye"
    elif re.search(r'\b(damla|pivot|fıskiye|tarla|mahsul|hasat|sulama|sprinkler|drip|crop)\b', title_lower):
        category = "Tarımsal Sulama"
    elif re.search(r'\b(arıtma|kanalizasyon|boru|şebeke|sayaç|sensör|filtrasyon|wastewater|leak|pipe)\b', title_lower):
        category = "Su Teknolojileri"
    elif re.search(r'\b(kuraklık|taşkın|sel|baraj|iklim|yağış|fırtına|flood|drought|climate)\b', title_lower):
        category = "İklim & Kuraklık"
    elif re.search(r'\b(politika|yasa|bakanlık|anlaşma|mevzuat|zirve|forum|diplomasi|hukuk)\b', title_lower):
        category = "Su Politikaları"

    pool = THEMATIC_IMAGES.get(category, THEMATIC_IMAGES["Su Kaynakları"])
    return pool[seed_index % len(pool)]

def resolve_article_image(item: Dict[str, Any], index: int = 0) -> str:
    """
    Resolves the best available image URL for an article:
    1. Unwraps Inoreader camo proxy URLs.
    2. Fetches og:image from original article URL if from direct publishers.
    3. Falls back to a curated, high-definition topic-matched photograph.
    """
    raw_img = (item.get("image_url") or "").strip()
    link = (item.get("link") or "").strip()
    title = item.get("title_tr") or item.get("title") or ""
    category = item.get("category_tr") or "Su Kaynakları"
    if item.get("is_academic"):
        category = "Akademik Yayınlar"

    # 1. Check if raw image is an Inoreader camo proxy
    if raw_img:
        unwrapped = unwrap_inoreader_camo(raw_img)
        if unwrapped:
            return unwrapped

    # 2. Try fetching og:image from the article link for direct publishers
    if link and ("wwt-online.de" in link or "iwmi.org" in link or "waterfm.com" in link):
        direct_img = fetch_og_image(link)
        if direct_img:
            return direct_img

    # 3. If raw image is a valid non-camo http URL, use it
    if raw_img and raw_img.startswith("http") and "inoreader.com/camo" not in raw_img:
        return raw_img

    # 4. Fallback to topic-matched thematic image
    return get_thematic_image(title, category, index)
