'use client';

import React, { useEffect, useState } from 'react';
import MetricCard from '@/components/MetricCard';
import SyncChart from '@/components/SyncChart';
import { API_BASE_URL, getAuthHeaders } from '@/lib/api';
import { 
  Users, 
  UserPlus, 
  Clock, 
  Calendar,
  CheckCircle2,
  Zap
} from 'lucide-react';

interface DashboardStats {
  processados_mes: number;
  total_pacientes: number;
  taxa_sucesso: number;
  total_erros: number;
  nome: string;
  crm: string;
  uf_crm: string;
  subscription_expires_at: string | null;
}

export default function Home() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const resp = await fetch(`${API_BASE_URL}/dashboard/stats`, {
          headers: getAuthHeaders()
        });
        if (resp.ok) {
          const data = await resp.json();
          setStats(data);
        }
      } catch (err) {
        console.error('Erro ao buscar stats:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto flex items-center justify-center h-96">
        <div className="text-gray-400 text-lg animate-pulse">Carregando dados...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Visão geral</h1>
          <p className="text-gray-500 mt-1">
            {stats?.nome ? `Dr(a). ${stats.nome}` : 'Dashboard'} · {stats?.crm ? `CRM ${stats.crm}/${stats.uf_crm}` : ''}
          </p>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          title="Processados (mês)" 
          value={String(stats?.processados_mes ?? 0)} 
          subValue="sincronizações neste mês" 
          isPositive={true}
          icon={<Users size={20} />}
        />
        <MetricCard 
          title="Pacientes Únicos" 
          value={String(stats?.total_pacientes ?? 0)} 
          subValue="pacientes no total" 
          isPositive={true}
          icon={<UserPlus size={20} />}
        />
        <MetricCard 
          title="Taxa de Sucesso" 
          value={`${stats?.taxa_sucesso ?? 0}%`} 
          subValue={`${stats?.total_erros ?? 0} erros este mês`} 
          isPositive={(stats?.taxa_sucesso ?? 0) > 90}
          icon={<CheckCircle2 size={20} />}
        />
        <MetricCard 
          title="Assinatura" 
          value={stats?.subscription_expires_at 
            ? new Date(stats.subscription_expires_at).toLocaleDateString('pt-BR') 
            : 'Sem data'} 
          subValue="data de expiração" 
          isPositive={true}
          icon={<Calendar size={20} />}
        />
      </div>

      {/* Chart + Highlights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <SyncChart />
        </div>

        {/* Highlights Section */}
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm h-full flex flex-col justify-between">
            <h3 className="text-lg font-bold text-gray-900 mb-6">Resumo</h3>
            
            <div className="space-y-6 flex-1">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl">
                  <Users size={20} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{stats?.processados_mes ?? 0} sincronizações</p>
                  <p className="text-xs text-gray-500">processadas neste mês</p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-50 text-blue-600 rounded-2xl">
                  <CheckCircle2 size={20} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{stats?.taxa_sucesso ?? 0}% de sucesso</p>
                  <p className="text-xs text-gray-500">{stats?.total_erros ?? 0} erros de sincronização</p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="p-3 bg-orange-50 text-orange-600 rounded-2xl">
                  <Zap size={20} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{stats?.total_pacientes ?? 0} pacientes</p>
                  <p className="text-xs text-gray-500">cadastrados na plataforma</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
