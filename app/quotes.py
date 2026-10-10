"""
app/quotes.py
Su yönetimi, su verimliliği, tarımsal sulama ve havza koruma konularında
günün öğüt niteliğindeki sözlerini sağlayan modül.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List

WATER_MANAGEMENT_QUOTES: List[Dict[str, str]] = [
    {
        "quote": "Tarımsal sulamada yapılacak her yüzde 10'luk verimlilik artışı, metropollerin yıllık içme suyu ihtiyacını karşılayabilecek ölçektedir. Akıllı sensörler ve damla sulama bir tercih değil, milli bir zorunluluktur.",
        "author": "Su Verimliliği ve Tarımsal Sulama Rehberi",
        "category": "Tarımsal Sulama"
    },
    {
        "quote": "Suyu atalarımızdan miras almadık, gelecek nesillerden ödünç aldık. Havzalarımızdaki her bir damlayı yarının emaneti bilinciyle yönetmek zorundayız.",
        "author": "Sürdürülebilir Havza Yönetimi İlkesi",
        "category": "Gelecek & Koruma"
    },
    {
        "quote": "Yeraltı suları sınırsız bir kaynak değil, kuraklık yıllarının stratejik güvenlik sigortasıdır. Akiferlerimizi aşırı çekimden korumak gıda güvenliğimizin teminatıdır.",
        "author": "Hidrojeoloji ve Yeraltı Suları Bilinci",
        "category": "Yeraltı Suları"
    },
    {
        "quote": "Bir damla suyun yönetimi, bir milletin geleceğinin yönetimidir. Kuraklık kapıyı çalmadan önce alınan tedbirler, kriz anındaki çaresiz çabalardan bin kat daha kıymetlidir.",
        "author": "Entegre Su Politikaları Masası",
        "category": "Stratejik Yönetim"
    },
    {
        "quote": "Vahşi sulama sadece suyu değil, toprağın en verimli organik katmanını ve mineral zenginliğini de alıp götürür. Toprağı korumak, suyu damla damla vermekten geçer.",
        "author": "Toprak ve Su Koruma Öğüdü",
        "category": "Tarımsal Sulama"
    },
    {
        "quote": "Arıtılmış atık suların tarımsal sulama ve sanayide yeniden kullanımı, su kıtlığı çeken havzalarda can simididir. Döngüsel su ekonomisi geleceğin anahtarıdır.",
        "author": "Döngüsel Su Ekonomisi Raporu",
        "category": "Geri Kazanım"
    },
    {
        "quote": "Gökyüzünden düşen her yağmur damlasını betonla denize akıtmak yerine; yağmur hasadı, sünger şehirler ve taşkın göletleriyle toprakla buluşturmalıyız.",
        "author": "Kentsel Su ve İklim Direnci İlkeleri",
        "category": "Yağmur Hasadı"
    },
    {
        "quote": "Su ayak izinizi küçültmek, musluğu kısmaktan fazlasıdır; ne tükettiğimizin, ne ektiğimizin ve nasıl ürettiğimizin farkında olmakla başlar.",
        "author": "Su Ayak İzi ve Tüketim Bilinci",
        "category": "Bilinçli Tüketim"
    },
    {
        "quote": "Nehirler sadece su akıtmaz; bir havzanın can damarı, biyoçeşitliliğin yuvası ve medeniyetlerin taşıyıcısıdır. Nehir yataklarına müdahale ederken doğanın hakkını gözetmeliyiz.",
        "author": "Ekolojik Akış ve Nehir Havzası Etiği",
        "category": "Havza Koruma"
    },
    {
        "quote": "Kurak havzalarda çok su tüketen ürün deseni seçmek, geleceği bugünden tüketmektir. Havza bazlı doğru ürün planlaması su tasarrufunun temelidir.",
        "author": "Tarımsal Planlama ve Havza Dengesi",
        "category": "Ürün Deseni"
    },
    {
        "quote": "Su kayıp ve kaçak oranlarını düşürmeyen bir şehir şebekesi, delik bir kovaya su doldurmaya benzer. Altyapıyı yenilemek, yeni baraj yapmaktan daha etkilidir.",
        "author": "Kentsel Su Altyapısı İlkeleri",
        "category": "Şebeke Yönetimi"
    },
    {
        "quote": "Suyun zenginliği debisinde değil, akılcı ve adil paylaşımındadır. Sektörler arası su tahsisinde bilimi ve adaleti rehber edinmeliyiz.",
        "author": "Adil Su Tahsisi ve Yönetişim",
        "category": "Su Yönetişimi"
    },
    {
        "quote": "Barajlarımızdaki su seviyesini sadece yağışlar değil, havzada yaşayan her bir bireyin su tasarrufu kültürü belirler.",
        "author": "Toplumsal Su Seferberliği",
        "category": "Tasarruf Kültürü"
    },
    {
        "quote": "Toprağın nemini ölçmeden yapılan sulama, hem bitkiye hem de su bütçesine yüktür. Dijital tarım ve hassas sulama teknolojileri su israfının panzehiridir.",
        "author": "Akıllı Tarım ve Sensör Teknolojileri",
        "category": "Teknoloji"
    },
    {
        "quote": "Sulak alanları kurutmak, havzanın doğal böbreklerini ve iklim regülatörlerini yok etmektir. Göllerimizi ve bataklıklarımızı korumak iklim krizine karşı ilk kalkanımızdır.",
        "author": "Sulak Alanlar ve Ekolojik Denge",
        "category": "Sulak Alanlar"
    },
    {
        "quote": "Su krizi bir gün aniden gelmez; yıllar süren ihmallerin, plansız tüketimin ve ertelemelerin sonucu olarak sessizce kapıyı çalar. Tedbir bugündür.",
        "author": "Kuraklık Erken Uyarı Sistemi",
        "category": "Kriz Önleme"
    },
    {
        "quote": "Bir damla suyun toprağa sızması yıllar alır, ancak kontrolsüz bir kuyu onu dakikalar içinde tüketebilir. Kaçak sondajlar yer altının gizli felaketidir.",
        "author": "Yeraltı Su Kaynakları Koruma Masası",
        "category": "Yeraltı Suları"
    },
    {
        "quote": "Sanayide her metreküp suyun kapalı devre sistemlerle defalarca kullanımı, hem sanayicinin maliyetini düşürür hem de nehirlerimizi kirlilikten korur.",
        "author": "Yeşil Sanayi ve Endüstriyel Su Verimliliği",
        "category": "Sanayi Verimliliği"
    },
    {
        "quote": "Ormanlar suyun yeryüzündeki en büyük süngeridir. Ağaçlandırma sadece erozyonu önlemez; temiz içme suyu havzalarının devamlılığını sağlar.",
        "author": "Orman ve Havza Hidrolojisi",
        "category": "Havza Koruma"
    },
    {
        "quote": "Su bilinci okullarda çocuklukta başlamalı, tarlada çiftçiyle, fabrikada mühendisle olgunlaşmalıdır. Bilinçsiz su yönetimi hiçbir kanunla tam olarak çözülemez.",
        "author": "Su Okuryazarlığı ve Eğitim",
        "category": "Eğitim & Kültür"
    },
    {
        "quote": "İklim değişikliği su rejimini hızla değiştiriyor; artık geçmişin yağış ortalamalarıyla geleceğin su politikaları inşa edilemez. Dinamik ve esnek yönetim şarttır.",
        "author": "İklim Değişikliği ve Hidrolojik Uyum",
        "category": "İklim Uyumu"
    },
    {
        "quote": "Suyu kaynağında temiz tutmak, kirlettikten sonra ileri arıtma tesisleriyle temizlemeye çalışmaktan yüz kat daha ucuz ve sürdürülebilirdir.",
        "author": "Su Kirliliğini Önleme İlkesi",
        "category": "Kirlilik Önleme"
    },
    {
        "quote": "Gece sulaması yapmak buharlaşma kaybını yarı yarıya azaltır. Doğanın döngüsüne uyumlu sulama takvimleri, bedelsiz ve anında su tasarrufudur.",
        "author": "Çiftçi Su Yönetimi Rehberi",
        "category": "Tarımsal Sulama"
    },
    {
        "quote": "Su kaynaklarının korunması sadece bir çevre meselesi değil; doğrudan ulusal güvenlik, bağımsızlık ve gıda egemenliği meselesidir.",
        "author": "Stratejik Su Güvenliği Doktrini",
        "category": "Ulusal Güvenlik"
    },
    {
        "quote": "Kuraklık dönemlerinde su kısıtı uygulamak geç kalmış bir adımdır; asıl marifet bereketli yıllarda su hasadı yapıp rezervleri dolu tutmaktır.",
        "author": "Su Güvenliği ve Rezerv Yönetimi",
        "category": "Rezerv Yönetimi"
    },
    {
        "quote": "Her dere yatağı milyonlarca yıldır kendi yolunu çizer. Dere yataklarını daraltmak veya kapatmak, ilk büyük yağışta felakete davetiye çıkarmaktır.",
        "author": "Taşkın ve Havza Mühendisliği",
        "category": "Taşkın Yönetimi"
    },
    {
        "quote": "Kırsal alanda kapalı basınçlı boru sistemlerine geçilmedikçe, açık kanallarda buharlaşan ve sızan her damla milli servetin kaybıdır.",
        "author": "DSİ Modern Sulama Sistemleri Vizyonu",
        "category": "Sulama Altyapısı"
    },
    {
        "quote": "Su tasarrufu fedakarlık değil, yarın susuz kalmamak için bugün atılan en rasyonel ve kazançlı yatırımdır.",
        "author": "Su Verimliliği Seferberliği",
        "category": "Verimlilik"
    },
    {
        "quote": "Akarsuların doğduğu kaynak noktalarından döküldüğü denizlere kadar bir bütün olarak yönetilmediği hiçbir model başarılı olamaz.",
        "author": "Entegre Nehir Havzası Yönetim Planı (ENHYP)",
        "category": "Havza Planlama"
    },
    {
        "quote": "Toprak organik maddesi yüksek olan tarla, suyu sünger gibi tutar; organik maddesi fakir toprak ise suyu hızla kaybeder. Suyu tutmak toprağı beslemekle başlar.",
        "author": "Onarıcı Tarım ve Toprak Nemi Yönetimi",
        "category": "Toprak Sağlığı"
    },
    {
        "quote": "Bir litre kullanılmış motor yağı veya kimyasal atık, bir milyon litre temiz yer altı suyunu zehirleyebilir. Suyu korumak, toprağa ne döktüğümüzü bilmektir.",
        "author": "Çevre Koruma ve Akifer Güvenliği",
        "category": "Akifer Güvenliği"
    },
    {
        "quote": "Geleceğin şehirleri, suyu dışarıdan getiren değil; tükettiği suyu yerinde arıtıp dönüştüren ve yağmurunu depolayan akıllı şehirler olacaktır.",
        "author": "Geleceğin Akıllı Şehirleri Su Raporu",
        "category": "Akıllı Şehirler"
    },
    {
        "quote": "Su kaynaklarını yönetirken sadece insan ihtiyaçlarını değil; havzadaki börtü böceğin, balıkların ve ormanların su hakkını da teslim etmeliyiz.",
        "author": "Ekolojik Hakkaniyet ve Can Suyu İlkesi",
        "category": "Can Suyu"
    },
    {
        "quote": "Barajlardaki buharlaşmayı azaltan yüzer güneş enerjisi panelleri, hem temiz enerji üretir hem de suyun buharlaşarak kaybolmasını önler. İkili fayda, geleceğin mühendisliğidir.",
        "author": "Yenilikçi Su ve Enerji Teknolojileri",
        "category": "Yenilikçi Teknoloji"
    },
    {
        "quote": "Su yönetiminde en pahalı çözüm, hiçbir şey yapmayıp kriz anında su taşımak veya tankerlerle çare aramaktır. En ucuz çözüm ise tasarruftur.",
        "author": "Su Ekonomisi ve Kriz Maliyeti",
        "category": "Su Ekonomisi"
    },
    {
        "quote": "Kurakçıl peyzaj (xeriscaping), şehir parklarında ve refüjlerde içme suyuyla çim sulama israfına son veren en estetik ve akılcı su yönetimidir.",
        "author": "Kentsel Yeşil Alan ve Kurakçıl Peyzaj",
        "category": "Kentsel Tasarruf"
    },
    {
        "quote": "Bir göl kuruduğunda sadece su kaybolmaz; o bölgenin mikroiklimi, tarımı, balıkçılığı ve çocukların geleceği de kurur. Göllerimizi yaşatmak vatani görevdir.",
        "author": "Sulak Alanlar ve Doğa Koruma Çağrısı",
        "category": "Göl Koruma"
    },
    {
        "quote": "Akıllı sayaçlar ve scada sistemleri ile donatılmayan içme suyu şebekelerinde sızıntılar görünmez bir hırsız gibidir; dijitalleşme suyun koruyucusudur.",
        "author": "Dijital Su Şebekeleri ve SCADA Yönetimi",
        "category": "Dijitalleşme"
    },
    {
        "quote": "Gıda israfı, aynı zamanda o gıdayı üretmek için harcanan yüzlerce metreküp suyun çöpe atılması demektir. Tabağındaki yemeği koruyan, suyu korur.",
        "author": "Gıda-Su Bağı ve Sürdürülebilirlik",
        "category": "Gıda-Su Bağı"
    },
    {
        "quote": "Tuzlanma ve çoraklaşma, aşırı ve yanlış sulamanın bereketli ovalara vurduğu en acı darbedir. Ölçülü su, ömür boyu bereket getirir.",
        "author": "Tarımsal Drenaj ve Tuzluluk Kontrolü",
        "category": "Toprak Koruma"
    },
    {
        "quote": "Suyu yönetmek doğayı fethetmek değil; doğanın hidrolojik döngüsünü anlayıp onunla barışık ve uyumlu bir yaşam kurabilmektir.",
        "author": "Doğa Temelli Su Çözümleri",
        "category": "Doğa Temelli Çözümler"
    },
    {
        "quote": "Her bireyin evinde yapacağı 1 dakikalık duş tasarrufu veya damlatan musluğu onarması, bir yılda barajlar dolusu suyun havzada kalmasını sağlar.",
        "author": "Bireysel Tasarruf ve Hanehalkı Su Rehberi",
        "category": "Evsel Tasarruf"
    }
]

def get_daily_water_quote(dt: datetime = None) -> Dict[str, str]:
    """
    Belirtilen tarihe (varsayılan: bugün UTC) göre 'Günün Sözü'nü deterministik olarak döndürür.
    Yılın gününe göre deterministik seçim yaparak her gün yeni ve farklı bir öğüt sunar.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    
    # Yılın günü (1-366) ve yıl bilgisi ile deterministik indeks hesabı
    day_of_year = dt.timetuple().tm_yday
    year = dt.year
    index = (day_of_year + (year * 7)) % len(WATER_MANAGEMENT_QUOTES)
    
    return WATER_MANAGEMENT_QUOTES[index]
