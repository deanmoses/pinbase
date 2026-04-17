# Model And Title Detail/Edit UX

## Goal

Create a clearer information architecture for model and title detail pages across both the public read-only views as well as the authenticated edit flows.

The current UI mixes too many concerns:

- reader content
- record metadata
- edit workflows
- page-level navigation
- edit-section navigation

This becomes especially problematic on mobile, where the current tab model does not have enough room and the edit form becomes overwhelming.

## Core Principles

- Optimize first for the end-user reader, not the editor.

## Edit Interaction Model

The model and title edit screens should behave as a set of accordion sections rather than one large always-open form.

Core behavior:

- render the screen as named accordion sections
- only one section is edited at a time
- each section has its own `Edit`, `Save`, and `Cancel` controls
- saving applies only to the current section, not the whole page
- edit note and citation attach to the section being saved, not to the page as a whole

## Model Detail UX

### Model Reader View

Sections:

- Overview
- Specifications
- People
- Relationships
- Media

Utility actions (not part of the reading flow):

- Edit
- History
- Tools
  - Sources

### Model Edit

Sections:

- Overview
  - Model.Description
- Basics
  - Model.Title, Model.CorporateEntity (but label it Manufacturer)
  - Model.Name, Model.Slug
  - Model.Year, Model.Month
  - Model.Abbreviations
- Technology
  - Technology Generation, Technology Subgeneration
  - Display Type, Display Subtype
  - System
- Features
  - Game format, Cabinet
  - Reward types, Tags
  - Themes, Production quantity
  - \# Players, \# Flippers
  - Gameplay features
- Related Models
  - Variant of
  - Converted from
  - Remake of
- People
  - Person/Role rows
- Media
  - Photos & Videos
- External Data
  - Links
    - IPDB ID
    - OPDB ID
    - Pinside ID
  - Ratings
    - Pinside rating
    - IPDB rating
- Change Title
  - A dedicated section for changing the model's title?

## Title Detail UX

### Title Reader View

When showing a single-model title, the title reader view should look like the model view, but with the addition of title-specific fields like series & franchise. However, when showing a title with multiple models, it should have these accordion sections:

- Overview
- Models
- Specifications
  - Include Franchise / Series here
- People (hide if none/0)
- Media (hide if none/0)

Actions in top bar are same as Model page:

- Edit menu of sections
- History
- Tools menu
  - Sources

### Single-Model Title Edit

When clicking 'edit' on a single-model title, we need to think through what happens. For example:

- Do we need to make the title.name and title.slug editable? Or does it just follow the model.name and slug?
- The Description and Abbreviations of both Title and Model should not be visible/populated/editable; pick one.

I think we need to merge the edit of title and model on single-model titles... I'd actually prefer keeping them separate for users doing editing, on the assumption that those people have taken the time to understand the domain model a bit but there's no place to GO to get that separate edit view: for single-model titles, the only detail page is the Title one, so in my mind the Title detail page MUST provide access to the full editing experience.

Sections:

- Overview [The existing Model Overview section]
  - Model.Description
- Title Basics
  - Title.Name, Title.Slug
  - Title.Franchise, Title.Series
  - Title.Abbreviations
- Model Basics (a slimmed down version w/o name, slug, abbreviations)
  - Model.Corporate Entity (but label it Manufacturer)
  - Model.Year, Model.Month
- Technology [The existing Model Technology section]
  - Technology Generation, Technology Subgeneration
  - Display Type, Display Subtype
  - System
- Features [The existing Model Features section]
  - Game format, Cabinet
  - Reward types, Tags
  - Themes, Production quantity
  - \# Players, \# Flippers
  - Gameplay features
- Related Models [The existing Model Related Features section]
  - Variant of
  - Converted from
  - Remake of
- People [The existing Model People section]
  - Person/Role rows
- Media [The existing Model Media section]
  - Photos & Videos
- Model External Data [The existing Model External Data section]
  - Links
    - IPDB ID
    - opdb_machine_id
    - Pinside ID
  - Ratings
    - Pinside rating
    - IPDB rating
- Title External Data
  - Title.obdb_group_id
  - Title.fandom_page_id
- Change Title
  - A dedicated section for changing the model's title?

### Multi-Model Title Edit

Sections:

- Overview
  - Title.Description
- Title Basics
  - Title.Name, Title.Slug
  - Title.Franchise, Title.Series
  - Title.Abbreviations
- Title External Data
  - Title.obdb_group_id
  - Title.fandom_page_id

For multi-model titles, models are edited on their own page.
