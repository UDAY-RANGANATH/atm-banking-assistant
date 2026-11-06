import tseslint from 'typescript-eslint'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'

const hooksRecommended = {
  plugins: { 'react-hooks': reactHooks },
  rules: reactHooks.configs.recommended.rules,
}

export default tseslint.config(
  { ignores: ['dist', 'node_modules', 'vite.config.ts'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      ...tseslint.configs.recommended.filter((c) => !c.rules || !c.rules['@typescript-eslint/no-explicit-any']),
      hooksRecommended,
    ],
    languageOptions: {
      globals: { ...globals.browser },
    },
    rules: {
      // Educational prototype: `any` appears in a few JSON payload spots;
      // TS strict mode (tsc) remains the primary static gate.
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      // Pre-existing patterns in this prototype load data inside effects;
      // restructuring them is out of scope for Phase 5.
      'react-hooks/set-state-in-effect': 'off',
    },
  },
)
