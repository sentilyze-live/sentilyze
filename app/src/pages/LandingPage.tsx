import React from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, Shield, Zap, BarChart3, ArrowRight, Coins, Bell } from 'lucide-react';

const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen relative">
      {/* Video Background */}
      <div className="fixed inset-0 z-0">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-cover brightness-[0.8]"
        >
          <source src="/background.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-gradient-to-b from-[var(--bg-primary)]/40 via-[var(--bg-primary)]/30 to-[var(--bg-primary)]/50" />
        <div className="absolute inset-0 bg-gradient-radial from-[var(--aurora-primary)]/8 via-transparent to-transparent" />
      </div>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[var(--bg-primary)]/70 backdrop-blur-lg border-b border-white/40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-white drop-shadow-lg">SENTILYZE</span>
          </div>
          <nav className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-gray-300 hover:text-white transition-colors drop-shadow-md">Özellikler</a>
            <a href="#markets" className="text-gray-300 hover:text-white transition-colors drop-shadow-md">Piyasalar</a>
            <a href="#about" className="text-gray-300 hover:text-white transition-colors drop-shadow-md">Hakkımızda</a>
          </nav>
          <div className="flex items-center gap-4">
            <Link
              to="/app"
              className="px-6 py-2.5 rounded-lg bg-white/15 text-white font-medium hover:bg-white/25 transition-colors border border-white/40 backdrop-blur-sm drop-shadow-lg"
            >
              Giriş Yap
            </Link>
            <Link
              to="/app"
              className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold hover:from-blue-400 hover:to-purple-500 transition-all shadow-lg shadow-blue-500/30"
            >
              Hemen Başla
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6 relative z-10">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/20 border border-blue-500/40 mb-6 backdrop-blur-sm">
                <Zap className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-blue-300 font-medium drop-shadow-md">AI Powered Predictions</span>
              </div>
              <h1 className="text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight drop-shadow-lg">
                Altın ve Kripto
                <span className="block bg-gradient-to-r from-blue-400 via-purple-400 to-blue-400 bg-clip-text text-transparent">Piyasa Analizi</span>
              </h1>
              <p className="text-xl text-gray-200 mb-8 leading-relaxed drop-shadow-md">
                Yapay zeka destekli tahminler, gerçek zamanlı piyasa verileri ve profesyonel analiz araçları ile yatırımlarınızı bir adım öne taşıyın.
              </p>
              <div className="flex flex-wrap gap-4">
                <Link
                  to="/app"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold text-lg hover:from-blue-400 hover:to-purple-500 transition-all shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50"
                >
                  Analiz Panelini Aç
                  <ArrowRight className="w-5 h-5" />
                </Link>
                <Link
                  to="/admin"
                  className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-white/10 text-white font-medium text-lg hover:bg-white/20 transition-colors border border-white/20 backdrop-blur-sm"
                >
                  Admin Paneli
                </Link>
              </div>
            </div>
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-500/30 to-purple-500/30 rounded-3xl blur-3xl" />
              <div className="relative bg-[var(--bg-secondary)]/50 rounded-3xl border border-white/40 p-8 backdrop-blur-lg shadow-2xl">
                <div className="flex items-center gap-4 mb-6">
                  <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-rose-500" />
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <div className="w-3 h-3 rounded-full bg-emerald-500" />
                  </div>
                  <span className="text-sm text-gray-300">sentilyze.live</span>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--bg-secondary)]/60 border border-white/30 backdrop-blur-md">
                    <div className="flex items-center gap-3">
                      <Coins className="w-8 h-8 text-blue-400" />
                      <div>
                        <p className="text-white font-semibold drop-shadow-md">Altın (XAU/USD)</p>
                        <p className="text-sm text-gray-400">Gram Altın</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-white font-bold drop-shadow-md">₺2.847,45</p>
                      <p className="text-sm text-emerald-400">+2.34%</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--bg-secondary)]/60 border border-white/30 backdrop-blur-md">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center">
                        <span className="text-white font-bold text-sm">₿</span>
                      </div>
                      <div>
                        <p className="text-white font-semibold drop-shadow-md">Bitcoin (BTC)</p>
                        <p className="text-sm text-gray-400">USD</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-white font-bold drop-shadow-md">$43.234</p>
                      <p className="text-sm text-emerald-400">+5.67%</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-6 relative z-10">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-4xl font-bold text-white text-center mb-4 drop-shadow-lg">Neden Sentilyze?</h2>
          <p className="text-gray-300 text-center mb-12 max-w-2xl mx-auto drop-shadow-md">
            En gelişmiş yapay zeka teknolojileri ile piyasaları analiz edin, doğru zamanda doğru kararları verin.
          </p>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-[var(--bg-secondary)]/55 rounded-2xl p-8 border border-white/40 hover:border-[var(--aurora-primary)]/70 transition-all backdrop-blur-lg hover:bg-[var(--bg-secondary)]/70 shadow-2xl">
              <div className="w-14 h-14 rounded-xl bg-blue-500/30 flex items-center justify-center mb-6 shadow-lg">
                <BarChart3 className="w-7 h-7 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3 drop-shadow-md">AI Tahminleri</h3>
              <p className="text-gray-200">
                LSTM, ARIMA ve XGBoost modelleri ile altın ve kripto para fiyat tahminleri. Dakikalar içinde güncellenen veriler.
              </p>
            </div>
            <div className="bg-[var(--bg-secondary)]/55 rounded-2xl p-8 border border-white/40 hover:border-[var(--aurora-primary)]/70 transition-all backdrop-blur-lg hover:bg-[var(--bg-secondary)]/70 shadow-2xl">
              <div className="w-14 h-14 rounded-xl bg-blue-500/30 flex items-center justify-center mb-6 shadow-lg">
                <TrendingUp className="w-7 h-7 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3 drop-shadow-md">Teknik Analiz</h3>
              <p className="text-gray-200">
                RSI, MACD, Bollinger Bands ve daha fazlası. Profesyonel teknik analiz araçları ile piyasayı okuyun.
              </p>
            </div>
            <div className="bg-[var(--bg-secondary)]/55 rounded-2xl p-8 border border-white/40 hover:border-[var(--aurora-primary)]/70 transition-all backdrop-blur-lg hover:bg-[var(--bg-secondary)]/70 shadow-2xl">
              <div className="w-14 h-14 rounded-xl bg-blue-500/30 flex items-center justify-center mb-6 shadow-lg">
                <Bell className="w-7 h-7 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3 drop-shadow-md">Akıllı Alarmlar</h3>
              <p className="text-gray-200">
                Belirlediğiniz fiyat seviyelerine ulaşıldığında anında Telegram bildirimi alın. Hiçbir fırsatı kaçırmayın.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-white/10 relative z-10 bg-black/40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white drop-shadow-md">SENTILYZE</span>
          </div>
          <p className="text-gray-400 text-sm">
            © 2024 Sentilyze. Tüm hakları saklıdır.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
