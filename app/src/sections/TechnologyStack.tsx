import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { 
  Cloud, 
  Server, 
  Brain, 
  Code2,
  ArrowRight,
  Database,
  Cpu,
  Layers,
  BarChart3
} from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const techStack = [
  {
    id: 'cloud',
    title: 'Cloud Platform',
    subtitle: 'Google Cloud Platform',
    description: 'Cloud Run, Pub/Sub, BigQuery, Vertex AI, Cloud Storage',
    icon: Cloud,
    color: 'var(--signal-cyan)',
    technologies: ['Cloud Run', 'Pub/Sub', 'BigQuery', 'Vertex AI'],
  },
  {
    id: 'backend',
    title: 'Backend',
    subtitle: 'Python & FastAPI',
    description: 'High-performance async APIs with microservices architecture',
    icon: Server,
    color: 'var(--lag-green)',
    technologies: ['Python 3.11', 'FastAPI', 'AsyncIO', 'Pydantic'],
  },
  {
    id: 'ml',
    title: 'ML/AI',
    subtitle: 'TensorFlow & Vertex AI',
    description: 'LSTM, ARIMA, XGBoost models with ensemble voting',
    icon: Brain,
    color: 'var(--amber-pulse)',
    technologies: ['TensorFlow', 'LSTM', 'ARIMA', 'XGBoost'],
  },
  {
    id: 'frontend',
    title: 'Frontend',
    subtitle: 'React & Node.js',
    description: 'Modern responsive UI with real-time data visualization',
    icon: Code2,
    color: 'var(--gold-accent)',
    technologies: ['React 18', 'TypeScript', 'Tailwind', 'Chart.js'],
  },
];

const architectureFlow = [
  { label: 'Clients', icon: Code2, port: null },
  { label: 'API Gateway', icon: Server, port: '8000' },
  { label: 'Microservices', icon: Cpu, port: '8081-8087' },
  { label: 'BigQuery', icon: Database, port: null },
];

