import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { 
  Database, 
  Brain, 
  TrendingUp, 
  Bell, 
  MessageSquare, 
  Twitter, 
  Zap,
  BarChart3,
  Cpu,
  Send
} from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const services = [
  {
    id: 1,
    port: '8081',
    title: 'Data Ingestion',
    description: 'Collects real-time data from Reddit API, Twitter API, Binance WebSocket, and GoldAPI.io',
    icon: Database,
    color: 'from-[var(--signal-cyan)] to-[var(--crypto-blue)]',
    technologies: [
      { icon: MessageSquare, label: 'Reddit' },
      { icon: Twitter, label: 'Twitter' },
      { icon: Zap, label: 'Binance' },
      { icon: Database, label: 'GoldAPI' },
    ],
    position: 'top-left',
  },
  {
    id: 2,
    port: '8082',
    title: 'Sentiment Processing',
    description: 'Vertex AI Gemini & Hugging Face Transformers analyze sentiment and extract entities',
    icon: Brain,
    color: 'from-[var(--lag-green)] to-[var(--signal-cyan)]',
    technologies: [
      { icon: Cpu, label: 'Vertex AI' },
      { icon: Brain, label: 'Hugging Face' },
    ],
    position: 'top-right',
  },
  {
    id: 3,
    port: '8083',
    title: 'Market Context',
    description: 'Technical indicators: RSI, MACD, Bollinger Bands. Bull/Bear regime detection',
    icon: BarChart3,
    color: 'from-[var(--amber-pulse)] to-[var(--lag-green)]',
    technologies: [
      { icon: TrendingUp, label: 'RSI/MACD' },
      { icon: BarChart3, label: 'Bollinger' },
    ],
    position: 'bottom-left',
  },
  {
    id: 4,
    port: '8084-8087',
    title: 'Prediction & Alerts',
    description: 'LSTM+ARIMA+XGBoost ensemble predictions. Telegram & Discord alerts',
    icon: Bell,
    color: 'from-[var(--gold-accent)] to-[var(--amber-pulse)]',
    technologies: [
      { icon: Brain, label: 'LSTM' },
      { icon: TrendingUp, label: 'ARIMA' },
      { icon: Send, label: 'Telegram' },
      { icon: MessageSquare, label: 'Discord' },
    ],
    position: 'bottom-right',
  },
];

const messageFlow = [
  { label: 'raw-market-data', color: 'var(--signal-cyan)' },
  { label: 'processed-sentiment', color: 'var(--lag-green)' },
  { label: 'market-context', color: 'var(--amber-pulse)' },
  { label: 'predictions', color: 'var(--gold-accent)' },
];

