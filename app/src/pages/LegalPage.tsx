import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Shield, FileText, AlertTriangle, Cookie } from 'lucide-react';

const legalPages: Record<string, { title: string; icon: React.ElementType; content: React.ReactNode }> = {
  privacy: {
    title: 'Gizlilik Politikası',
    icon: Shield,
    content: (
      <>
        <p className="text-sm text-[var(--text-muted)] mb-6">Son Güncelleme: 3 Şubat 2026</p>

        <h2>1. Giriş</h2>
        <p>Sentilyze ("biz", "bize", "bizim") olarak kullanıcılarımızın gizliliğine büyük önem veriyoruz. Bu Gizlilik Politikası, platformumuzu kullandığınızda kişisel verilerinizin nasıl toplandığını, kullanıldığını ve korunduğunu açıklamaktadır.</p>

        <h2>2. Topladığımız Veriler</h2>
        <h3>2.1 Hesap Bilgileri</h3>
        <ul>
          <li>E-posta adresi</li>
          <li>Kullanıcı adı</li>
          <li>Şifre (şifrelenmiş olarak)</li>
          <li>Kayıt tarihi</li>
        </ul>
        <h3>2.2 Kullanım Verileri</h3>
        <ul>
          <li>IP adresi</li>
          <li>Tarayıcı bilgisi</li>
          <li>İşletim sistemi</li>
          <li>Erişim zamanları</li>
          <li>Görüntülenen sayfalar</li>
        </ul>

        <h2>3. Veri Kullanımı</h2>
        <p>Topladığımız verileri şu amaçlarla kullanıyoruz:</p>
        <ul>
          <li>Hesap oluşturma ve yönetimi</li>
          <li>Platform hizmetlerinin sağlanması</li>
          <li>Kullanıcı deneyiminin iyileştirilmesi</li>
          <li>Güvenlik ve dolandırıcılık önleme</li>
          <li>Yasal yükümlülüklerin yerine getirilmesi</li>
        </ul>

        <h2>4. Veri Paylaşımı</h2>
        <p>Kişisel verilerinizi hizmet sağlayıcılar (Google Cloud, analitik, e-posta), yasal gereklilikler (mahkeme kararları, kolluk kuvvetleri) ve iş transferi durumlarında paylaşabiliriz.</p>

        <h2>5. Veri Güvenliği</h2>
        <ul>
          <li>SSL/TLS şifreleme</li>
          <li>Veri şifreleme (rest ve transit)</li>
          <li>Düzenli güvenlik denetimleri</li>
          <li>Erişim kontrolleri</li>
        </ul>

        <h2>6. Haklarınız</h2>
        <p>KVKK ve GDPR kapsamında erişim, düzeltme, silme, sınırlandırma, itiraz ve taşınabilirlik haklarına sahipsiniz.</p>

        <h2>7. Çerezler</h2>
        <p>Platformumuz zorunlu çerezler (oturum yönetimi, güvenlik), analitik çerezler ve tercih çerezleri kullanır. Tarayıcı ayarlarınızdan çerezleri reddedebilirsiniz. Detaylı bilgi için <a href="/legal/cookies" className="text-[var(--signal-cyan)] hover:underline">Çerez Politikamızı</a> inceleyebilirsiniz.</p>

        <h2>8. İletişim</h2>
        <p>Gizlilik politikası ile ilgili sorularınız için: <strong>contact@sentilyze.live</strong></p>
      </>
    ),
  },
  terms: {
    title: 'Kullanım Şartları',
    icon: FileText,
    content: (
      <>
        <p className="text-sm text-[var(--text-muted)] mb-6">Son Güncelleme: 3 Şubat 2026</p>

        <h2>1. Kabul Ediliş</h2>
        <p>Sentilyze platformunu ("Platform") kullanarak, bu Kullanım Şartlarını okuduğunuzu, anladığınızı ve kabul ettiğinizi beyan edersiniz.</p>

        <div className="bg-amber-900/20 border border-amber-700/30 rounded-lg p-4 my-4">
          <p className="text-amber-400 font-semibold mb-2">Önemli Beyan:</p>
          <ul className="text-amber-200/80">
            <li>Sentilyze bir yatırım danışmanlığı platformu değildir</li>
            <li>Platform, kullanıcılara yatırım tavsiyesi vermemektedir</li>
            <li>Sunulan tüm veriler bilgilendirme amaçlıdır ve kesinlik taşımaz</li>
            <li>Platform, 6362 sayılı SPK Kanunu kapsamında yatırım danışmanlığı faaliyeti yürütmemektedir</li>
          </ul>
        </div>

        <h2>2. Hizmet Tanımı</h2>
        <p>Platform pazar duygu analizi, yapay zeka destekli senaryo analizleri, teknik gösterge verileri ve haber/sosyal medya sentiment analizi sağlar. Yatırım tavsiyesi, alım/satım önerileri veya portföy yönetimi SAĞLAMAZ.</p>

        <h2>3. Kullanıcı Sorumluluğu</h2>
        <p>Tüm yatırım kararları tamamen kullanıcının sorumluluğundadır. Platform, kullanıcıların finansal kararları sonucu oluşabilecek zararlardan sorumlu değildir.</p>

        <h2>4. Fikri Mülkiyet</h2>
        <p>Platformdaki tüm içerik, yazılım, tasarım ve veriler Sentilyze'in fikri mülkiyetidir.</p>

        <h2>5. Sorumluluk Sınırlaması</h2>
        <p>Sentilyze, platformun kullanımından kaynaklanan doğrudan veya dolaylı zararlardan, veri kayıplarından veya iş kesintilerinden sorumlu tutulamaz.</p>

        <h2>6. İletişim</h2>
        <p>Kullanım şartları ile ilgili sorularınız için: <strong>contact@sentilyze.live</strong></p>
      </>
    ),
  },
  'risk-disclosure': {
    title: 'Risk Bildirimi',
    icon: AlertTriangle,
    content: (
      <>
        <p className="text-sm text-[var(--text-muted)] mb-6">Son Güncelleme: 3 Şubat 2026</p>

        <div className="bg-red-900/20 border border-red-700/30 rounded-lg p-4 my-4">
          <p className="text-red-400 font-bold">Kripto para birimleri, altın ve diğer emtia piyasalarına yatırım yapmak YÜKSEK RİSK içerir ve sermayenizin tamamını kaybetmenize neden olabilir.</p>
        </div>

        <h2>1. Platform Kısıtlamaları</h2>
        <h3>1.1 Yatırım Danışmanlığı Değildir</h3>
        <ul>
          <li>Sentilyze bir yatırım danışmanlığı platformu DEĞİLDİR</li>
          <li>6362 sayılı SPK Kanunu kapsamında faaliyet göstermemektedir</li>
          <li>Yatırım lisansına sahip değildir</li>
          <li>Profesyonel finansal tavsiye vermemektedir</li>
        </ul>

        <h3>1.2 Bilgilendirme Amaçlıdır</h3>
        <p>Platform tarafından sunulan tüm veriler sadece bilgilendirme amaçlıdır, yapay zeka modelleri tarafından üretilen senaryo analizleridir, kesinlik taşımaz ve hatalar içerebilir.</p>

        <h2>2. Pazar Riskleri</h2>
        <ul>
          <li><strong>Volatilite Riski:</strong> Kripto para ve emtia piyasaları aşırı volatilite gösterebilir</li>
          <li><strong>Likidite Riski:</strong> Bazı piyasalarda likidite düşebilir</li>
          <li><strong>Regülasyon Riski:</strong> Düzenleyici değişiklikler piyasaları etkileyebilir</li>
          <li><strong>Teknolojik Risk:</strong> Teknik aksaklıklar, siber saldırılar veya sistem hataları oluşabilir</li>
        </ul>

        <h2>3. Yapay Zeka Riskleri</h2>
        <ul>
          <li>AI modelleri hatalı tahminler üretebilir</li>
          <li>Geçmiş performans geleceği garanti etmez</li>
          <li>Model sınırlılıkları mevcuttur</li>
          <li>Veri kalitesi sonuçları etkileyebilir</li>
        </ul>

        <h2>4. Sorumluluk Reddi</h2>
        <p>Sentilyze, platformun kullanımından kaynaklanan herhangi bir mali kayıptan sorumlu değildir. Kullanıcılar kendi bağımsız araştırmalarını yapmalı ve lisanslı yatırım danışmanlarından profesyonel tavsiye almalıdır.</p>

        <h2>5. İletişim</h2>
        <p>Risk bildirimi ile ilgili sorularınız için: <strong>contact@sentilyze.live</strong></p>
      </>
    ),
  },
  cookies: {
    title: 'Çerez Politikası',
    icon: Cookie,
    content: (
      <>
        <p className="text-sm text-[var(--text-muted)] mb-6">Son Güncelleme: 6 Şubat 2026</p>

        <h2>1. Giriş</h2>
        <p>Sentilyze ("biz", "bize", "bizim") olarak, web sitemizde çerez (cookie) ve benzeri teknolojiler kullanıyoruz. Bu Çerez Politikası, hangi çerezleri kullandığımızı, neden kullandığımızı ve çerez tercihlerinizi nasıl yönetebileceğinizi açıklamaktadır.</p>

        <h2>2. Çerez Nedir?</h2>
        <p>Çerezler, web sitesini ziyaret ettiğinizde cihazınıza (bilgisayar, tablet, akıllı telefon) kaydedilen küçük metin dosyalarıdır. Çerezler, web sitesinin sizi tanımasını, tercihlerinizi hatırlamasını ve kullanıcı deneyiminizi iyileştirmesini sağlar.</p>

        <h2>3. Kullandığımız Çerezler</h2>

        <h3>3.1 Gerekli Çerezler (Her Zaman Aktif)</h3>
        <p>Bu çerezler web sitesinin temel işlevlerini yerine getirmesi için zorunludur ve devre dışı bırakılamazlar.</p>
        <ul>
          <li><strong>sentilyze-theme:</strong> Tema tercihinizi (karanlık/aydınlık mod) saklar. Süre: 1 yıl</li>
          <li><strong>sentilyze-cookie-consent:</strong> Çerez izin tercihlerinizi saklar. Süre: 1 yıl</li>
        </ul>

        <h3>3.2 Analitik Çerezler (İsteğe Bağlı)</h3>
        <p>Bu çerezler, web sitemizin nasıl kullanıldığını anlamamıza yardımcı olur. Toplanan veriler anonimdir ve kullanıcı deneyimini iyileştirmek için kullanılır.</p>
        <ul>
          <li><strong>_ga:</strong> Google Analytics tarafından kullanıcıları ayırt etmek için kullanılır. Süre: 2 yıl</li>
          <li><strong>_gid:</strong> Google Analytics tarafından kullanıcıları ayırt etmek için kullanılır. Süre: 24 saat</li>
          <li><strong>_gat:</strong> Google Analytics tarafından istek oranını sınırlamak için kullanılır. Süre: 1 dakika</li>
        </ul>

        <h3>3.3 Pazarlama Çerezleri (İsteğe Bağlı)</h3>
        <p>Bu çerezler, size ilgi alanlarınıza uygun reklamlar göstermek ve pazarlama kampanyalarının etkinliğini ölçmek için kullanılır. Şu anda bu kategoride aktif çerez bulunmamaktadır.</p>

        <h2>4. Yasal Dayanak</h2>
        <p>Çerez kullanımımız aşağıdaki yasal düzenlemelere uygundur:</p>
        <ul>
          <li><strong>KVKK Madde 10:</strong> Kişisel verilerin işlenmesi hakkında kullanıcıların bilgilendirilmesi</li>
          <li><strong>GDPR (EU) 2016/679:</strong> Avrupa Birliği Genel Veri Koruma Tüzüğü</li>
          <li><strong>ePrivacy Directive 2002/58/EC:</strong> Elektronik iletişimde gizlilik direktifi</li>
        </ul>

        <h2>5. Çerez Tercihlerinizi Yönetme</h2>
        <p>Çerez tercihlerinizi aşağıdaki yöntemlerle yönetebilirsiniz:</p>

        <h3>5.1 Sitemiz Üzerinden</h3>
        <ul>
          <li>Sayfanın alt kısmındaki "Cookie Settings" linkine tıklayarak tercihlerinizi değiştirebilirsiniz</li>
          <li>İsteğe bağlı çerezleri kategorilere göre açıp kapatabilirsiniz</li>
          <li>Tercihleriniz cihazınızda saklanır ve gelecekteki ziyaretlerinizde uygulanır</li>
        </ul>

        <h3>5.2 Tarayıcı Ayarları</h3>
        <p>Çoğu web tarayıcısı, çerezleri otomatik olarak kabul edecek şekilde ayarlanmıştır. Tarayıcı ayarlarınızdan çerezleri engelleyebilir veya silebilirsiniz:</p>
        <ul>
          <li><strong>Chrome:</strong> Ayarlar → Gizlilik ve güvenlik → Çerezler ve diğer site verileri</li>
          <li><strong>Firefox:</strong> Ayarlar → Gizlilik ve Güvenlik → Çerezler ve Site Verileri</li>
          <li><strong>Safari:</strong> Tercihler → Gizlilik → Çerezleri ve web sitesi verilerini yönet</li>
          <li><strong>Edge:</strong> Ayarlar → Gizlilik, arama ve hizmetler → Çerezler ve site izinleri</li>
        </ul>

        <div className="bg-amber-900/20 border border-amber-700/30 rounded-lg p-4 my-4">
          <p className="text-amber-400 font-semibold mb-2">Önemli Not:</p>
          <p className="text-amber-200/80">
            Çerezleri tamamen engellerseniz, web sitemizin bazı özellikleri düzgün çalışmayabilir.
            Gerekli çerezler her zaman aktiftir çünkü bunlar sitenin temel işlevselliği için zorunludur.
          </p>
        </div>

        <h2>6. Çerez Politikası Güncellemeleri</h2>
        <p>Bu Çerez Politikasını zaman zaman güncelleyebiliriz. Önemli değişiklikler olduğunda, web sitemizde bir bildirim yayınlayacağız. Sayfanın üst kısmındaki "Son Güncelleme" tarihine bakarak en son ne zaman güncellendiğini görebilirsiniz.</p>

        <h2>7. Haklarınız</h2>
        <p>KVKK ve GDPR kapsamında aşağıdaki haklara sahipsiniz:</p>
        <ul>
          <li><strong>Erişim Hakkı:</strong> Hangi çerezlerin kullanıldığını öğrenme</li>
          <li><strong>Düzeltme Hakkı:</strong> Çerez tercihlerinizi değiştirme</li>
          <li><strong>Silme Hakkı:</strong> Çerezleri silme (tarayıcı ayarlarından)</li>
          <li><strong>İtiraz Hakkı:</strong> İsteğe bağlı çerezleri reddetme</li>
          <li><strong>Veri Taşınabilirliği:</strong> Çerez verilerinizin bir kopyasını talep etme</li>
        </ul>

        <h2>8. Üçüncü Taraf Çerezleri</h2>
        <p>Bazı çerezler, Google Analytics gibi üçüncü taraf hizmet sağlayıcılar tarafından yerleştirilir. Bu çerezlerin kullanımı, ilgili üçüncü tarafların gizlilik politikalarına tabidir:</p>
        <ul>
          <li><strong>Google Analytics:</strong> <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-[var(--signal-cyan)] hover:underline">Google Gizlilik Politikası</a></li>
        </ul>

        <h2>9. İletişim</h2>
        <p>Çerez Politikamız hakkında sorularınız varsa, bizimle iletişime geçebilirsiniz:</p>
        <ul>
          <li><strong>E-posta:</strong> contact@sentilyze.live</li>
          <li><strong>Adres:</strong> Türkiye</li>
        </ul>

        <p className="text-sm text-[var(--text-muted)] mt-8">
          Bu Çerez Politikası, 6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) ve AB Genel Veri Koruma Tüzüğü (GDPR) uyarınca hazırlanmıştır.
        </p>
      </>
    ),
  },
};

