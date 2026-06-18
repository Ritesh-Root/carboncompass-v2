import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      thresholds: {
        lines: 90,
        functions: 90,
        branches: 85,
        statements: 90,
      },
      exclude: [
        'node_modules/**',
        'tests/**',
        'dist/**',
        '**/*.config.*',
        '**/index.ts',
        // App shell / bootstrap — wiring of already-unit-tested pieces.
        'src/main.tsx',
        'src/App.tsx',
        // Thin presentational/infra shells with no branching logic.
        'src/components/shared/ErrorBoundary.tsx',
        'src/components/shared/SkipLink.tsx',
      ],
    },
  },
});
