import path from 'path';
import { fileURLToPath } from 'url';
import pluginReactHooks from 'eslint-plugin-react-hooks';
import pluginTypescript from '@typescript-eslint/eslint-plugin';
import parserTypescript from '@typescript-eslint/parser';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default [
  {
    ignores: [
      '.next/**',
      'node_modules/**',
      'public/**',
      'out/**',
      'build/**',
      'next-env.d.ts',
      'lib/api.ts',
      'lib/api/*.ts'
    ],
  },
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      parser: parserTypescript,
      parserOptions: {
        ecmaVersion: 2020, // Specify ECMAScript version
        sourceType: 'module',
        jsx: true, // Enable JSX parsing
      },
      globals: {
        React: 'readonly',
      },
    },
    plugins: {
      'react-hooks': pluginReactHooks,
      '@typescript-eslint': pluginTypescript,
    },
    rules: {
      '@typescript-eslint/no-unused-vars': 'warn',
      '@typescript-eslint/no-explicit-any': 'warn',
      // Disable due to ESLint 9 incompatibility in v4 of the plugin
      // 'react-hooks/exhaustive-deps': 'error',
    },
  },
];
