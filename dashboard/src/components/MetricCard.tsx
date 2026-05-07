import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string;
  subValue: string;
  isPositive?: boolean;
  trend?: string;
  icon: React.ReactNode;
}

const MetricCard = ({ title, value, subValue, isPositive, trend, icon }: MetricCardProps) => {
  return (
    <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div className="p-2 bg-gray-50 rounded-xl text-gray-400">
          {icon}
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
            isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
          }`}>
            {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {trend}
          </div>
        )}
      </div>
      <div>
        <p className="text-sm text-gray-500 font-medium mb-1">{title}</p>
        <div className="flex flex-col">
          <h3 className="text-2xl font-bold text-gray-900">{value}</h3>
          <p className={`text-xs mt-1 ${isPositive ? 'text-emerald-600' : 'text-gray-400'}`}>
            {subValue}
          </p>
        </div>
      </div>
    </div>
  );
};

export default MetricCard;
