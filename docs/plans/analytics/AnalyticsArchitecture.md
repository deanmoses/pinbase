# Analytics Architecture

## Decouple from Provider

We should use an internal analytics abstraction layer.

Do this:

```ts
ourCustomAnalytics.capture(...);
```

... instead of this:

```ts
someSpecificVendor.capture(...)
```

throughout the codebase.

Benefits:

- vendor independence
- centralized governance
- easier testing
- easier migration
- consistent event naming
- centralized privacy controls
