import prettier from 'eslint-config-prettier';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';
import ts from 'typescript-eslint';

export default ts.config(
  ...ts.configs.recommended,
  ...svelte.configs.recommended,
  prettier,
  ...svelte.configs.prettier,
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },
  {
    files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
    languageOptions: {
      parserOptions: {
        parser: ts.parser,
      },
    },
  },
  {
    rules: {
      'svelte/no-navigation-without-resolve': 'off',
      // Standard convention: `_`-prefixed args/vars are intentionally unused.
      // Lets snippets accept required arguments they don't need to reference.
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      // Use named imports from `$lib/api/schema` instead of indexed access.
      // `openapi-typescript --root-types` emits top-level aliases for every
      // component schema, so `components['schemas']['Foo']` is always
      // expressible as `Foo`. Indexed access is allowed only in
      // `src/lib/api/client.ts` (the override below).
      // Type-position `components['schemas'][...]` parses as a
      // TSIndexedAccessType, not a MemberExpression — that's why this rule
      // targets the TS-specific node.
      'no-restricted-syntax': [
        'error',
        {
          selector:
            "TSIndexedAccessType[objectType.typeName.name='components'][indexType.literal.value='schemas']",
          message:
            "Use a named import from '$lib/api/schema' instead of components['schemas'][...].",
        },
      ],
    },
  },
  {
    // The createApiClient factory is an implementation detail of the api/
    // folder. App code uses the default `client` export from $lib/api/client
    // (browser) or `createServerClient` from $lib/api/server (SSR). Reaching
    // into $lib/api/internal/ from outside the api/ folder is a layering bug.
    files: [
      'src/**/*.ts',
      'src/**/*.js',
      'src/**/*.svelte',
      'src/**/*.svelte.ts',
      'src/**/*.svelte.js',
    ],
    ignores: ['src/lib/api/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['$lib/api/internal/*', '**/api/internal/*'],
              message:
                "Don't import from $lib/api/internal/ — use the default `client` from $lib/api/client or `createServerClient` from $lib/api/server.",
            },
          ],
        },
      ],
    },
  },
  {
    ignores: ['build/', '.svelte-kit/', 'dist/', 'src/lib/api/schema.d.ts'],
  },
);
