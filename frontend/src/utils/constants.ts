/**
 * Shared client-side constants for the Carbon Footprint Awareness Platform.
 *
 * These benchmarks mirror the authoritative values in the backend
 * `app/carbon/factors.py` (GLOBAL_AVERAGE / PARIS_TARGET). Keeping a single
 * definition here avoids the same magic numbers drifting across the UI.
 */

/** Global per-capita average annual emissions (Our World in Data 2023), kg CO2e/year. */
export const GLOBAL_AVERAGE_KG = 4000;

/** Sustainable per-capita budget to limit warming to 1.5°C (IPCC SR1.5), kg CO2e/year. */
export const PARIS_TARGET_KG = 2000;
