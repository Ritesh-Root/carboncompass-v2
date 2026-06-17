/**
 * InsightCard — Single carbon reduction action card.
 *
 * Accessibility features:
 *   - <article> with descriptive aria-label
 *   - Priority badge is visually prominent and screen-reader legible
 *   - Category icon decorative (aria-hidden)
 */

import type { InsightItem } from '../../types';
import { formatKg, getCategoryIcon, formatCategory } from '../../utils/formatters';

interface InsightCardProps {
  insight: InsightItem;
  index: number;
}

const priorityColors = ['bg-primary-600', 'bg-primary-500', 'bg-primary-400'];

export const InsightCard = ({ insight, index }: InsightCardProps) => {
  const icon = getCategoryIcon(insight.category);
  const categoryLabel = formatCategory(insight.category);
  const saving = formatKg(insight.estimated_saving_kg);
  const badgeColor = priorityColors[index] ?? priorityColors[2];

  return (
    <article
      aria-label={`Insight ${index + 1}: ${categoryLabel} — ${insight.action}`}
      className="card p-5 transition-colors duration-150 hover:border-gray-300 animate-fade-in"
    >
      <div className="flex items-start gap-4">
        {/* Priority Badge */}
        <div className="flex-shrink-0 flex flex-col items-center gap-1">
          <span
            className={`
              ${badgeColor} text-white text-xs font-semibold
              w-7 h-7 rounded-full flex items-center justify-center
            `}
            aria-label={`Priority ${insight.priority}`}
          >
            {insight.priority}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Category header */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base" aria-hidden="true">
              {icon}
            </span>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              {categoryLabel}
            </span>
          </div>

          {/* Action text */}
          <p className="text-sm text-gray-700 leading-relaxed mb-3">{insight.action}</p>

          {/* Metrics row */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Saving */}
            <div className="flex items-center bg-primary-50 text-primary-800 rounded-md px-2.5 py-1">
              <span className="text-xs font-medium">Save ~{saving} CO₂e/year</span>
            </div>

            {/* Timeframe */}
            <div className="flex items-center bg-gray-50 text-gray-600 rounded-md px-2.5 py-1">
              <span className="text-xs">{insight.timeframe}</span>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
};
