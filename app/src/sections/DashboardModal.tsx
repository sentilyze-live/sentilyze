import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { 
  X, 
  Activity, 
  Database, 
  Brain, 
  Cloud,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Wifi,
  Clock,
  Zap,
  BarChart3,
  MessageSquare
} from 'lucide-react';

interface DashboardModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Simulated live data
const generateLogEntry = () => {
  const events = [
    { type: 'info', message: 'Price update received from Binance' },
    { type: 'success', message: 'Sentiment analysis completed' },
    { type: 'info', message: 'Market context processed' },
    { type: 'success', message: 'Prediction generated with 87% confidence' },
    { type: 'warning', message: 'High volatility detected in XAU/USD' },
    { type: 'info', message: 'Pub/Sub message published' },
    { type: 'success', message: 'BigQuery insert successful' },
  ];
  const event = events[Math.floor(Math.random() * events.length)];
  return {
    timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
    ...event,
  };
};

const serviceStatus = [
  { name: 'Pub/Sub', status: 'active', icon: MessageSquare, latency: '45ms' },
  { name: 'BigQuery', status: 'active', icon: Database, latency: '120ms' },
  { name: 'Vertex AI', status: 'active', icon: Brain, latency: '280ms' },
  { name: 'Cloud Run', status: 'active', icon: Cloud, latency: '35ms' },
];

