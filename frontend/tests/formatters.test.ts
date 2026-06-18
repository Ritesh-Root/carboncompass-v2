/**
 * Unit tests for formatting helpers — focused on boundary behaviour and the
 * device-id format contract that the backend enforces.
 */

import { describe, expect, it, beforeEach } from 'vitest';
import { formatKg, getDeviceId } from '../src/utils/formatters';

describe('formatKg boundaries', () => {
  it.each([
    [0, '0 kg'],
    [500, '500 kg'],
    [999, '999 kg'],
    [1000, '1.0t'],
    [1500, '1.5t'],
  ])('formats %d as %s', (input, expected) => {
    expect(formatKg(input)).toBe(expected);
  });

  it('rounds sub-tonne values up but still labels them in kg (documents the boundary)', () => {
    // The tonne check runs before rounding, so 999.6 stays in kg and rounds to 1000.
    expect(formatKg(999.6)).toBe('1000 kg');
  });
});

describe('getDeviceId format contract', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('always produces an id the backend regex accepts', () => {
    const deviceIdPattern = /^[a-zA-Z0-9_-]{8,64}$/;
    for (let i = 0; i < 100; i++) {
      sessionStorage.clear();
      expect(getDeviceId()).toMatch(deviceIdPattern);
    }
  });

  it('caches the id within a session', () => {
    const first = getDeviceId();
    expect(getDeviceId()).toBe(first);
  });
});
