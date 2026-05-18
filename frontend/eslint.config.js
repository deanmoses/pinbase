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
    // `no-restricted-imports` policies. Both restrictions are colocated in a
    // single config block because ESLint flat config merges rule options by
    // override (last block wins) rather than by union — splitting them would
    // silently drop one of the two restrictions on overlapping files.
    //
    // - api/internal: the createApiClient factory is an implementation detail
    //   of the api/ folder. App code uses the default `client` export from
    //   $lib/api/client (browser) or `createServerClient` from $lib/api/server
    //   (SSR). Reaching into $lib/api/internal/ from outside api/ is a
    //   layering bug — the rule is suppressed inside src/lib/api/** via the
    //   per-file override below.
    // - posthog-js: the analytics vendor SDK. Only src/lib/analytics/posthog.ts
    //   may touch it; everywhere else routes through the abstraction in
    //   $lib/analytics. This keeps the vendor boundary one-file-wide so a
    //   future swap is mechanical (see
    //   docs/plans/analytics/AnalyticsArchitecture.md § Migration).
    files: [
      'src/**/*.ts',
      'src/**/*.js',
      'src/**/*.svelte',
      'src/**/*.svelte.ts',
      'src/**/*.svelte.js',
    ],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'posthog-js',
              message:
                "Don't import posthog-js directly — use the `analytics` export from $lib/analytics. Only src/lib/analytics/posthog.ts may touch the SDK.",
              allowTypeImports: true,
            },
          ],
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
    // The api/ folder is allowed to import from its own internals.
    files: ['src/lib/api/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'posthog-js',
              message:
                "Don't import posthog-js directly — use the `analytics` export from $lib/analytics. Only src/lib/analytics/posthog.ts may touch the SDK.",
              allowTypeImports: true,
            },
          ],
        },
      ],
    },
  },
  {
    // The PostHog adapter is the one file that's allowed to import the SDK.
    files: ['src/lib/analytics/posthog.ts'],
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
