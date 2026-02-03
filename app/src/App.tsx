import { useEffect, useState, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
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

const GoldDashboard: React.FC = () => {
  return (
    <DashboardLayout>
      <div className="min-h-screen bg-[#0B0F14]">
        <GoldHeader />
        <div className="p-6">
          <PriceTable />
          <PredictionTable />
          <GoldChart />
          <TechnicalIndicators />
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <SentimentPanel />
            <NewsFeed />
          </div>
          <SpikeAnalysis />
        </div>
      </div>
    </DashboardLayout>
  );
};

const LandingPage: React.FC = () => {
  const [isLightMode, setIsLightMode] = useState(false);
  const mainRef = useRef<HTMLDivElement>(null);

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
      <Navigation 
        isLightMode={isLightMode}
        onThemeToggle={toggleTheme}
      />
      
      <main>
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