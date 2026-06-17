/**
 * ResultsDisplay — Carbon calculation results with comparisons and chart.
 *
 * Accessibility features:
 *   - <section aria-labelledby="results-heading">
 *   - aria-live="polite" so screen readers announce new results
 *   - Progress bars have aria-label with percentage and comparison target
 *   - "Get Personalized Insights" button triggers AI insights flow
 */

import { useCarbonStore } from '../../store/carbonStore';
import type { CarbonResult } from '../../types';
import { formatKg, getFootprintLabel } from '../../utils/formatters';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { CategoryChart } from './CategoryChart';

interface ResultsDisplayProps {
  result: CarbonResult;
}

const ComparisonBar = ({
  id,
  label,
  pct,
  benchmark,
  benchmarkKg,
}: {
  id: string;
  label: string;
  pct: number;
  benchmark: string;
  benchmarkKg: number;
}) => {
  const clampedPct = Math.min(pct, 200);
  const barWidth = Math.min(clampedPct / 2, 100); // 200% maps to full bar width
  const color = pct <= 100 ? 'bg-primary-500' : pct <= 150 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="font-bold text-gray-900">
          {pct.toFixed(0)}%{' '}
          <span className="font-normal text-gray-500">of {formatKg(benchmarkKg)}</span>
        </span>
      </div>
      <div
        className="relative w-full h-3 bg-gray-100 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={200}
        aria-label={`${label}: your footprint is ${pct.toFixed(0)}% of the ${benchmark} (${formatKg(benchmarkKg)}/year)`}
        id={id}
      >
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${barWidth}%` }}
        />
        {/* 100% marker */}
        <div
          className="absolute top-0 h-full w-0.5 bg-gray-400 opacity-60"
          style={{ left: '50%' }}
          aria-hidden="true"
        />
      </div>
      <p className="text-xs text-gray-400">
        {pct <= 100
          ? `You are below the ${benchmark}`
          : `You are ${(pct - 100).toFixed(0)}% above the ${benchmark}`}
      </p>
    </div>
  );
};

export const ResultsDisplay = ({ result }: ResultsDisplayProps) => {
  const fetchInsights = useCarbonStore(s => s.fetchInsights);
  const isLoadingInsights = useCarbonStore(s => s.isLoadingInsights);
  const insights = useCarbonStore(s => s.insights);

  const { label, colorClass, bgClass } = getFootprintLabel(result.vs_global_average_pct);

  return (
    <section
      aria-labelledby="results-heading"
      aria-live="polite"
      aria-atomic="true"
      className="space-y-6 animate-slide-up"
    >
      {/* Total Footprint Hero */}
      <div className="card p-8 text-center">
        <h2 id="results-heading" className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
          Your Annual Carbon Footprint
        </h2>
        <div className="flex items-end justify-center gap-2 mb-4">
          <span className="text-5xl font-semibold text-gray-900 tabular-nums tracking-tight">
            {formatKg(result.total_kg)}
          </span>
          <span className="text-xl text-gray-400 mb-1">CO₂e</span>
        </div>
        <span
          className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colorClass} ${bgClass}`}
        >
          {label}
        </span>
      </div>

      {/* Benchmark Comparisons */}
      <div className="card p-6 space-y-5">
        <h3 className="text-sm font-semibold text-gray-900">How You Compare</h3>
        <ComparisonBar
          id="global-average-bar"
          label="vs Global Average"
          pct={result.vs_global_average_pct}
          benchmark="global average"
          benchmarkKg={4000}
        />
        <ComparisonBar
          id="paris-target-bar"
          label="vs Paris 1.5°C Target"
          pct={result.vs_paris_target_pct}
          benchmark="Paris climate target"
          benchmarkKg={2000}
        />
        <p className="text-xs text-gray-400 pt-2 border-t border-gray-100">
          Sources: Our World in Data 2023 (global avg) · IPCC SR1.5 (Paris target)
        </p>
      </div>

      {/* Category Chart */}
      <div className="card p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Breakdown by Category</h3>
        <CategoryChart breakdown={result.breakdown} ranked_categories={result.ranked_categories} />
      </div>

      {/* Get Insights CTA */}
      {!insights && (
        <div className="flex justify-center">
          <button
            onClick={fetchInsights}
            disabled={isLoadingInsights}
            aria-busy={isLoadingInsights}
            aria-label={
              isLoadingInsights
                ? 'Loading your personalised reduction plan...'
                : 'Get personalised carbon reduction insights powered by Google Gemini AI'
            }
            className="
              inline-flex items-center justify-center gap-2 bg-primary-600
              text-white px-8 py-3 rounded-lg text-sm font-medium
              hover:bg-primary-700
              focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors duration-150 min-w-[240px]
            "
          >
            {isLoadingInsights ? (
              <LoadingSpinner label="Generating insights..." size="sm" />
            ) : (
              'Get Personalised Insights'
            )}
          </button>
        </div>
      )}
    </section>
  );
};
