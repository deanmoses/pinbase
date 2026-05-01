# Media Hosting & CDN Provider Requirements

## Background

The media plan in [Media.md](Media.md) selected Cloudflare R2 partly on the assumption that we could put Cloudflare's CDN in front of an R2 bucket via a custom domain on `flipcommons.org`. **That assumption is wrong.** Cloudflare requires the custom domain's DNS to be hosted on Cloudflare to serve a public R2 bucket through it, and we are not moving `flipcommons.org` DNS to Cloudflare.

This doc captures the requirements we use to evaluate replacement storage + CDN providers. The evaluation itself, with options compared and a recommendation, lives in [MediaHostingProviderOptions.md](MediaHostingProviderOptions.md).

## Requirements

1. **No DNS hosting dependency.** DNS stays hosted where it is today. I'm assuming we have to do CNAME validation.
2. **S3-compatible API.** `django-storages` with the S3 backend is already wired up in [backend/config/settings.py](../../../backend/config/settings.py) using the boto3 library; provider-neutral env vars (`MEDIA_STORAGE_BUCKET`, `MEDIA_STORAGE_ENDPOINT`, etc.) are already in place.
3. **Custom `media.flipcommons.org` subdomain for serving.** Public URLs go in API responses and we don't want them pointing at a vendor hostname.
4. **Operational simplicity.** Setup, ongoing config, and troubleshooting should be navigable by a volunteer dev without specialized training. No enterprise IAM-style permission systems to debug, no vendor-specific concepts (VCL, edge runtimes, complex service hierarchies) to learn just to operate a media bucket. Friendly self-serve UX matters more than feature breadth.
5. **Managed TLS without certificate handling.** `media.flipcommons.org` must get HTTPS through provider-managed certificate issuance and renewal. No manually generated certificates, no uploaded private keys, no recurring certificate-renewal chores, and no requirement to move DNS hosting to the media provider just to get managed TLS.
6. **Production-grade serving.** No "dev only / rate-limited / no SLA" public URLs in front of real users.
7. **Viability.** Preferably with a vendor we know won't go out of business.
8. **Storage location.** We'd prefer file storage close to Chicago, to optimize for perf of cold reads near the museum. Second choice would be US-East.
   1. Justification: the museum's in Chicago, a lot of the reads will happen there, we'll have a CDN POP in Chicago, and I want cold image serving to be fast to Chicago specifically Especially at first, when the site isn't used much, I expect lots of images won't be hit every day. Dunno how long files stay in CDN cache...
   2. If we were optimizing for writes we'd put it near the Railway-hosted website in US-East (Virginia), but writes are much less frequent and future presigned uploads could remove app-region write latency.
9. **Inexpensive.** Under around $10/month at launch, including custom domain if they charge for it, with no unbounded egress risk. Stays cheap as the catalog grows. Egress is the historical blowup.
10. After doing a comparison, they all seem to be under $10/month. Cost doesn't seem to be a big decision point between them.
11. **Hosting-independent.** If media is stored at the same provider as Railway, the decision to leave Railway for app hosting and the decision to leave for media hosting must remain independent.
12. **API URLs do not have to be stable** across a future migration.
13. **Storage keys stay vendor-neutral.** Already true: `catalog-media/{uuid}/...`.

## CDN

We will be hooking up a CDN to file-serving at the same time.

### CDN facts

- **UUID filenames**. The media filenames are all UUIDs.
- **Immutable contents**. The media file contents are immutable, so cache forever.

### CDN requirements

- **Chicago-area POP.** A CDN with a POP near Chicago specifically, where the museum is located.
- **Global POPs.** A CDN with POPs globally, not one that just focuses on a region (like mainly US or mainly Europe)
- **Same provider as file storage... or not?** I thought I'd like to have the same provider for both CDN and file storage, for operational simplicity, but it sounds like it might be better to get separate file and CDN providers, both best-in-breed and both focusing on simplicity for non-devops users.
- **Private origin**. I'd prefer the connection between the CDN and the origin to be private. This is not a hard requirement, because the media filenames are all UUIDs, meaning as long as the bucket doesn't list its contents, we could live with a public origin, though I'd RATHER a private connection between the CDN and the bucket

## Perf might be the tie-breaker

As long as the biggest requirements are satisfied -- things like cost, operational simplicity, auto-cert-rotation, DNS hosting, viability -- then maybe let's decide on perf.

Cold image serving should fast. To Chicago specifically, if not everywhere. Especially at first, when the site isn't used much, I expect lots of images won't be hit every day.

## Providers to avoid in possible

1. **Avoid Cloudflare if possible.** I'm feeling a bit burned on Cloudflare's insistence on hosting the DNS, and we have some moral objections to Cloudflare. We'd like a path that lets us leave Cloudflare entirely, including for ingest. No Cloudflare file storage, no Cloudflare CDN.
2. **Avoid AWS if possible.** AWS is too operationally complex for non-devops volunteer devs (IAM config, Cloudfront config billing surface). We don't use it for anything today, it doesn't feel like the moment to start if we can find something more simple but equally as robust.

## Capabilities of interest (not requirements)

These don't drive the launch decision but are worth knowing because they affect future work:

- **Image transformation on the fly** (`?w=400&format=webp`-style URL params): strong interest. We'd plausibly replace our server-side Pillow rendition pipeline with this in a future PR. Not in the initial cutover — one thing at a time.
- **Video transcoding pipeline** (upload source → HLS renditions + poster). Interest, not commitment. Affects [Media.md:633-635](Media.md#L633-L635) (the future video transcoding worker).
- **Adaptive bitrate streaming** (HLS/DASH delivery). Same — interest, not commitment.

## Non-requirements

- Video support is not yet needed.
- Direct creator upload widgets, signed URLs for gated content.

## Next

See [MediaHostingProviderOptions.md](MediaHostingProviderOptions.md) for the evaluation of specific providers against these requirements, including a recommendation.
