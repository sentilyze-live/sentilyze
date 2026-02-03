import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { 
  Cloud, 
  MessageSquare, 
  Database, 
  Brain, 
  CheckCircle2,
  Server,
  Zap,
  Clock
} from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const gcpServices = [
  {
    id: 'cloudrun',
    name: 'Cloud Run',
    percentage: 40,
    description: '7 microservices with scale-to-zero and auto-scaling 0-100 instances',
    icon: Cloud,
    color: 'var(--signal-cyan)',
    metrics: [
      { label: 'Uptime', value: '99.9%' },
      { label: 'Cold Start', value: '50ms' },
    ],
    features: ['Serverless containers', 'Auto-scaling', 'Scale-to-zero', 'HTTP/2 & gRPC'],
  },
  {
    id: 'pubsub',
    name: 'Pub/Sub',
    percentage: 25,
    description: 'Event-driven messaging with <100ms latency, handling 50K+ msg/sec',
    icon: MessageSquare,
    color: 'var(--lag-green)',
    metrics: [
      { label: 'Throughput', value: '50K+/s' },
      { label: 'Latency', value: '<100ms' },
    ],
    features: ['Global messaging', 'Push subscriptions', 'Dead-letter queues', 'Ordering keys'],
  },
  {
    id: 'bigquery',
    name: 'BigQuery',
    percentage: 20,
    description: 'Petabyte-scale analytics and ML training data warehouse',
    icon: Database,
    color: 'var(--amber-pulse)',
    metrics: [
      { label: 'Scale', value: 'PB-scale' },
      { label: 'Queries', value: 'Real-time' },
    ],
    features: ['Serverless', 'ML integration', 'Streaming inserts', 'Partitioning'],
  },
  {
    id: 'vertexai',
    name: 'Vertex AI',
    percentage: 15,
    description: 'Gemini Pro for sentiment analysis, model hosting, and MLOps pipelines',
    icon: Brain,
    color: 'var(--gold-accent)',
    metrics: [
      { label: 'Model', value: 'Gemini Pro' },
      { label: 'Pipeline', value: 'AutoML' },
    ],
    features: ['Model training', 'Endpoint hosting', 'Feature store', 'Pipelines'],
  },
];

const architectureMap = {
  nodes: [
    { id: 'clients', label: 'Clients', x: 10, y: 50 },
    { id: 'gateway', label: 'API Gateway\nPort 8000', x: 30, y: 50 },
    { id: 'services', label: 'Microservices\n8081-8087', x: 55, y: 50 },
    { id: 'pubsub', label: 'Pub/Sub', x: 75, y: 30 },
    { id: 'bigquery', label: 'BigQuery', x: 75, y: 70 },
  ],
  connections: [
    { from: 'clients', to: 'gateway' },
    { from: 'gateway', to: 'services' },
    { from: 'services', to: 'pubsub' },
    { from: 'services', to: 'bigquery' },
    { from: 'pubsub', to: 'bigquery', dashed: true },
  ],
};

