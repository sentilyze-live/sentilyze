import React from 'react';
import { LayoutDashboard, TrendingUp, Bitcoin, Bell, Settings, LogOut, Coins } from 'lucide-react';

interface MenuItem {
  icon: React.ElementType;
  label: string;
  href: string;
  active?: boolean;
}

const menuItems: MenuItem[] = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/' },
  { icon: Coins, label: 'Altın', href: '/gold', active: true },
  { icon: Bitcoin, label: 'Bitcoin', href: '/bitcoin' },
  { icon: Bell, label: 'Alarmlar', href: '/alerts' },
  { icon: Settings, label: 'Ayarlar', href: '/settings' },
];

const Sidebar: React.FC = () => {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-[#121822] border-r border-[#1F2A38] z-50 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-[#1F2A38]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-white">SENTILYZE</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.label}>
                <a
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                    item.active
                      ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                      : 'text-[#9AA4B2] hover:bg-[#1A2230] hover:text-white'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-[#1F2A38]">
        <button className="flex items-center gap-3 px-4 py-3 w-full rounded-lg text-[#9AA4B2] hover:bg-[#1A2230] hover:text-white transition-all duration-200">
          <LogOut className="w-5 h-5" />
          <span className="font-medium">Çıkış</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
