import { useEffect, useState, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Toaster } from 'sonner';
import Navigation from './sections/Navigation';
import Hero from './sections/Hero';
import HowItWorks from './sections/HowItWorks';
import GoogleCloud from './sections/GoogleCloud';
import GoldAnalysis from './sections/GoldAnalysis';
import TechnologyStack from './sections/TechnologyStack';
import Footer from './sections/Footer';
import DashboardLayout from './components/DashboardLayout';
import GoldHeader from './components/gold/GoldHeader';
import PriceTable from './components/gold/PriceTable';
import PredictionTable from './components/gold/PredictionTable';
import GoldChart from './components/gold/GoldChart';
import TechnicalIndicators from './components/gold/TechnicalIndicators';
import SentimentPanel from './components/gold/SentimentPanel';
import NewsFeed from './components/gold/NewsFeed';
import SpikeAnalysis from './components/gold/SpikeAnalysis';
import './App.css';

gsap.registerPlugin(ScrollTrigger);

// Skip to content link for accessibility
const SkipToContent: React.FC = () => {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-500 focus:text-white focus:rounded-lg"
    >
      Ana içeriğe atla
    </a>
  );
};

const GoldDashboard: React.FC = () => {
  return (
    <DashboardLayout>
      <div className="min-h-screen bg-[var(--bg-primary)]">
        <GoldHeader />
        <main id="main-content" className="p-6">
          <PriceTable />
          <PredictionTable />
          <GoldChart />
          <TechnicalIndicators />
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <SentimentPanel />
            <NewsFeed />
          </div>
          <SpikeAnalysis />
        </main>
      </div>
    </DashboardLayout>
  );
};

const LandingPage: React.FC = () => {
  const [isLightMode, setIsLightMode] = useState(false);
  const mainRef = useRef<HTMLDivElement>(null);

  // Apply aurora theme for landing page
  useEffect(() => {
    document.documentElement.setAttribute('data-landing-theme', 'aurora');

    return () => {
      document.documentElement.removeAttribute('data-landing-theme');
    };
  }, []);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>('.reveal-section').forEach((section) => {
        gsap.fromTo(
          section,
          { opacity: 0.9, y: 30 },
          {
            opacity: 1,
            y: 0,
            duration: 0.6,
            ease: 'power2.out',
            scrollTrigger: {
              trigger: section,
              start: 'top 85%',
              toggleActions: 'play none none none',
            },
          }
        );
      });
    }, mainRef);

    return () => ctx.revert();
  }, []);

  const toggleTheme = () => {
    setIsLightMode(!isLightMode);
    document.documentElement.classList.toggle('light');
  };

  return (
    <div ref={mainRef} className="min-h-screen bg-[var(--void-black)]">
      <SkipToContent />
      <Navigation 
        isLightMode={isLightMode}
        onThemeToggle={toggleTheme}
      />
      
      <main id="main-content">
        <Hero />
        <HowItWorks />
        <GoogleCloud />
        <GoldAnalysis />
        <TechnologyStack />
      </main>
      
      <Footer />
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Toaster 
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
          },
        }}
      />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/app" element={<GoldDashboard />} />
        <Route path="/admin/*" element={<Navigate to="/admin/login" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
