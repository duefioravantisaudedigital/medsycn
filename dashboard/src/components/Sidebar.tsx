'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { 
  LayoutDashboard, 
  Users, 
  FileBarChart, 
  History, 
  Settings, 
  LifeBuoy,
  Zap,
  LogOut
} from 'lucide-react';
import Cookies from 'js-cookie';

const Sidebar = () => {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    Cookies.remove('medsync_token');
    Cookies.remove('medsync_user');
    router.push('/login');
  };

  const menuItems = [
    { icon: <LayoutDashboard size={20} />, label: 'Início', href: '/' },
    { icon: <Users size={20} />, label: 'Pacientes', href: '/pacientes' },
    { icon: <FileBarChart size={20} />, label: 'Relatórios', href: '/relatorios' },
    { icon: <History size={20} />, label: 'Histórico', href: '/historico' },
  ];

  const secondaryItems = [
    { icon: <Settings size={20} />, label: 'Ajustes', href: '/ajustes' },
    { icon: <LifeBuoy size={20} />, label: 'Suporte', href: '/suporte' },
  ];

  return (
    <div className="w-64 bg-[#064e3b] h-screen flex flex-col text-white p-6 fixed left-0 top-0">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-3 mb-10 hover:opacity-80 transition-opacity">
        <div className="bg-white/20 p-2 rounded-lg">
          <div className="w-6 h-6 bg-white rounded-full flex items-center justify-center">
            <div className="w-3 h-3 bg-[#064e3b] rounded-sm rotate-45" />
          </div>
        </div>
        <h1 className="text-xl font-bold tracking-tight">MedSync</h1>
      </Link>

      {/* Main Menu */}
      <nav className="flex-1 space-y-2">
        {menuItems.map((item, index) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={index}
              href={item.href}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                isActive 
                  ? 'bg-white/10 text-white font-medium shadow-inner' 
                  : 'text-emerald-100/60 hover:bg-white/5 hover:text-white'
              }`}
            >
              {item.icon}
              <span className="flex-1 text-left">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom Section */}
      <div className="pt-6 border-t border-white/10 space-y-2">
        {secondaryItems.map((item, index) => (
          <Link
            key={index}
            href={item.href}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-emerald-100/60 hover:bg-white/5 hover:text-white transition-all"
          >
            {item.icon}
            <span className="text-left">{item.label}</span>
          </Link>
        ))}

        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-red-300/60 hover:bg-red-500/10 hover:text-red-400 transition-all mt-2"
        >
          <LogOut size={20} />
          <span className="text-left font-medium">Sair da Conta</span>
        </button>

        {/* Subscription Card */}
        <div className="mt-8 bg-white/5 border border-white/10 rounded-2xl p-4">
          <div className="flex justify-between items-start mb-2">
            <div>
              <p className="text-[10px] text-emerald-100/50 uppercase tracking-wider font-bold">Plano Pro - ativo</p>
              <p className="text-sm font-semibold">Expira 31/05</p>
            </div>
          </div>
          <div className="w-full bg-white/10 h-1.5 rounded-full mb-4">
            <div className="bg-emerald-400 h-full w-2/3 rounded-full" />
          </div>
          <button className="w-full bg-white text-[#064e3b] py-2 rounded-lg text-xs font-bold hover:bg-emerald-50 transition-colors">
            Renovar
          </button>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