const TechnologyStack = () => {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Section header
      gsap.fromTo(
        '.tech-header',
        { y: 40, opacity: 0 },
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

      // Tech cards with rotation
      gsap.fromTo(
        '.tech-card',
        { rotateZ: (i) => (i % 2 === 0 ? -15 : 15), scale: 0.9, opacity: 0 },
        {
          rotateZ: (i) => (i % 2 === 0 ? -2 : 2),
          scale: 1,
          opacity: 1,
          duration: 0.6,
          stagger: 0.1,
          ease: 'back.out(1.4)',
          scrollTrigger: {
            trigger: '.tech-cards',
            start: 'top 75%',
          },
        }
      );

      // Architecture diagram
      gsap.fromTo(
        '.arch-diagram',
        { scale: 0.95, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.7,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: '.arch-diagram',
            start: 'top 80%',
          },
        }
      );

      // Flow arrows
      gsap.fromTo(
        '.flow-arrow',
        { width: 0, opacity: 0 },
        {
          width: '100%',
          opacity: 1,
          duration: 0.5,
          stagger: 0.1,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: '.arch-diagram',
            start: 'top 70%',
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      id="technology"
      ref={sectionRef}
      className="py-24 relative overflow-hidden"
    >
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[var(--void-black)] via-[var(--deep-slate)]/20 to-[var(--void-black)]" />

      <div className="section-container max-w-7xl mx-auto relative z-10">
        {/* Section Header */}
        <div className="tech-header text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full bg-[var(--signal-cyan)]/10 text-[var(--signal-cyan)] text-xs font-medium uppercase tracking-wider mb-4">
            Technology
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-[var(--soft-white)] mb-4">
            Our Technology Stack
          </h2>
          <p className="text-lg text-[var(--cool-gray)] max-w-2xl mx-auto">
            Modern tools for modern finance
          </p>
        </div>

        {/* Tech Cards */}
        <div className="tech-cards grid grid-cols-1 md:grid-cols-2 gap-6 mb-16">
          {techStack.map((tech, index) => (
            <div
              key={tech.id}
              className="tech-card glass-card p-6 card-lift"
              style={{
                transform: `rotateZ(${index % 2 === 0 ? -2 : 2}deg)`,
              }}
            >
              <div className="flex items-start gap-4">
                <div
                  className="w-14 h-14 rounded-xl flex items-center justify-center shrink-0"
                  style={{ backgroundColor: `${tech.color}15` }}
                >
                  <tech.icon size={28} style={{ color: tech.color }} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-lg font-semibold text-[var(--soft-white)]">
                      {tech.title}
                    </h3>
                  </div>
                  <p
                    className="text-sm font-medium mb-2"
                    style={{ color: tech.color }}
                  >
                    {tech.subtitle}
                  </p>
                  <p className="text-sm text-[var(--cool-gray)] mb-4">
                    {tech.description}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {tech.technologies.map((t) => (
                      <span
                        key={t}
                        className="px-2 py-1 rounded-md text-xs"
                        style={{
                          backgroundColor: `${tech.color}15`,
                          color: tech.color,
                        }}
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Architecture Diagram */}
        <div className="arch-diagram glass-card p-8">
          <h3 className="text-lg font-semibold text-[var(--soft-white)] text-center mb-8">
            System Architecture
          </h3>

          {/* Flow Diagram */}
          <div className="relative">
            {/* Desktop Layout */}
            <div className="hidden md:flex items-center justify-between gap-4">
              {architectureFlow.map((node, index) => (
                <div key={node.label} className="flex items-center gap-4">
                  <div className="glass-card p-4 text-center min-w-[140px] card-lift">
                    <div className="w-10 h-10 rounded-lg bg-[var(--signal-cyan)]/10 flex items-center justify-center mx-auto mb-2">
                      <node.icon size={20} className="text-[var(--signal-cyan)]" />
                    </div>
                    <p className="text-sm font-medium text-[var(--soft-white)]">
                      {node.label}
                    </p>
                    {node.port && (
                      <span className="port-badge mt-2">Port {node.port}</span>
                    )}
                  </div>
                  {index < architectureFlow.length - 1 && (
                    <div className="flow-arrow flex items-center">
                      <ArrowRight size={20} className="text-[var(--signal-cyan)]" />
                      <div className="w-12 h-0.5 bg-gradient-to-r from-[var(--signal-cyan)] to-[var(--lag-green)]" />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Mobile Layout */}
            <div className="md:hidden space-y-4">
              {architectureFlow.map((node, index) => (
                <div key={node.label} className="flex items-center gap-4">
                  <div className="glass-card p-4 flex-1 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-[var(--signal-cyan)]/10 flex items-center justify-center">
                      <node.icon size={20} className="text-[var(--signal-cyan)]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[var(--soft-white)]">
                        {node.label}
                      </p>
                      {node.port && (
                        <span className="port-badge text-xs">Port {node.port}</span>
                      )}
                    </div>
                  </div>
                  {index < architectureFlow.length - 1 && (
                    <div className="flex flex-col items-center">
                      <ArrowRight size={16} className="text-[var(--signal-cyan)] rotate-90" />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Microservices Detail */}
            <div className="mt-8 pt-8 border-t border-[var(--border)]">
              <h4 className="text-sm font-medium text-[var(--cool-gray)] mb-4 text-center">
                Microservices Architecture (Ports 8081-8087)
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { port: '8081', name: 'Ingestion', icon: Database },
                  { port: '8082', name: 'Sentiment', icon: Brain },
                  { port: '8083', name: 'Context', icon: Layers },
                  { port: '8084', name: 'Prediction', icon: Cpu },
                  { port: '8085', name: 'Alerts', icon: Server },
                  { port: '8086', name: 'Analytics', icon: BarChart3 },
                  { port: '8087', name: 'Tracker', icon: Cloud },
                ].map((service) => (
                  <div
                    key={service.port}
                    className="flex items-center gap-2 p-2 rounded-lg bg-[var(--graphite-blue)]"
                  >
                    <service.icon size={14} className="text-[var(--signal-cyan)]" />
                    <span className="text-xs text-[var(--soft-white)]">{service.name}</span>
                    <span className="port-badge text-xs ml-auto">{service.port}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Tech Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
          {[
            { label: 'Services', value: '7', icon: Server },
            { label: 'API Endpoints', value: '50+', icon: Code2 },
            { label: 'ML Models', value: '4', icon: Brain },
            { label: 'Data Sources', value: '12', icon: Database },
          ].map((stat) => (
            <div key={stat.label} className="glass-card p-4 text-center">
              <stat.icon
                size={20}
                className="mx-auto mb-2 text-[var(--signal-cyan)]"
              />
              <p className="text-2xl font-bold text-[var(--soft-white)]">
                {stat.value}
              </p>
              <p className="text-xs text-[var(--cool-gray)]">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default TechnologyStack;
