/**
 * App — Main application layout with ARIA landmarks.
 *
 * Accessibility features:
 *   - role="banner" on header
 *   - <nav aria-label="Main navigation">
 *   - id="main-content" tabIndex={-1} as skip-link target
 *   - role="contentinfo" on footer
 *   - Error boundary wraps the entire app
 */

import { useEffect } from 'react';
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { SkipLink } from './components/shared/SkipLink';
import { LoadingSpinner } from './components/shared/LoadingSpinner';
import { CarbonForm } from './components/Calculator/CarbonForm';
import { ResultsDisplay } from './components/Calculator/ResultsDisplay';
import { InsightsList } from './components/Insights/InsightsList';
import { HistoryChart } from './components/History/HistoryChart';
import { HistoryTable } from './components/History/HistoryTable';
import { useCarbonStore } from './store/carbonStore';

const NavLink = ({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) => (
  <button
    onClick={onClick}
    aria-current={active ? 'page' : undefined}
    className={`
      px-3 py-1.5 rounded-lg text-sm font-medium transition-colors duration-150
      focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
      ${active ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}
    `}
  >
    {label}
  </button>
);

function AppContent() {
  const step = useCarbonStore(s => s.step);
  const setStep = useCarbonStore(s => s.setStep);
  const result = useCarbonStore(s => s.result);
  const insights = useCarbonStore(s => s.insights);
  const history = useCarbonStore(s => s.history);
  const isLoadingHistory = useCarbonStore(s => s.isLoadingHistory);
  const fetchHistory = useCarbonStore(s => s.fetchHistory);
  const reset = useCarbonStore(s => s.reset);

  const handleHistoryClick = () => {
    setStep('history');
    fetchHistory();
  };

  // Focus main content area on step change (for keyboard/screen reader users)
  useEffect(() => {
    const main = document.getElementById('main-content');
    if (main) main.focus();
  }, [step]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Skip Link */}
      <SkipLink />

      {/* ------------------------------------------------------------------ */}
      {/* Header / Navigation                                                  */}
      {/* ------------------------------------------------------------------ */}
      <header
        role="banner"
        className="sticky top-0 z-40 bg-white/95 backdrop-blur-sm border-b border-gray-200"
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          {/* Logo */}
          <button
            onClick={reset}
            aria-label="CarbonCompass — return to calculator"
            className="flex items-center gap-2.5 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-lg p-1"
          >
            <span
              aria-hidden="true"
              className="flex h-7 w-7 items-center justify-center rounded-md bg-primary-600 text-white text-sm font-semibold"
            >
              C
            </span>
            <div className="text-left">
              <span className="block text-sm font-semibold text-gray-900 leading-tight">
                CarbonCompass
              </span>
              <span className="block text-xs text-gray-400 leading-tight">
                Understand · Track · Reduce
              </span>
            </div>
          </button>

          {/* Navigation */}
          <nav aria-label="Main navigation">
            <ul className="flex items-center gap-1 list-none m-0 p-0">
              <li>
                <NavLink
                  label="Calculate"
                  active={step === 'form' || step === 'results'}
                  onClick={() => setStep(result ? 'results' : 'form')}
                />
              </li>
              <li>
                <NavLink label="History" active={step === 'history'} onClick={handleHistoryClick} />
              </li>
            </ul>
          </nav>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Intro (only on form step)                                            */}
      {/* ------------------------------------------------------------------ */}
      {step === 'form' && (
        <div className="border-b border-gray-200 bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary-600 mb-3">
              Personal carbon footprint
            </p>
            <h1 className="text-3xl sm:text-[2.6rem] font-bold text-gray-900 max-w-2xl leading-[1.1]">
              Know your number.
              <br className="hidden sm:block" /> Then bring it down.
            </h1>
            <p className="text-gray-500 text-base max-w-2xl mt-4 leading-relaxed">
              Answer a few questions about how you travel, power your home, eat, and shop.
              CarbonCompass turns it into a yearly CO₂e estimate — and three actions that cut the
              most.
            </p>
            <dl className="flex flex-wrap gap-x-10 gap-y-3 mt-7">
              <div>
                <dt className="text-xs text-gray-400">Global average</dt>
                <dd className="text-lg font-semibold text-gray-900 tabular-nums">
                  4,000 <span className="text-sm font-normal text-gray-400">kg/yr</span>
                </dd>
              </div>
              <div className="sm:border-l sm:border-gray-200 sm:pl-10">
                <dt className="text-xs text-gray-400">Paris 1.5°C target</dt>
                <dd className="text-lg font-semibold text-gray-900 tabular-nums">
                  2,000 <span className="text-sm font-normal text-gray-400">kg/yr</span>
                </dd>
              </div>
              <div className="sm:border-l sm:border-gray-200 sm:pl-10">
                <dt className="text-xs text-gray-400">Your estimate</dt>
                <dd className="text-lg font-semibold text-primary-600">~30 seconds</dd>
              </div>
            </dl>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Main Content                                                         */}
      {/* ------------------------------------------------------------------ */}
      <main
        id="main-content"
        tabIndex={-1}
        aria-label="Main content"
        className="max-w-4xl mx-auto px-4 sm:px-6 py-8 focus:outline-none"
      >
        {step === 'form' && <CarbonForm />}

        {step === 'results' && result && (
          <div className="space-y-8">
            {/* Back button */}
            <button
              onClick={() => setStep('form')}
              aria-label="Back to calculator form"
              className="
                flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900
                focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-lg px-2 py-1
                transition-colors duration-150
              "
            >
              <span aria-hidden="true">←</span> Back to Calculator
            </button>
            <ResultsDisplay result={result} />
            {insights && <InsightsList insightsResponse={insights} />}
          </div>
        )}

        {step === 'history' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900 mb-1">Your Carbon History</h1>
              <p className="text-gray-500 text-sm">
                Track your footprint over time to see the impact of your changes.
              </p>
            </div>
            {isLoadingHistory ? (
              <div className="flex justify-center py-16">
                <LoadingSpinner label="Loading your history..." size="lg" />
              </div>
            ) : (
              <>
                <HistoryChart history={history} />
                <HistoryTable history={history} />
              </>
            )}
          </div>
        )}
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* Footer                                                               */}
      {/* ------------------------------------------------------------------ */}
      <footer role="contentinfo" className="border-t border-gray-200 bg-white mt-16 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
            <div>
              <h2 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                Data Sources
              </h2>
              <ul className="text-xs text-gray-500 space-y-1 list-none">
                <li>UK DEFRA 2023 — Transport & Home Energy factors</li>
                <li>US EPA 2023 — Electricity grid emissions</li>
                <li>ICAO Carbon Calculator — Aviation emissions</li>
                <li>Our World in Data 2023 — Diet emissions & global average</li>
                <li>IPCC AR6 / SR1.5 — Consumption & Paris target</li>
              </ul>
            </div>
            <div>
              <h2 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                About
              </h2>
              <p className="text-xs text-gray-500 leading-relaxed">
                This tool provides estimates for educational purposes based on peer-reviewed
                emission factors. Individual results may vary based on local grid mix, vehicle
                efficiency, and personal circumstances.
              </p>
            </div>
          </div>
          <div className="border-t border-gray-100 pt-4 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-gray-400">
            <span>© 2026 CarbonCompass</span>
            <span className="flex items-center gap-1">
              Powered by{' '}
              <span aria-label="Google Gemini AI" className="font-medium text-gray-500">
                Google Gemini
              </span>{' '}
              ·{' '}
              <span aria-label="Google Cloud" className="font-medium text-gray-500">
                Google Cloud
              </span>
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}
