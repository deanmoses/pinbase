# Citations - Product Challenges

Design constraints and product hazards that should stay front-of-mind while Pinbase designs citations.

This is not the business case for citations and not the final design. It captures the main ways citation systems tend to fail in practice, so the feature can be designed around those failures rather than rediscovering them later.

See also:

- [Citations.md](Citations.md)
- [CitationsBusinessCase.md](CitationsBusinessCase.md)
- [CitationsPriorArt.md](CitationsPriorArt.md)
- [CitationsDesign.md](CitationsDesign.md)

## Core Challenge

**Citation systems impose too much complexity at the moment of authoring.**

That is the recurring product failure mode.

Wikimedia's own research on [Citoid support for Wikimedia references](https://meta.wikimedia.org/wiki/Research:Citoid_support_for_Wikimedia_references) describes references as an intricate system that is difficult for inexperienced or non-technical users to add correctly. The [Wikimedia Usability Initiative study](https://usability.wikimedia.org/wiki/Usability%2C_Experience%2C_and_Evaluation_Study) likewise found that adding references was one of the more challenging editing tasks. Wikimedia's later [Reusing references research](https://meta.wikimedia.org/wiki/WMDE_Technical_Wishes/Reusing_references/Research) shows that reuse, variation, and maintenance add another layer of difficulty. Similar friction appears outside Wikimedia too: [Obstacles to Dataset Citation Using Bibliographic Management Software](https://datascience.codata.org/articles/10.5334/dsj-2025-017) found that major reference managers often fail to import or export complete citation metadata accurately.

Pinbase should treat this as a core product challenge, not just a UI detail.

## Why This Happens

At citation time, editors often have to resolve too many things at once:

- what source they are citing
- how that source should be named
- which edition, version, or format matters
- what locator points to the relevant material
- how a reader can access the source
- whether an existing record should be reused or a new one created

Each of these questions is defensible on its own. The problem is that many citation systems force contributors to answer them all in one moment, while they are also trying to finish an edit.

## Design Challenges For Pinbase

### 1. Reduce authoring burden without lowering evidence quality

Pinbase wants stronger sourcing, not looser sourcing. But if adding a citation feels like mini-bibliography work, many contributors will either skip citations or add low-quality ones.

This is the central design tension.

### 2. Make reuse helpful, not bureaucratic

Shared citation sources are valuable, but the act of reusing a source cannot become a gate that slows ordinary editing to a crawl.

Search-first, quick-create-second is a likely direction, but the principle matters more than the exact workflow:

- reuse should be easy
- quick-create should also be easy

### 3. Support precision without demanding precision everywhere

Readers benefit from knowing what evidence supports which claims. Contributors do not want to hand-craft a scholarly apparatus for every paragraph.

Pinbase needs enough granularity to be trustworthy without demanding more precision than contributors will realistically maintain.

See [CitationGranularity.md](CitationGranularity.md).

### 4. Support rich evidence types without exploding the UI

Pinball evidence is not just books and URLs. It includes manuals, flyers, scans, videos, interviews, museum records, observations, and eventually museum-hosted reference copies.

The system needs to support this richer evidence model without turning citation entry into a branching maze of specialized forms.

### 5. Preserve long-term source quality without blocking contribution

Over time, Pinbase should get better at:

- reusing known sources
- upgrading access links
- attaching archive copies
- replacing poor scans with better ones
- merging duplicate source records

But none of those improvements should be prerequisites for saving an ordinary citation.

### 6. Keep the reader-facing trust signal honest

The read side should make evidence visible and legible, but it should not imply more certainty or precision than the underlying citation model can really support.

This matters for:

- citation granularity
- source naming
- locator presentation
- multiple sources on one claim
- zero-citation or weakly cited pages

## Product Opportunity

These challenges are also the opportunity.

If Pinbase can make citation authoring easier than wiki-style freehand citation systems while still preserving high-quality evidence, citations become a genuine product advantage rather than an editorial chore.

One especially promising direction is pre-seeding known sources so that contributors are usually selecting and locating rather than performing bibliographic data entry from scratch.

## Working Rule

While designing citations, the default question should be:

**Does this reduce or increase complexity at the moment of authoring?**

If a design choice improves metadata purity but makes contribution meaningfully harder, it should be treated skeptically unless the value is unusually high.
