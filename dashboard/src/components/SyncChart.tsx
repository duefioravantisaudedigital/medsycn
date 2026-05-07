'use client';

import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from 'recharts';

const data = [
  { name: 'Jan', novos: 400, existentes: 240 },
  { name: 'Fev', novos: 300, existentes: 139 },
  { name: 'Mar', novos: 200, existentes: 980 },
  { name: 'Abr', novos: 278, existentes: 390 },
  { name: 'Mai', novos: 189, existentes: 480 },
];

const SyncChart = () => {
  return (
    <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm h-[400px]">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Pacientes por mês (2025)</h3>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-[#059669] rounded-full" />
            <span className="text-xs text-gray-500 font-medium">Novos</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-[#d1fae5] rounded-full" />
            <span className="text-xs text-gray-500 font-medium">Existentes</span>
          </div>
        </div>
      </div>
      
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barGap={8}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis 
              dataKey="name" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#9ca3af', fontSize: 12 }}
              dy={10}
            />
            <YAxis hide />
            <Tooltip 
              cursor={{ fill: '#f9fafb' }}
              contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
            />
            <Bar dataKey="novos" fill="#059669" radius={[4, 4, 0, 0]} barSize={32} />
            <Bar dataKey="existentes" fill="#d1fae5" radius={[4, 4, 0, 0]} barSize={32} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default SyncChart;