const GoogleCloud = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [animatedPercentages, setAnimatedPercentages] = useState<number[]>([0, 0, 0, 0]);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Section header
      gsap.fromTo(
        '.gcp-header',
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

      // Service cards with 3D flip
      gsap.fromTo(
        '.gcp-card',
        { rotateY: -30, opacity: 0, transformPerspective: 1000 },
        {
          rotateY: 0,
          opacity: 1,
          duration: 0.7,
          stagger: 0.15,
          ease: 'back.out(1.4)',
          scrollTrigger: {
            trigger: '.gcp-cards',
            start: 'top 75%',
          },
        }
      );

      // Animate progress bars
      ScrollTrigger.create({
        trigger: '.gcp-cards',
        start: 'top 70%',
        onEnter: () => {
          gcpServices.forEach((service, index) => {
            gsap.to({}, {
              duration: 1.2,
              ease: 'expo.out',
              onUpdate: function() {
                setAnimatedPercentages(prev => {
                  const newPercentages = [...prev];
                  newPercentages[index] = Math.round(service.percentage * this.progress());
                  return newPercentages;
                });
              },
            });
          });
        },
        once: true,
      });

      // Architecture map
      gsap.fromTo(
        '.arch-map',
        { scale: 0.9, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.7,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: '.arch-map',
            start: 'top 80%',
          },
        }
      );

      // SLA metrics
      gsap.fromTo(
        '.sla-metric',
        { y: 20, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.5,
          stagger: 0.1,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: '.sla-section',
            start: 'top 85%',
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      id="infrastructure"
      ref={sectionRef}
      className="py-24 relative overflow-hidden"
    >
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[var(--void-black)] via-[var(--deep-slate)]/20 to-[var(--void-black)]" />
      
      {/* Google Cloud color accent */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#4285F4]/50 to-transparent" />

      <div className="section-container max-w-7xl mx-auto relative z-10">
        {/* Section Header */}
        <div className="gcp-header text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#4285F4]/10 border border-[#4285F4]/20 mb-4">
            <Cloud size={14} className="text-[#4285F4]" />
            <span className="text-xs font-medium text-[#4285F4] uppercase tracking-wider">
              Infrastructure
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-[var(--soft-white)] mb-4">
            Infrastructure Backbone:{' '}
            <span className="text-[#4285F4]">Google Cloud</span>
          </h2>
          <p className="text-lg text-[var(--cool-gray)] max-w-2xl mx-auto">
            100% running on Google Cloud Platform with enterprise-grade reliability
          </p>
        </div>

        {/* Service Cards */}
        <div className="gcp-cards grid grid-cols-1 md:grid-cols-2 gap-6 mb-16">
          {gcpServices.map((service, index) => (
            <div
              key={service.id}
              className="gcp-card glass-card p-6 card-lift"
              style={{ transformStyle: 'preserve-3d' }}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: `${service.color}20` }}
                  >
                    <service.icon size={24} style={{ color: service.color }} />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-[var(--soft-white)]">
                      {service.name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className="text-2xl font-bold"
                        style={{ color: service.color }}
                      >
                        {animatedPercentages[index]}%
                      </span>
                      <span className="text-xs text-[var(--cool-gray)]">usage</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="h-2 rounded-full bg-[var(--graphite-blue)] overflow-hidden mb-4">
                <div
                  className="h-full rounded-full progress-shimmer transition-all duration-1000"
                  style={{
                    width: `${animatedPercentages[index]}%`,
                    background: `linear-gradient(90deg, ${service.color}, ${service.color}80)`,
                  }}
                />
              </div>

              {/* Description */}
              <p className="text-sm text-[var(--cool-gray)] mb-4">
                {service.description}
              </p>

              {/* Metrics */}
              <div className="flex gap-4 mb-4">
                {service.metrics.map((metric) => (
                  <div
                    key={metric.label}
                    className="flex items-center gap-1.5 text-xs"
                  >
                    <CheckCircle2 size={12} style={{ color: service.color }} />
                    <span className="text-[var(--cool-gray)]">{metric.label}:</span>
                    <span className="text-[var(--soft-white)] font-mono">
                      {metric.value}
                    </span>
                  </div>
                ))}
              </div>

              {/* Features */}
              <div className="flex flex-wrap gap-2">
                {service.features.map((feature) => (
                  <span
                    key={feature}
                    className="px-2 py-1 rounded-md text-xs"
                    style={{
                      backgroundColor: `${service.color}15`,
                      color: service.color,
                    }}
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* SLA & Metrics */}
        <div className="sla-section grid grid-cols-2 md:grid-cols-4 gap-4 mb-16">
          {[
            { icon: CheckCircle2, label: 'Uptime SLA', value: '99.9%', color: 'var(--lag-green)' },
            { icon: Server, label: 'Services', value: '7', color: 'var(--signal-cyan)' },
            { icon: Zap, label: 'Auto-scaling', value: '0-100', color: 'var(--amber-pulse)' },
            { icon: Clock, label: 'Latency', value: '<100ms', color: 'var(--gold-accent)' },
          ].map((metric) => (
            <div
              key={metric.label}
              className="sla-metric glass-card p-4 text-center"
            >
              <metric.icon
                size={24}
                className="mx-auto mb-2"
                style={{ color: metric.color }}
              />
              <p className="text-2xl font-bold text-[var(--soft-white)] mb-1">
                {metric.value}
              </p>
              <p className="text-xs text-[var(--cool-gray)]">{metric.label}</p>
            </div>
          ))}
        </div>

        {/* Architecture Map */}
        <div className="arch-map glass-card p-8">
          <h3 className="text-lg font-semibold text-[var(--soft-white)] text-center mb-8">
            Service Architecture Map
          </h3>
          
          <div className="relative h-64 md:h-80">
            <svg
              className="absolute inset-0 w-full h-full"
              viewBox="0 0 100 100"
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Connection lines */}
              {architectureMap.connections.map((conn, i) => {
                const fromNode = architectureMap.nodes.find(n => n.id === conn.from);
                const toNode = architectureMap.nodes.find(n => n.id === conn.to);
                if (!fromNode || !toNode) return null;
                
                return (
                  <line
                    key={i}
                    x1={fromNode.x}
                    y1={fromNode.y}
                    x2={toNode.x}
                    y2={toNode.y}
                    stroke="url(#lineGradient)"
                    strokeWidth="0.5"
                    strokeDasharray={conn.dashed ? '2 1' : '0'}
                    opacity="0.6"
                  />
                );
              })}
              
              {/* Animated data flow dots */}
              {architectureMap.connections.slice(0, 3).map((conn, i) => {
                const fromNode = architectureMap.nodes.find(n => n.id === conn.from);
                const toNode = architectureMap.nodes.find(n => n.id === conn.to);
                if (!fromNode || !toNode) return null;
                
                return (
                  <circle
                    key={`flow-${i}`}
                    r="1"
                    fill="var(--signal-cyan)"
                    opacity="0.8"
                  >
                    <animateMotion
                      dur={`${2 + i * 0.5}s`}
                      repeatCount="indefinite"
                      path={`M${fromNode.x},${fromNode.y} L${toNode.x},${toNode.y}`}
                    />
                  </circle>
                );
              })}
              
              <defs>
                <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="var(--signal-cyan)" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="var(--lag-green)" stopOpacity="0.3" />
                </linearGradient>
              </defs>
            </svg>
            
            {/* Nodes */}
            {architectureMap.nodes.map((node) => (
              <div
                key={node.id}
                className="absolute transform -translate-x-1/2 -translate-y-1/2"
                style={{
                  left: `${node.x}%`,
                  top: `${node.y}%`,
                }}
              >
                <div className="glass-card px-3 py-2 text-center min-w-[80px]">
                  <p className="text-xs font-medium text-[var(--soft-white)] whitespace-pre-line">
                    {node.label}
                  </p>
                </div>
              </div>
            ))}
          </div>
          
          {/* Legend */}
          <div className="flex flex-wrap justify-center gap-4 mt-6 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 bg-[var(--signal-cyan)]" />
              <span className="text-[var(--cool-gray)]">Direct Connection</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 bg-[var(--signal-cyan)] border-dashed" style={{ borderTop: '1px dashed var(--signal-cyan)', background: 'none', height: '1px' }} />
              <span className="text-[var(--cool-gray)]">Async Flow</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[var(--signal-cyan)] animate-pulse" />
              <span className="text-[var(--cool-gray)]">Live Data</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default GoogleCloud;
