'use client';

import React, { useEffect, useState } from 'react';
import { Search, Filter, MoreHorizontal, Users } from 'lucide-react';
import { API_BASE_URL, getAuthHeaders } from '@/lib/api';

interface PacienteData {
  id: number;
  nome: string;
  cpf: string;
  email: string | null;
  telefone: string | null;
  ultima_consulta: string | null;
  total_consultas: number;
}

const PacientesPage = () => {
  const [pacientes, setPacientes] = useState<PacienteData[]>([]);
  const [filtro, setFiltro] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPacientes() {
      try {
        const resp = await fetch(`${API_BASE_URL}/dashboard/pacientes`, {
          headers: getAuthHeaders()
        });
        if (resp.ok) {
          const data = await resp.json();
          setPacientes(data.pacientes);
        }
      } catch (err) {
        console.error('Erro ao buscar pacientes:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchPacientes();
  }, []);

  const pacientesFiltrados = pacientes.filter(p =>
    p.nome.toLowerCase().includes(filtro.toLowerCase()) ||
    p.cpf.includes(filtro)
  );

  function formatCPF(cpf: string) {
    if (cpf.length === 11) {
      return `${cpf.slice(0,3)}.${cpf.slice(3,6)}.${cpf.slice(6,9)}-${cpf.slice(9)}`;
    }
    return cpf;
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Meus Pacientes</h1>
          <p className="text-gray-500 mt-1">{pacientes.length} pacientes sincronizados</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        {/* Toolbar */}
        <div className="p-6 flex justify-between items-center gap-4 border-b border-gray-50">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input 
              type="text" 
              placeholder="Buscar por nome ou CPF..." 
              value={filtro}
              onChange={(e) => setFiltro(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-100 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-gray-400 animate-pulse">Carregando pacientes...</div>
        ) : pacientesFiltrados.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="mx-auto mb-4 text-gray-300" size={48} />
            <p className="text-gray-400">Nenhum paciente encontrado.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                  <th className="px-6 py-4 font-bold">Paciente</th>
                  <th className="px-6 py-4 font-bold">CPF</th>
                  <th className="px-6 py-4 font-bold">Última Sincronização</th>
                  <th className="px-6 py-4 font-bold">Consultas</th>
                  <th className="px-6 py-4 font-bold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {pacientesFiltrados.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-6 py-4 font-medium text-gray-900">{p.nome}</td>
                    <td className="px-6 py-4 text-gray-500 text-sm font-mono">{formatCPF(p.cpf)}</td>
                    <td className="px-6 py-4 text-gray-500 text-sm">
                      {p.ultima_consulta ? new Date(p.ultima_consulta).toLocaleDateString('pt-BR') : '-'}
                    </td>
                    <td className="px-6 py-4 text-gray-500 text-sm">{p.total_consultas}x</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-emerald-50 text-emerald-600 text-xs font-bold rounded-full">
                        Sincronizado
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default PacientesPage;
