const globals = require('globals');

module.exports = [
  { ignores: ['node_modules/**', '.npm-cache/**', 'output/**', 'tmp/**', 'dist/**'] },
  {
    files: ['**/*.js', '**/*.cjs'],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'script',
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      'no-undef': 'error',
      'no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-dupe-keys': 'error',
      'no-duplicate-case': 'error',
      'no-unreachable': 'error',
      'no-constant-condition': 'error',
      'no-unsafe-optional-chaining': 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      eqeqeq: 'error',
      'prefer-const': 'error',
    },
  },
];
