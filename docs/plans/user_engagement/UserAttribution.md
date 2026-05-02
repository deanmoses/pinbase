# User Attribution

How this project credits contributors — on articles, on photos, and on profiles.

## Article Attribution

Wikipedia deliberately does not show author credit on articles. There's no byline. Attribution is buried in the edit history tab, where you'd have to scroll through potentially thousands of edits to see who wrote what. Wikipedia's explicit policy is "no one owns an article," and suppressing visible credit reinforces that norm. This works at Wikipedia's scale because the mission and community are strong enough to sustain contribution without personal recognition.

This project is not Wikipedia. At this project's scale — dozens of contributors, not hundreds of thousands — recognition is personal rather than statistical. A contributor who writes a definitive history of the System 11 platform should see evidence of that contribution without digging through an edit log. One approach worth exploring: a "Contributors to this article" line on the article itself, listing the people who've meaningfully edited it. This makes contribution visible without implying single authorship, and it's compatible with the open wiki model — anyone can still edit, and their name joins the list.

The details of how this works (how many names to show, what threshold of contribution earns a listing, how to handle minor edits vs. substantial ones) are design problems to work through. The principle is: contribution to an article should be visible on the article.

## Photo Attribution

### Problem Statement

This project now accepts user-uploaded photos. When a user uploads a photo of a pinball machine, we know internally who uploaded it — but we haven't decided what to show publicly.

This is a product decision with real tension between competing values:

**Community building** wants visible credit. Attribution is a social reward. When contributors see their name next to their photos, they upload more. Sites with prominent attribution (Pinside, Wikimedia Commons, iNaturalist) sustain large, active contributor bases. Anonymous contribution systems tend to attract fewer and lower-quality submissions.

**Privacy** wants less visibility. Some users — especially those new to a community or uploading on behalf of someone else — don't want their name attached to every photo. IPDB found this was common enough to make credit opt-in, and they report that people specifically request anonymity.

**Accuracy** wants flexibility. The person who uploads a photo isn't always the person who took it. A museum volunteer might upload a batch of photos taken by a visiting collector. A friend might share a great shot from a show. Without a way to credit someone other than the uploader, the UI either misattributes or stays silent.

We need to decide: what does a visitor to this project see when they look at a photo, and how much control does the uploader have over that?

## Research

### Pinball sites

**IPDB** accepts an optional photographer credit per photo. They only display it if the submitter explicitly asks. Default is uncredited. This works for IPDB because they have a small editorial team that reviews every submission and can follow up with contributors. The tradeoff is that most photos on IPDB carry no credit at all.

**Pinside** always shows the uploader's username and avatar on photos. Users build visible contribution histories and reputation scores. This drives significant engagement — heavy contributors are recognized community members. The tradeoff is there's no privacy opt-out and no way to credit a different photographer.

### Other UGC sites

**Wikimedia Commons** has the richest attribution: uploader, author, license, source URL. It distinguishes between "own work" and third-party photos. All of this is displayed on file detail pages, not inline on articles. The tradeoff is a high-friction upload process.

**Flickr** always credits the uploader via their display name. No mechanism to credit a different photographer. Uploaders control their display name, which provides some privacy control.

**IMDb** shows "Added by [username]" on image detail pages. Gallery thumbnails show no attribution. No opt-out.

**Discogs** credits the uploader on the image detail page only. No opt-out, no alternate credit.

**iNaturalist** always shows "© [username]" with license info. Strong community norm around attribution. No opt-out.

### What the research suggests

Almost every successful UGC site shows the contributor's name by default. The sites that make credit optional (IPDB) tend to end up with mostly uncredited content — which makes the site feel impersonal and reduces the incentive to contribute.

The most common UI pattern is two-tier display:

- **Gallery / thumbnail view:** clean grid, no attribution clutter
- **Detail / lightbox view:** contributor name, upload date, optionally license

This two-tier approach is likely right for this project regardless of which attribution model we choose.

## Options

### Option A: Always show the uploader's name

Every photo shows the uploader's display name in the detail/lightbox view. No configuration, no opt-out.

- **Why it could work:** Simplest possible approach. 100% of photos are credited. Builds community identity from day one. Clear accountability for moderation. This is what Pinside, IMDb, Discogs, and iNaturalist do.
- **Why it might not:** No privacy opt-out — some users won't upload at all. Can't credit a different photographer. Changing this later means deciding what to do with existing photos.

### Option B: Optional credit (default: uncredited)

The upload form includes an optional "Photo credit" text field. When filled in, the credit is shown. When left blank, the photo appears with no public attribution. This is the IPDB model.

- **Why it could work:** Respects privacy by default. Supports crediting a third-party photographer.
- **Why it might not:** Optional fields on upload forms are overwhelmingly left blank. Expect 80-90% of photos to be uncredited, which makes the gallery feel impersonal and removes the community incentive. IPDB compensates with editorial curation; this project is self-serve and can't.

### Option C: Credit by default, with opt-out and override

The uploader's display name is shown by default. The uploader can replace it with a different name (to credit someone else) or choose to be anonymous.

- **Why it could work:** High default fill rate — the gallery feels alive with contributor names from day one. Handles all three cases: self-credit, third-party credit, and anonymous. Privacy-conscious users have an escape hatch. This inverts IPDB's default: credit on unless you ask for it off.
- **Why it might not:** More complex upload UX — an extra field that most users will ignore but some will need. Requires a clear way to distinguish "use my name" from "show no name" in the UI. Slightly more work to build than Option A.

### Option D: Separate credit and visibility

Always record who the photographer is (required, defaults to the uploader's name). Separately, let the uploader choose whether that credit is shown publicly.

- **Why it could work:** Cleanest data — always knows the photographer, separately from the display preference. No ambiguity between "didn't fill it in" and "wants to be anonymous." Closest to the Wikimedia model.
- **Why it might not:** Two controls on an upload form is more friction than one. The distinction between "who took this" and "should we show it" is meaningful at Wikimedia's scale but probably over-engineered for this project's current stage. A required credit field adds friction even when the uploader is the photographer (the common case).

## Decision

**Option A now, with a path to C later.**

Start by always showing the uploader's display name on the photo detail/lightbox view. No new fields, no configuration — just surface what we already track (`uploaded_by`). Gallery thumbnails stay clean with no attribution.

This is the right first step because:

- It's the simplest thing that works. No new data model, no upload UX changes.
- It establishes attribution as a norm from day one, before habits form around anonymity.
- Every photo uploaded under Option A remains correctly attributed if we later add opt-out or photographer override — no backfill needed.

**Future additions (not committed, just preserved as options):**

- **Opt-out:** Add an optional mechanism for uploaders to hide their name. Could be per-photo or account-wide. Only worth adding if users actually request it.
- **Photographer credit:** Add an optional field for crediting someone other than the uploader. Only worth adding if the "uploader ≠ photographer" case turns out to be common in practice.
