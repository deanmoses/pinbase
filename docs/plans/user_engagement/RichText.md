# Rich Text Editing: How Much Editor Do Contributors Need?

## Background

The [UserEngagement](UserEngagement.md) plan bets that Pinbase wins contributors by being a better partner than the alternatives. IPDB has an opaque editorial queue. Wikipedia has intimidating bureaucracy — sourcing standards, notability guidelines, editorial norms. Pinbase's opening is: write something, it's live. No queue, no notability debate, no editorial norms to internalize.

The editor is a separate question from the engagement model. Contributors write in Markdown, which is itself a markup language — a simple one, but invisible to anyone who hasn't used it. Even basic formatting (bold, links, headings) is hidden behind keyboard shortcuts that a new contributor won't know exist. How much tooling is worth building to make that easier?

The answer depends on who the contributors actually are and where the real friction lies. Wikipedia's own research (below) found that removing markup was not the intervention that moved the engagement needle — the social and bureaucratic barriers mattered far more. Pinbase won't have those barriers, so the editor experience could matter more in relative terms, but it's not clear it's the highest-value investment right now.

## The Options

### 1. Current state: wikilinks autocomplete + keyboard shortcuts

The editor already supports `[[wikilink]]` autocomplete (type `[[` and get suggestions) and standard keyboard shortcuts for formatting (Ctrl+B for bold, etc.). Contributors write in Markdown but don't need to know the syntax if they use the shortcuts.

**Pros:** Already built. Zero additional engineering cost. Sufficient for technically comfortable contributors.

**Cons:** Formatting is completely undiscoverable. A contributor who doesn't already know Ctrl+B exists will type plain text and never realize formatting is available. The wikilink syntax (`[[Page Name]]`) is itself a markup convention that has to be learned.

### 2. Toolbar

A formatting toolbar above the editor with buttons for bold, italic, headings, links, wikilinks, and lists. Clicking a button inserts the corresponding Markdown. The contributor still sees Markdown in the editing area, but doesn't need to memorize syntax.

**Pros:** Makes formatting discoverable. Relatively cheap to build (a row of buttons that insert text). Keeps Markdown as the source format, avoiding the complexity of a separate document model. Familiar pattern — GitHub, Stack Overflow, and Discourse all use this approach.

**Cons:** Contributors still see raw Markdown while editing, which can be confusing if they're not expecting it. Doesn't fully deliver on the "no markup language" promise.

### 3. WYSIWYG editor

A full rich text editor (e.g. TipTap, ProseMirror, Lexical) where the editing surface looks like the final output. Bold text appears bold, headings appear large, links are clickable. No Markdown visible.

**Pros:** Fully delivers on the "no markup" promise. Lowest possible barrier to entry for non-technical contributors. The approach used by Notion, Confluence, and modern wiki products.

**Cons:** Significant engineering investment to build and maintain. Requires a document model that round-trips cleanly to/from Markdown storage. Ongoing maintenance burden as editor libraries evolve. Can introduce subtle formatting bugs that are hard to debug.

## Research

### Wikipedia VisualEditor: WYSIWYG didn't move the needle

Wikipedia shipped VisualEditor in 2013 — a full WYSIWYG editor built on a custom engine (Parsoid + OOjs UI) that lets contributors edit without seeing wikitext markup. It was a massive, multi-year engineering investment motivated by declining editor numbers.

The Wikimedia Foundation ran controlled studies on its impact:

- **May 2015 study:** Making VisualEditor the default for new editors showed no significant difference in first-edit rates, editor retention, or total contributions compared to the control group.
- **Earlier studies:** New editors using VisualEditor weren't reverted or blocked more often (good), but showed a measurable productivity loss — they edited less, likely because the editor was slower than the wikitext editor at the time.
- The overall measured impact was effectively zero on the metrics that mattered most: getting new people to make a first edit and getting them to come back.

**What this means for Pinbase:** Wikipedia's finding was that the editor wasn't the bottleneck — social barriers were (intimidating norms, reverts of newcomer edits, notability policies, editorial bureaucracy). Pinbase won't have those barriers, so the editor might matter more in relative terms. But the Wikipedia case is strong evidence that a WYSIWYG editor alone doesn't drive engagement, and the engineering cost is high.

Sources: [Wikimedia May 2015 study](https://meta.wikimedia.org/wiki/Research:VisualEditor%27s_effect_on_newly_registered_editors/May_2015_study), [VisualEditor research overview](https://meta.wikimedia.org/wiki/Research:VisualEditor), [VisualEditor/Why](https://en.wikipedia.org/wiki/Wikipedia:VisualEditor/Why)

### Notion vs. Confluence: the whole experience matters more than the editor

An often-cited anecdote: one organization that switched from Confluence to Notion saw their wiki grow from 200 to 800 pages in six months. But this was a complete product switch, not an editor change. Notion's advantage is the overall writing experience — clean interface, fast response, slash commands, drag-and-drop blocks — not any single editor feature.

Confluence has a WYSIWYG editor too, and it didn't prevent the engagement problem. The lesson: a pleasant, responsive writing experience matters more than the specific editor paradigm (WYSIWYG vs. toolbar vs. raw markup). A sluggish WYSIWYG is worse than a fast, clean Markdown editor.

Sources: [Notion vs Confluence 2026 comparison](https://saascrmreview.com/notion-vs-confluence/)

### Stack Overflow: toolbar + preview as the pragmatic middle

Stack Overflow uses a Markdown editor with a formatting toolbar and live preview (Stacks-Editor). They found that real-time preview — seeing the rendered output as you type — was the feature that mattered most for writing quality. They later built a hybrid editor that renders Markdown inline, closer to a WYSIWYG experience but without the complexity of a separate document model.

This is the approach GitHub, Discourse, and most developer-facing community platforms settled on. No controlled engagement studies are publicly available, but the convergence of multiple large platforms on this pattern is signal.

Sources: [Stacks-Editor (GitHub)](https://github.com/StackExchange/Stacks-Editor), [Stack Overflow editor design blog](https://stackoverflow.blog/2008/05/22/potential-markup-and-editing-choices/)

### The missing data: Pinbase's actual contributors

No external study directly answers the question for Pinbase, because the answer depends on who the contributors are. The [UserEngagement](UserEngagement.md) plan describes the initial contributor base as museum-connected pinball enthusiasts — a small, known, motivated group. Key unknowns:

- **Technical comfort.** Do these contributors use Markdown regularly, or is it foreign? If the former, keyboard shortcuts may be sufficient. If the latter, even a toolbar is a meaningful improvement.
- **Where the drop-off is.** Are people failing to start contributions, or starting and producing poorly-formatted content? The editor choice addresses the second problem, not the first.
