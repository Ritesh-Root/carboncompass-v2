/**
 * Unit tests for the Zustand carbon store.
 *
 * The store holds all async orchestration and error handling for the app. It
 * is mocked in every component test, so these tests exercise it directly with
 * a mocked apiClient — covering success paths, error paths, the non-Error
 * fallback messages, and the early-return guards.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCarbonStore } from '../src/store/carbonStore';
import { apiClient } from '../src/api/client';
import type { CarbonResult, HistoryEntry, InsightsResponse } from '../src/types';

vi.mock('../src/api/client', () => ({
  apiClient: {
    calculateFootprint: vi.fn(),
    getInsights: vi.fn(),
    saveEntry: vi.fn(),
    getHistory: vi.fn(),
  },
}));

const mockedApi = vi.mocked(apiClient);

const mockResult: CarbonResult = {
  total_kg: 6800,
  breakdown: { transport: 3000, home: 1300, diet: 2500, consumption: 1000 },
  vs_global_average_pct: 170,
  vs_paris_target_pct: 340,
  ranked_categories: [{ category: 'transport', kg: 3000, percentage: 44 }],
  device_id: 'test-device-001',
  diet_type: 'meat_medium',
  consumption_level: 'medium',
  flights_short_haul: 0,
  flights_long_haul: 0,
};

const mockInsights: InsightsResponse = {
  insights: [
    {
      category: 'transport',
      action: 'Take the train.',
      estimated_saving_kg: 800,
      timeframe: '30 days',
      priority: 1,
    },
  ],
  source: 'gemini',
  total_potential_saving_kg: 800,
};

const mockHistory: HistoryEntry[] = [
  {
    id: 'entry-1',
    timestamp: '2025-06-01T12:00:00Z',
    total_kg: 6800,
    breakdown: mockResult.breakdown,
    ranked_categories: mockResult.ranked_categories,
    insights: mockInsights.insights,
    vs_global_average_pct: 170,
    vs_paris_target_pct: 340,
  },
];

// A fully-formed CarbonInput is not needed by the mocked client, so cast a stub.
const stubInput = { device_id: 'test-device-001' } as never;

beforeEach(() => {
  vi.clearAllMocks();
  useCarbonStore.setState({
    inputs: {},
    result: null,
    insights: null,
    history: [],
    isCalculating: false,
    isLoadingInsights: false,
    isLoadingHistory: false,
    error: null,
    step: 'form',
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('carbonStore — calculate', () => {
  it('sets result, advances to results step, and clears flags on success', async () => {
    mockedApi.calculateFootprint.mockResolvedValue(mockResult);

    await useCarbonStore.getState().calculate(stubInput);

    const s = useCarbonStore.getState();
    expect(s.result).toEqual(mockResult);
    expect(s.step).toBe('results');
    expect(s.isCalculating).toBe(false);
    expect(s.insights).toBeNull();
    expect(s.error).toBeNull();
  });

  it('sets the thrown Error message and leaves result null on failure', async () => {
    mockedApi.calculateFootprint.mockRejectedValue(new Error('server exploded'));

    await useCarbonStore.getState().calculate(stubInput);

    const s = useCarbonStore.getState();
    expect(s.error).toBe('server exploded');
    expect(s.result).toBeNull();
    expect(s.isCalculating).toBe(false);
  });

  it('falls back to a generic message when a non-Error is thrown', async () => {
    mockedApi.calculateFootprint.mockRejectedValue('not an error object');

    await useCarbonStore.getState().calculate(stubInput);

    expect(useCarbonStore.getState().error).toBe('Failed to calculate footprint');
  });
});

describe('carbonStore — fetchInsights', () => {
  it('returns early and makes no request when there is no result', async () => {
    await useCarbonStore.getState().fetchInsights();
    expect(mockedApi.getInsights).not.toHaveBeenCalled();
  });

  it('sets insights on success', async () => {
    useCarbonStore.setState({ result: mockResult });
    mockedApi.getInsights.mockResolvedValue(mockInsights);

    await useCarbonStore.getState().fetchInsights();

    const s = useCarbonStore.getState();
    expect(s.insights).toEqual(mockInsights);
    expect(s.isLoadingInsights).toBe(false);
  });

  it('sets the Error message on failure', async () => {
    useCarbonStore.setState({ result: mockResult });
    mockedApi.getInsights.mockRejectedValue(new Error('gemini down'));

    await useCarbonStore.getState().fetchInsights();

    expect(useCarbonStore.getState().error).toBe('gemini down');
  });

  it('falls back to a generic message on a non-Error failure', async () => {
    useCarbonStore.setState({ result: mockResult });
    mockedApi.getInsights.mockRejectedValue(42);

    await useCarbonStore.getState().fetchInsights();

    expect(useCarbonStore.getState().error).toBe('Failed to fetch insights');
  });
});

describe('carbonStore — saveEntry', () => {
  it('returns early when result or insights are missing', async () => {
    useCarbonStore.setState({ result: mockResult, insights: null });
    await useCarbonStore.getState().saveEntry();
    expect(mockedApi.saveEntry).not.toHaveBeenCalled();
  });

  it('calls the API when result and insights are present', async () => {
    useCarbonStore.setState({ result: mockResult, insights: mockInsights });
    mockedApi.saveEntry.mockResolvedValue({ id: 'doc-1', saved_at: '2025-06-01T12:00:00Z' });

    await useCarbonStore.getState().saveEntry();

    expect(mockedApi.saveEntry).toHaveBeenCalledWith(mockResult, mockInsights.insights);
  });

  it('swallows failures without surfacing an error to the user', async () => {
    const consoleErr = vi.spyOn(console, 'error').mockImplementation(() => {});
    useCarbonStore.setState({ result: mockResult, insights: mockInsights });
    mockedApi.saveEntry.mockRejectedValue(new Error('write failed'));

    await expect(useCarbonStore.getState().saveEntry()).resolves.toBeUndefined();

    expect(useCarbonStore.getState().error).toBeNull();
    expect(consoleErr).toHaveBeenCalled();
  });
});

describe('carbonStore — fetchHistory', () => {
  it('sets history on success', async () => {
    mockedApi.getHistory.mockResolvedValue(mockHistory);

    await useCarbonStore.getState().fetchHistory();

    const s = useCarbonStore.getState();
    expect(s.history).toEqual(mockHistory);
    expect(s.isLoadingHistory).toBe(false);
  });

  it('sets the Error message on failure', async () => {
    mockedApi.getHistory.mockRejectedValue(new Error('history unavailable'));

    await useCarbonStore.getState().fetchHistory();

    expect(useCarbonStore.getState().error).toBe('history unavailable');
  });

  it('falls back to a generic message on a non-Error failure', async () => {
    mockedApi.getHistory.mockRejectedValue(null);

    await useCarbonStore.getState().fetchHistory();

    expect(useCarbonStore.getState().error).toBe('Failed to load history');
  });
});

describe('carbonStore — synchronous actions', () => {
  it('merges inputs with setInputs', () => {
    useCarbonStore.getState().setInputs({ household_size: 3 });
    useCarbonStore.getState().setInputs({ diet_type: 'vegan' });
    expect(useCarbonStore.getState().inputs).toEqual({ household_size: 3, diet_type: 'vegan' });
  });

  it('sets the step', () => {
    useCarbonStore.getState().setStep('history');
    expect(useCarbonStore.getState().step).toBe('history');
  });

  it('clears the error', () => {
    useCarbonStore.setState({ error: 'something' });
    useCarbonStore.getState().clearError();
    expect(useCarbonStore.getState().error).toBeNull();
  });

  it('resets data and returns to the form step', () => {
    useCarbonStore.setState({ result: mockResult, insights: mockInsights, step: 'results' });
    useCarbonStore.getState().reset();
    const s = useCarbonStore.getState();
    expect(s.result).toBeNull();
    expect(s.insights).toBeNull();
    expect(s.step).toBe('form');
  });
});
