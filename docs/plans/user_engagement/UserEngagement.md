# User Engagement: How this project Builds a Self-Sustaining Knowledge Base

## The Problem

Pinball has a rich, deep history — and it's slowly being lost. The people who know it best are aging out. The existing reference sites are either frozen (IPDB hasn't evolved in years) or noisy (Pinside buries knowledge in forum threads). There's no place where a passionate amateur historian can write a careful essay about the evolution of pop bumpers and have it live alongside authoritative catalog data, credited to them, improvable by others, and durable enough to outlive them.

That last part matters. The goal isn't just to collect knowledge — it's to build something that endures. A contribution to this project should still be useful in 20 years, even if the person who wrote it has moved on. This means the knowledge can't be locked to its original author. It has to be a living document that the community maintains, corrects, and deepens over time.

## The Constraints

This project is a project of The Flip, a volunteer-run museum. This means:

- **No dedicated moderation staff.** The museum director is motivated but time-limited. There is no team sitting in a queue approving edits. Any model that requires a human bottleneck will die the first week the bottleneck is busy.
- **Small initial contributor base.** At launch, contributors are a known group of museum-connected pinball enthusiasts. The community is small enough that people know each other.
- **Museum brand attached.** The site carries the museum's credibility. Content that's sloppy, wrong, or vandalized reflects on the institution. The quality floor matters even without paid staff to enforce it.

These constraints rule out two common models:

- **Pre-publication review** (Atlas Obscura, MusicBrainz) requires staff to process a queue. With volunteers, the queue becomes a graveyard.
- **Single-author content** (blogs, authored contributions) means pages die when their author loses interest. An encyclopedia for future generations can't afford that.

## The Model: Open Wiki, Community-Corrected

Edits go live immediately. No approval queue. No voting. The community self-corrects.

This is Wikipedia's model, and it works because of a counterintuitive insight: **you don't need gatekeepers if you make bad edits cheaper to fix than to prevent.** A one-click revert takes five seconds. A moderation queue takes days and demoralizes the contributor waiting in it.

### Why this works for this project specifically

**The vandalism risk is near zero.** Wikipedia needs semi-protection on articles about politicians and mass shootings because millions of people visit those pages with agendas. Nobody is edit-warring over the Gorgar page. If this ever changes, protection can be added reactively — building for today's actual threat level is smarter than building for Wikipedia's.

**The contributor base is self-selecting.** People who seek out a pinball encyclopedia to write about star rollovers are not the same population that vandalizes Wikipedia. The niche itself is a filter.

**The real risk is quality dilution, not vandalism.** A well-meaning but less skilled editor making a good essay worse. This is a real concern, but it's addressed by visibility and reversibility, not by gates.

## The Bet: Be a Great Partner to Contributors

Before stewardship, before watchlists, before any engagement mechanics — the first thing this project has to get right is the contribution experience itself. The hypothesis is simple: there are people who want to write about pinball history and upload their photo collections, and the existing options are bad enough that a good one wins by default.

IPDB requires submitting to an editorial team. You send in your contribution and wait. Maybe it gets published, maybe it doesn't. You have no control over how it's presented. The process is opaque and slow, and it's been this way for years. There's pent-up frustration among amateur historians who have knowledge to share and no good place to share it.

Wikipedia has the opposite problem: you can publish, but the bureaucracy around formatting, sourcing standards, notability guidelines, and editorial norms is intimidating. Writing a Wikipedia article is a skill in itself, separate from actually knowing the subject.

This project's opening is to be neither. Write something, it's live. Upload photos, they're on the page. No queue, no notability debate, no editorial norms to internalize. The contribution experience should feel like the site is a willing partner — it wants your knowledge and makes it easy to share. (For analysis of how much editor tooling is needed to deliver on this, see [RichText.md](RichText.md).)

This is the MVP of engagement. If the first contribution feels good enough that someone wants to do a second one, everything else follows. If it doesn't, no amount of gamification or community features will compensate.

## Why People Contribute: Stewardship and Visibility

An open wiki only works if people actually show up and write. Two motivations sustain long-term contribution:

### Stewardship

The primary motivator for sustained Wikipedia editors isn't edit counts or badges — it's identity. "I am the person who maintains the article on Bally Manufacturing, and that matters." The steward doesn't own the page, but they feel responsible for it. They watch it, they improve it, they defend it against bad edits. Game mechanics (contribution counts, awards) reinforce this identity, but the identity comes first.

This project needs to foster this. A contributor who writes a definitive history of Williams should feel like the steward of that page — not through exclusive control, but through visible association and the tools to maintain it (watchlists, edit history, their name in the contribution record).

### Visibility

Contributors need to feel recognized for their work. How this works in practice — what's shown on articles, on profiles, on photos — is a design problem with real tradeoffs. See [UserAttribution.md](UserAttribution.md) for the detailed analysis.

## How Quality Sustains Itself: The Correction Flywheel

Stewardship explains why people contribute. But an open wiki also needs mechanisms that make the community self-correcting — so that quality holds without moderators. These mechanisms form a progression, each handling a harder class of problem than the last:

### Edit history

Every version of every page is preserved. Nothing is ever truly lost. This is the foundation that makes everything else possible — contributors are braver about letting others edit their work when they know the original is one click away.

### Recent changes feed

A single page showing every edit across the site, in real time. This is the most underrated feature in Wikipedia's arsenal. Experienced Wikipedia editors are genuinely addicted to the recent changes page — it's how they find problems, discover new content, and feel the pulse of the project. At this project's scale, this feed is small enough to be browsable by anyone who cares. It turns passive readers into active stewards: "I just saw someone edited the Bally page — let me check if it's good."

### Watchlists

Contributors opt in to notifications when pages they care about are edited. This is how stewardship becomes operational: the person who wrote the System 11 essay doesn't approve edits to it, but they _notice_ them and can revert bad ones. The community polices itself because the people who care most are watching.

### One-click revert

Rolling back to any previous version is trivial. This changes the calculus of open editing: the worst case isn't "someone ruins the page," it's "someone ruins the page and it takes 5 seconds to fix." That's an acceptable risk.

### Talk pages

A discussion space attached to each article. Reverts handle clear-cut problems — vandalism, obvious errors. But some disagreements are genuine: "I think the Bally/Williams merger timeline is wrong, here's my source." That's not a revert, it's a conversation. Without a place for that conversation, disagreements become edit wars — two people reverting each other until one gives up. Talk pages turn conflicts into collaborative research. They're also where the community's shared understanding of accuracy develops over time: "We agreed last year that the primary source for this is the 1988 RePlay Magazine interview, not the Rogowski book." That institutional memory is what makes an encyclopedia authoritative rather than just editable.
