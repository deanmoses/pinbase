# Documentation

This directory contains the stable product, architecture, development, and operations documentation for Flipcommons.

For setup and common commands, start with the repository [README](../README.md). For historical design notes and implementation plans, use [plans/README.md](plans/README.md).

## Start Here

- [Overview.md](Overview.md) explains what Flipcommons is, who it serves, and why the product is shaped the way it is.
- [Development.md](Development.md) contributor-facing hub for working in this codebase.
- [Architecture.md](Architecture.md) gives the top-level system map.
- [DomainModel.md](DomainModel.md) explains the catalog's pinball domain model.

## Product And Domain

- [Definitions.md](Definitions.md) defines pinball terminology used by the product and data model.
- [Personas.md](Personas.md) describes the main user groups the product serves.
- [DomainModel.md](DomainModel.md) documents titles, models, variants, series, and related catalog concepts.
- [SingleModelTitles.md](SingleModelTitles.md) explains how the product handles titles with exactly one model.
- [RecordLifecycle.md](RecordLifecycle.md) covers creation, deletion, restore, and duplicate-prevention semantics.
- [Privacy.md](Privacy.md) captures privacy principles and analytics expectations.
- [SmallTeam.md](SmallTeam.md) records operating principles for a small team.

## System Architecture

- [Architecture.md](Architecture.md) overall Django + SvelteKit system.
- [WebArchitecture.md](WebArchitecture.md) the web split, same-origin model, API layer, development proxy.
- [AppBoundaries.md](AppBoundaries.md) Django app responsibilities and dependency rules.
- [ApiDesign.md](ApiDesign.md) endpoint design and schema design heuristics.
- [Authz.md](Authz.md) authorization activities, policy gates, and capability surfaces.
- [Provenance.md](Provenance.md) claims, resolution, audit history, provenance invariants.
- [Media.md](Media.md) media storage, uploads, claims, attachment resolution.
- [Ingest.md](Ingest.md) external data sources and the ingest pipeline.
- [Hosting.md](Hosting.md) Railway deployment topology.
- [DeployAutomation.md](DeployAutomation.md) philosophy behind the deploy safeguards (refuse-don't-warn, two refusal phases).
- [BuildChecks.md](BuildChecks.md) build-phase refusal gate (Dockerfile, sourcemap upload, build-time secrets).
- [DeployChecks.md](DeployChecks.md) preDeploy refusal gate (Django system checks).

## Frontend

- [Svelte.md](Svelte.md) Svelte 5 authoring conventions and rendering strategy.
- [SSRConversion.md](SSRConversion.md) workflow for converting routes from CSR to SSR.
- [DetailLayoutPatterns.md](DetailLayoutPatterns.md) detail-page layout patterns.
- [TestingFrontend.md](TestingFrontend.md) frontend test tiers and DOM test patterns.

## Backend

- [Python.md](Python.md) backend typing and Python style decisions.
- [DataModeling.md](DataModeling.md) database modeling principles and constraint patterns.
- [EntityNaming.md](EntityNaming.md) entity naming rules and where canonical names live.
- [TestingBackend.md](TestingBackend.md) backend test strategy and constraint testing.

## Testing And Review

- [Testing.md](Testing.md) overall testing strategy.
- [Reviewing.md](Reviewing.md) repo-specific review priorities and checks.

## Agent Docs

- [AGENTS.src.md](AGENTS.src.md) is the source for generated AI-agent guidance. Do not edit generated `AGENTS.md` or `CLAUDE.md` directly.

## Historical Plans

- [plans/README.md](plans/README.md) how to use historical planning documents. Plan docs are useful for context and rationale, but they are not canonical current documentation.
