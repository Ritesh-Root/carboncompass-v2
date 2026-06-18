/**
 * ChartTooltip — shared presentational tooltip card for Recharts charts.
 *
 * Both the category bar chart and the history line chart render the same
 * white rounded card; this component holds that markup in one place so the
 * two charts only supply their (different) title + value.
 */

import { formatKg } from '../../utils/formatters';

interface ChartTooltipProps {
  /** Top line — a category label, date, or other heading. */
  title: string;
  /** kg CO2e value shown formatted with a "CO₂e" suffix. */
  value: number;
}

export const ChartTooltip = ({ title, value }: ChartTooltipProps) => (
  <div className="bg-white border border-gray-200 rounded-xl px-3 py-2 shadow-lg text-sm">
    <p className="font-semibold text-gray-900">{title}</p>
    <p className="font-bold text-primary-700">{formatKg(value)} CO₂e</p>
  </div>
);