const LegalPage = () => {
  const { type } = useParams<{ type: string }>();
  const navigate = useNavigate();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [type]);

  const page = type ? legalPages[type] : null;

  if (!page) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="text-center">
          <p className="text-[var(--text-muted)] mb-4">Page not found</p>
          <button
            onClick={() => navigate('/')}
            className="text-[var(--gold-primary)] hover:underline"
          >
            Return to home
          </button>
        </div>
      </div>
    );
  }

  const PageIcon = page.icon;

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Header */}
      <div className="border-b border-[var(--border-color)]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors mb-6"
          >
            <ArrowLeft size={16} />
            <span>Back to Home</span>
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[var(--gold-light)] flex items-center justify-center">
              <PageIcon size={20} className="text-[var(--gold-primary)]" />
            </div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">{page.title}</h1>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="prose prose-invert max-w-none
          [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-[var(--text-primary)] [&_h2]:mt-8 [&_h2]:mb-3
          [&_h3]:text-lg [&_h3]:font-medium [&_h3]:text-[var(--text-primary)] [&_h3]:mt-6 [&_h3]:mb-2
          [&_p]:text-[var(--text-secondary)] [&_p]:mb-4 [&_p]:leading-relaxed
          [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:mb-4 [&_ul]:space-y-1
          [&_li]:text-[var(--text-secondary)]
          [&_strong]:text-[var(--text-primary)]
        ">
          {page.content}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-[var(--border-color)] py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-sm text-[var(--text-muted)]">
            &copy; {new Date().getFullYear()} Sentilyze. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LegalPage;