const HowItWorks = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const diagramRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Section header animation
      gsap.fromTo(
        '.hiw-header',
        { y: 50, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.6,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 80%',
          },
        }
      );

      // Central hub animation
      gsap.fromTo(
        '.central-hub',
        { scale: 0, rotateY: 180, opacity: 0 },
        {
          scale: 1,
          rotateY: 0,
          opacity: 1,
          duration: 0.8,
          ease: 'back.out(1.7)',
          scrollTrigger: {
            trigger: diagramRef.current,
            start: 'top 75%',
          },
        }
      );

      // Service nodes animation
      gsap.fromTo(
        '.service-node',
        { x: (i) => (i % 2 === 0 ? -100 : 100), opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.7,
          stagger: 0.15,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: diagramRef.current,
            start: 'top 70%',
          },
        }
      );

      // Connection lines animation
      gsap.fromTo(
        '.connection-line',
        { strokeDashoffset: 300 },
        {
          strokeDashoffset: 0,
          duration: 1,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: diagramRef.current,
            start: 'top 60%',
          },
        }
      );

      // Data packets animation
      gsap.to('.data-packet', {
        motionPath: {
          path: '.connection-path',
          align: '.connection-path',
          alignOrigin: [0.5, 0.5],
        },
        duration: 2,
        repeat: -1,
        ease: 'none',
        stagger: 0.5,
      });

      // Architectural patterns cards
      gsap.fromTo(
        '.pattern-card',
        { y: 40, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.5,
          stagger: 0.1,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: '.patterns-section',
            start: 'top 80%',
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      id="how-it-works"
      ref={sectionRef}
      className="py-24 relative overflow-hidden"
    >
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-[var(--void-black)] via-[var(--deep-slate)]/30 to-[var(--void-black)]" />

      <div className="section-container max-w-7xl mx-auto relative z-10">
        {/* Section Header */}
        <div className="hiw-header text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full bg-[var(--signal-cyan)]/10 text-[var(--signal-cyan)] text-xs font-medium uppercase tracking-wider mb-4">
            Architecture
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-[var(--soft-white)] mb-4">
            How Sentilyze Works
          </h2>
          <p className="text-lg text-[var(--cool-gray)] max-w-2xl mx-auto">
            Event-driven microservices architecture powered by Google Cloud
          </p>
        </div>

        {/* Architecture Diagram */}
        <div ref={diagramRef} className="relative mb-20">
          {/* Desktop Layout */}
          <div className="hidden lg:block">
            <div className="relative h-[600px]">
              {/* Central Hub - Pub/Sub */}
              <div className="central-hub absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
                <div className="relative">
                  {/* Rotating rings */}
                  <div className="absolute inset-0 w-64 h-64 -m-8">
                    <div className="absolute inset-0 rounded-full border border-[var(--signal-cyan)]/20 animate-[spin_20s_linear_infinite]" />
                    <div className="absolute inset-4 rounded-full border border-[var(--lag-green)]/20 animate-[spin_15s_linear_infinite_reverse]" />
                    <div className="absolute inset-8 rounded-full border border-[var(--amber-pulse)]/20 animate-[spin_25s_linear_infinite]" />
                  </div>
                  
                  {/* Hub content */}
                  <div className="relative w-48 h-48 rounded-2xl bg-[var(--deep-slate)] border border-[var(--signal-cyan)]/30 flex flex-col items-center justify-center glow-cyan">
                    <Send size={32} className="text-[var(--signal-cyan)] mb-3" />
                    <h3 className="text-lg font-semibold text-[var(--soft-white)] text-center">Pub/Sub</h3>
                    <p className="text-xs text-[var(--cool-gray)] text-center mt-1">Message Flow</p>
                  </div>

                  {/* Message flow labels */}
                  <div className="absolute -right-48 top-1/2 -translate-y-1/2 space-y-2">
                    {messageFlow.map((flow, i) => (
                      <div
                        key={flow.label}
                        className="flex items-center gap-2 text-xs"
                        style={{ animationDelay: `${i * 200}ms` }}
                      >
                        <div
                          className="w-2 h-2 rounded-full animate-pulse"
                          style={{ backgroundColor: flow.color, boxShadow: `0 0 8px ${flow.color}` }}
                        />
                        <span style={{ color: flow.color }}>{flow.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Service Nodes */}
              {services.map((service, index) => {
                const positions = [
                  'left-0 top-0',
                  'right-0 top-0',
                  'left-0 bottom-0',
                  'right-0 bottom-0',
                ];
                return (
                  <div
                    key={service.id}
                    className={`service-node absolute ${positions[index]} w-80`}
                  >
                    <div className="glass-card p-6 card-lift node-glow">
                      {/* Header */}
                      <div className="flex items-start justify-between mb-4">
                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${service.color} flex items-center justify-center`}>
                          <service.icon size={24} className="text-[var(--void-black)]" />
                        </div>
                        <span className="port-badge">Port {service.port}</span>
                      </div>

                      {/* Content */}
                      <h3 className="text-lg font-semibold text-[var(--soft-white)] mb-2">
                        {service.title}
                      </h3>
                      <p className="text-sm text-[var(--cool-gray)] mb-4">
                        {service.description}
                      </p>

                      {/* Technologies */}
                      <div className="flex flex-wrap gap-2">
                        {service.technologies.map((tech) => (
                          <div
                            key={tech.label}
                            className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-[var(--graphite-blue)] text-xs text-[var(--cool-gray)]"
                          >
                            <tech.icon size={12} />
                            <span>{tech.label}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Connection line to center */}
                    <svg
                      className="absolute top-1/2 left-1/2 w-full h-full pointer-events-none"
                      style={{
                        transform: index === 0 ? 'translate(160px, 50%)' :
                                  index === 1 ? 'translate(-100%, 50%) translateX(-160px)' :
                                  index === 2 ? 'translate(160px, -50%) translateY(-100%)' :
                                  'translate(-100%, -50%) translateX(-160px)'
                      }}
                    >
                      <line
                        className="connection-line"
                        x1="0"
                        y1="0"
                        x2={index === 0 || index === 2 ? '120' : '-120'}
                        y2={index === 0 || index === 1 ? '150' : '-150'}
                        stroke="url(#gradient)"
                        strokeWidth="2"
                        strokeDasharray="8 4"
                        fill="none"
                      />
                      <defs>
                        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="var(--signal-cyan)" stopOpacity="0.5" />
                          <stop offset="100%" stopColor="var(--lag-green)" stopOpacity="0.5" />
                        </linearGradient>
                      </defs>
                    </svg>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Mobile/Tablet Layout */}
          <div className="lg:hidden">
            {/* Central Hub */}
            <div className="central-hub flex justify-center mb-8">
              <div className="w-40 h-40 rounded-2xl bg-[var(--deep-slate)] border border-[var(--signal-cyan)]/30 flex flex-col items-center justify-center glow-cyan">
                <Send size={28} className="text-[var(--signal-cyan)] mb-2" />
                <h3 className="text-base font-semibold text-[var(--soft-white)]">Pub/Sub</h3>
                <p className="text-xs text-[var(--cool-gray)]">Message Flow</p>
              </div>
            </div>

            {/* Service Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {services.map((service) => (
                <div key={service.id} className="service-node">
                  <div className="glass-card p-5 card-lift">
                    <div className="flex items-start justify-between mb-3">
                      <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${service.color} flex items-center justify-center`}>
                        <service.icon size={20} className="text-[var(--void-black)]" />
                      </div>
                      <span className="port-badge">Port {service.port}</span>
                    </div>
                    <h3 className="text-base font-semibold text-[var(--soft-white)] mb-2">
                      {service.title}
                    </h3>
                    <p className="text-sm text-[var(--cool-gray)] mb-3">
                      {service.description}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {service.technologies.map((tech) => (
                        <div
                          key={tech.label}
                          className="flex items-center gap-1 px-2 py-0.5 rounded bg-[var(--graphite-blue)] text-xs text-[var(--cool-gray)]"
                        >
                          <tech.icon size={10} />
                          <span>{tech.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Architectural Patterns */}
        <div className="patterns-section">
          <h3 className="text-xl font-semibold text-[var(--soft-white)] text-center mb-8">
            Architectural Patterns
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'Event-Driven Architecture',
                description: 'Services communicate asynchronously via Pub/Sub topics for loose coupling and independent scaling',
                icon: Zap,
              },
              {
                title: 'CQRS Pattern',
                description: 'Separate read and write paths: Ingestion → Pub/Sub → BigQuery for writes, Analytics Engine → Views for reads',
                icon: Database,
              },
              {
                title: 'Saga Pattern',
                description: 'Multi-step prediction validation: Generate → Wait → Validate → Update Metrics → Retrain if needed',
                icon: TrendingUp,
              },
            ].map((pattern) => (
              <div key={pattern.title} className="pattern-card glass-card p-6">
                <div className="w-10 h-10 rounded-lg bg-[var(--signal-cyan)]/10 flex items-center justify-center mb-4">
                  <pattern.icon size={20} className="text-[var(--signal-cyan)]" />
                </div>
                <h4 className="text-base font-semibold text-[var(--soft-white)] mb-2">
                  {pattern.title}
                </h4>
                <p className="text-sm text-[var(--cool-gray)]">
                  {pattern.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