const DashboardModal = ({ isOpen, onClose }: DashboardModalProps) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [logs, setLogs] = useState<Array<{ timestamp: string; type: string; message: string }>>([]);
  const [metrics, setMetrics] = useState({
    cpu: 34,
    memory: 62,
    network: 12,
    uptime: '99.9%',
    messagesPerSec: 1247,
    peakMessages: 2891,
  });

  // Generate initial logs
  useEffect(() => {
    const initialLogs = Array.from({ length: 10 }, generateLogEntry);
    setLogs(initialLogs);
  }, []);

  // Simulate live data updates
  useEffect(() => {
    if (!isOpen) return;

    const logInterval = setInterval(() => {
      setLogs((prev) => {
        const newLog = generateLogEntry();
        return [newLog, ...prev].slice(0, 20);
      });
    }, 2000);

    const metricsInterval = setInterval(() => {
      setMetrics((prev) => ({
        ...prev,
        cpu: Math.max(20, Math.min(80, prev.cpu + (Math.random() - 0.5) * 10)),
        memory: Math.max(40, Math.min(90, prev.memory + (Math.random() - 0.5) * 5)),
        network: Math.max(5, Math.min(50, prev.network + (Math.random() - 0.5) * 8)),
        messagesPerSec: Math.max(800, Math.min(2000, prev.messagesPerSec + Math.floor((Math.random() - 0.5) * 100))),
      }));
    }, 3000);

    return () => {
      clearInterval(logInterval);
      clearInterval(metricsInterval);
    };
  }, [isOpen]);

  // Animation
  useEffect(() => {
    if (isOpen) {
      gsap.fromTo(
        modalRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.3, ease: 'power2.out' }
      );
      gsap.fromTo(
        panelRef.current,
        { rotateX: -15, y: 50, opacity: 0 },
        { rotateX: 0, y: 0, opacity: 1, duration: 0.5, ease: 'back.out(1.4)', delay: 0.1 }
      );
    }
  }, [isOpen]);

  const handleClose = () => {
    gsap.to(panelRef.current, {
      rotateX: 10,
      y: -50,
      opacity: 0,
      duration: 0.4,
      ease: 'power2.in',
    });
    gsap.to(modalRef.current, {
      opacity: 0,
      duration: 0.3,
      delay: 0.2,
      onComplete: onClose,
    });
  };

  if (!isOpen) return null;

  return (
    <div
      ref={modalRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-backdrop bg-black/80"
      onClick={handleClose}
    >
      <div
        ref={panelRef}
        className="relative w-full max-w-6xl max-h-[90vh] overflow-hidden rounded-2xl bg-[var(--deep-slate)] border border-[var(--signal-cyan)]/20"
        style={{ perspective: '1000px' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[var(--border)]">
          <div>
            <h2 className="text-xl font-semibold text-[var(--soft-white)] flex items-center gap-2">
              <Activity size={24} className="text-[var(--signal-cyan)]" />
              System Dashboard
            </h2>
            <p className="text-sm text-[var(--cool-gray)] mt-1">
              Real-time monitoring and metrics
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-lg text-[var(--cool-gray)] hover:text-[var(--soft-white)] hover:bg-[var(--graphite-blue)] transition-all"
          >
            <X size={20} />
          </button>
        </div>

        {/* Dashboard Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-100px)]">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Service Status */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-medium text-[var(--cool-gray)] mb-4 flex items-center gap-2">
                <CheckCircle2 size={16} className="text-[var(--lag-green)]" />
                Service Status
              </h3>
              <div className="space-y-3">
                {serviceStatus.map((service) => (
                  <div
                    key={service.name}
                    className="flex items-center justify-between p-3 rounded-lg bg-[var(--graphite-blue)]"
                  >
                    <div className="flex items-center gap-3">
                      <service.icon size={18} className="text-[var(--signal-cyan)]" />
                      <span className="text-sm text-[var(--soft-white)]">{service.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-[var(--cool-gray)] font-mono">
                        {service.latency}
                      </span>
                      <div className="live-indicator" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* System Health */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-medium text-[var(--cool-gray)] mb-4 flex items-center gap-2">
                <Cpu size={16} className="text-[var(--signal-cyan)]" />
                System Health
              </h3>
              <div className="space-y-4">
                {[
                  { label: 'CPU', value: metrics.cpu, color: 'var(--signal-cyan)', icon: Cpu },
                  { label: 'Memory', value: metrics.memory, color: 'var(--lag-green)', icon: Database },
                  { label: 'Network', value: metrics.network, color: 'var(--amber-pulse)', icon: Wifi, suffix: ' MB/s' },
                ].map((metric) => (
                  <div key={metric.label}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <metric.icon size={14} className="text-[var(--cool-gray)]" />
                        <span className="text-sm text-[var(--cool-gray)]">{metric.label}</span>
                      </div>
                      <span className="text-sm font-mono text-[var(--soft-white)]">
                        {Math.round(metric.value)}{metric.suffix || '%'}
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-[var(--graphite-blue)] overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(100, metric.value)}%`,
                          backgroundColor: metric.color,
                        }}
                      />
                    </div>
                  </div>
                ))}
                <div className="pt-3 border-t border-[var(--border)]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Clock size={14} className="text-[var(--cool-gray)]" />
                      <span className="text-sm text-[var(--cool-gray)]">Uptime</span>
                    </div>
                    <span className="text-sm font-mono text-[var(--lag-green)]">
                      {metrics.uptime}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Message Throughput */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-medium text-[var(--cool-gray)] mb-4 flex items-center gap-2">
                <Zap size={16} className="text-[var(--amber-pulse)]" />
                Message Throughput
              </h3>
              <div className="text-center mb-4">
                <p className="text-3xl font-bold text-[var(--soft-white)] font-mono">
                  {metrics.messagesPerSec.toLocaleString()}
                </p>
                <p className="text-xs text-[var(--cool-gray)]">messages/sec</p>
              </div>
              <div className="h-24 relative">
                {/* Simple bar chart visualization */}
                <div className="absolute inset-0 flex items-end justify-between gap-1">
                  {Array.from({ length: 12 }, (_, i) => {
                    const height = 30 + Math.random() * 60;
                    const isCurrent = i === 11;
                    return (
                      <div
                        key={i}
                        className="flex-1 rounded-t transition-all duration-300"
                        style={{
                          height: `${height}%`,
                          backgroundColor: isCurrent ? 'var(--signal-cyan)' : 'var(--graphite-blue)',
                          opacity: isCurrent ? 1 : 0.5,
                        }}
                      />
                    );
                  })}
                </div>
              </div>
              <div className="flex items-center justify-between mt-3 text-xs">
                <span className="text-[var(--cool-gray)]">Peak: {metrics.peakMessages.toLocaleString()}/s</span>
                <span className="text-[var(--lag-green)]">+12% vs last hour</span>
              </div>
            </div>

            {/* Live Data Stream */}
            <div className="glass-card p-5 md:col-span-2 lg:col-span-2">
              <h3 className="text-sm font-medium text-[var(--cool-gray)] mb-4 flex items-center gap-2">
                <BarChart3 size={16} className="text-[var(--signal-cyan)]" />
                Live Data Stream
              </h3>
              <div className="h-48 overflow-hidden">
                <div className="space-y-1">
                  {logs.map((log, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-3 p-2 rounded text-sm font-mono animate-[fade-in-up_0.3s_ease-out]"
                      style={{
                        backgroundColor: index === 0 ? 'var(--graphite-blue)' : 'transparent',
                      }}
                    >
                      <span className="text-[var(--cool-gray)] text-xs">{log.timestamp}</span>
                      <span
                        className={`text-xs ${
                          log.type === 'success'
                            ? 'text-[var(--lag-green)]'
                            : log.type === 'warning'
                            ? 'text-[var(--amber-pulse)]'
                            : 'text-[var(--signal-cyan)]'
                        }`}
                      >
                        {log.type === 'success' && <CheckCircle2 size={12} />}
                        {log.type === 'warning' && <AlertCircle size={12} />}
                        {log.type === 'info' && <Activity size={12} />}
                      </span>
                      <span className="text-[var(--soft-white)] truncate">{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="glass-card p-5">
              <h3 className="text-sm font-medium text-[var(--cool-gray)] mb-4">
                Quick Actions
              </h3>
              <div className="space-y-2">
                {[
                  { label: 'Restart Service', icon: Zap, color: 'var(--amber-pulse)' },
                  { label: 'Clear Cache', icon: Database, color: 'var(--signal-cyan)' },
                  { label: 'Export Logs', icon: Cloud, color: 'var(--lag-green)' },
                ].map((action) => (
                  <button
                    key={action.label}
                    className="w-full flex items-center gap-3 p-3 rounded-lg bg-[var(--graphite-blue)] hover:bg-[var(--deep-slate)] transition-colors text-left"
                  >
                    <action.icon size={16} style={{ color: action.color }} />
                    <span className="text-sm text-[var(--soft-white)]">{action.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardModal;
