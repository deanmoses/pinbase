# Media Hosting Provider Options

This doc evaluates specific storage and CDN providers against the requirements in [MediaHostingProviderRequirements.md](MediaHostingProviderRequirements.md). Requirements are referenced below by name (e.g. "the production-grade serving requirement", "the managed-TLS requirement") rather than by number, since the requirement order may change.

Storage and CDN are evaluated separately. Unbundling them is the industry norm past the smallest scale; combining them at the recommendation step is the reader's job. The recommendation at the end picks one of each.

Cloudflare and AWS options are excluded by the avoid-Cloudflare and avoid-AWS preferences and are not evaluated here.

## File Storage Options

All assume `django-storages` with the S3-compatible backend. `MEDIA_STORAGE_BUCKET`, `MEDIA_STORAGE_ENDPOINT`, etc. are already wired up in [backend/config/settings.py](../../../backend/config/settings.py).

### Backblaze B2

- **S3 API**: GA, mature, very well-trodden in `django-storages` setups.
- **US-East**: Yes — Reston, Virginia (`us-east-005`) added in 2024. Verify GA status before committing.
- **Cost**: $0.006/GB-month. No minimum charge — pure per-GB. At launch volume: pennies/month. Egress: 3× free egress per month relative to storage volume, then $0.01/GB. Bandwidth Alliance partnership has historically given free egress to Bunny CDN (verify current terms).
- **Cold-read perf**: HDD-backed tier for cost. Cold-read TTFB is the slowest of the candidates here — public benchmarks have shown 100–200ms higher first-byte than Wasabi for similar workloads. With a CDN/cache layer in front this matters less for steady-state, but at low launch traffic where many images won't be cache-hot, it's perceptible.
- **Operational simplicity**: clean self-serve dashboard, application keys with bucket-scoped permissions. **Largest developer community of any candidate** — most tutorials, most Stack Overflow answers, deepest third-party docs.
- **Private origin**: yes — buckets can be private; CDN authenticates with application keys.
- **Viability**: publicly traded (NASDAQ: BLZE), founded 2007, ~$146M 2025 revenue. Audited financials. Strongest viability of the simple-vendor storage candidates.
- **Verdict**: best community/docs and strongest public-co viability, but slowest cold reads. Right pick if community size matters more than cold-read latency.

### DigitalOcean Spaces

- **S3 API**: GA, mature.
- **US-East**: `nyc3` (New York). ✓
- **Cost**: $5/month flat — includes 250 GB storage and 1 TB transfer. Floor is high relative to actual usage at launch.
- **Cold-read perf**: SSD-backed. Competitive with S3 for TTFB.
- **Operational simplicity**: friendliest self-serve UX of any candidate. Sign up, click Create Space, get keys.
- **Private origin**: yes — buckets can be private; access keys for CDN.
- **Note on Spaces CDN**: their bundled CDN is **not** considered here. Spaces CDN fails the managed-TLS requirement when DNS isn't hosted at DigitalOcean. As pure storage behind a different CDN, that issue doesn't apply.
- **Viability**: publicly traded (NYSE: DOCN), ~$901M 2025 revenue, profitable, founded 2011. Solid.
- **Verdict**: solid storage candidate, especially for operational simplicity. $5/month floor is the only real downside.

### Wasabi

- **S3 API**: GA, well-trodden. Multiple production `django-storages` users.
- **US-East**: `us-east-1` (Virginia) and `us-east-2` (Virginia). ✓
- **Cost**: $0.007/GB-month effective ($6.99/TB/month). **1 TB minimum charge** — pay ~$7/month even when storing a few GB. Egress free under "fair use" (egress ≤ monthly storage volume).
- **Cold-read perf**: SSD-forward architecture. Wasabi explicitly markets fast read latency as a differentiator and has independent benchmarks supporting it. Fast cold reads relative to B2 (~50–100ms TTFB in typical conditions).
- **Operational simplicity**: clean dashboard, standard S3-style access keys. Account signup is heavier than B2 (asks for more business info upfront). Smaller developer community than B2.
- **Private origin**: yes.
- **Quirks**: 90-day minimum retention — files deleted within 90 days still bill for the full 90 days. Annoying for us if we test large file uploads and then delete.
- **Viability**: privately held, founded 2017 by David Friend (co-founder of Carbonite). $250M+ raised, claims profitability. No public financials. Established storage business; smaller brand presence in the developer sphere than B2.
- **Verdict**: fast cold reads, simple operations, well-known in the production storage space. Trade-off vs. B2: faster perf, smaller community, private vs. public.

### iDrive e2

- **S3 API**: GA.
- **Chicago**: There's a Chicago data center!
- **US-East**: Virginia (`us-east-1`). ✓
- **Cost**: $0.005/GB-month ($5/TB) on pay-as-you-go, with a **1 TB minimum** ($5/month floor — same shape as Wasabi, just at $5 vs. $7). Egress: 3× active storage free, then $0.01/GB.
- **Cold-read perf**: marketed as performance-oriented and reportedly comparable to Wasabi. Less independent benchmarking than B2 or Wasabi.
- **Operational simplicity**: reasonable self-serve dashboard, standard S3-style access keys. **Smallest developer community** of the three S3-clone candidates — fewer tutorials and SO answers when stuck.
- **Private origin**: yes.
- **Viability**: privately held by iDrive Inc. (originally Pro Softnet), founded 1995. 30+ years operating. Long-running consumer-backup business; less brand recognition in the object-storage developer space than Wasabi or B2.
- **Verdict**: cheapest at scale, perf in the same class as Wasabi. Smallest developer community of the candidates. Good choice if cost matters; Wasabi is similar with better community presence.

### Akamai Object Storage

- **S3 API**: GA (formerly Linode Object Storage; Linode acquired by Akamai in 2022).
- **US-East**: Newark and Washington DC. ✓
- **Cost**: ~$5/month for 250 GB storage + 1 TB transfer. Similar shape to DO Spaces.
- **Cold-read perf**: competitive with DO Spaces and Wasabi. SSD-backed.
- **Operational simplicity**: the Linode-origin storage dashboard is self-serve and reasonable. Complexity arrives if paired with Akamai CDN (Property Manager) — see CDN section.
- **Private origin**: yes.
- **Note on built-in custom-domain feature**: Akamai Object Storage's own custom-domain TLS feature is only available for E0/E1 endpoint buckets and requires BYO TLS cert (manual upload, manual renewal). That fails the managed-TLS requirement. Pairing this storage with a different CDN (Bunny, Fastly) avoids the issue — the CDN handles TLS instead.
- **Viability**: publicly traded (NASDAQ: AKAM), ~$4.2B 2025 revenue, founded 1998. **Strongest viability of any candidate.**
- **Verdict**: solid storage with the strongest viability story. Pair with a non-Akamai CDN to dodge Property Manager.

### Fastly Object Storage

- **S3 API**: GA, S3-compatible, intended to work with Fastly Deliver and Compute services.
- **US-East**: `us-east` regional endpoint. Also supports `us-west` and `eu-central`.
- **Cost**: 5 GB free, then $0.02/GB-month up to 50 TB, with request charges after free operation quotas. Zero egress fees within the Fastly ecosystem.
- **Cold-read perf**: well-positioned given Fastly's edge infrastructure and the free internal egress to their CDN.
- **Operational simplicity**: Fastly's services/origins concepts apply to storage too. Bucket access keys are account-level by default unless managed through the API.
- **Private origin**: yes within the Fastly ecosystem; third-party CDN origin compatibility would need explicit verification because public bucket access is not supported.
- **Viability**: publicly traded (NYSE: FSLY), ~$624M 2025 revenue, founded 2011. Solid.
- **Verdict**: real product now, but most compelling when paired with Fastly CDN. Less attractive for a Bunny CDN launch because third-party private-origin behavior needs verification and the storage price is higher than the simpler S3-compatible candidates.

### ❌ Bunny Edge Storage

- **Status**: **Fails the S3-compatible API requirement.** As of 2026-04-30, Bunny's S3-compatible API is invite-only preview. Their GA API is a proprietary HTTP interface, not S3-compatible.
- **Verdict**: out for the launch decision. Reopen if/when their S3 API hits GA — at that point Bunny all-in (storage + CDN + Optimizer + Stream) becomes the strongest single-vendor candidate for our future capabilities.

## CDN Options

All CDN options assume the storage provider exposes an S3-compatible HTTPS origin and the CDN is configured as a pull zone with that origin.

### Bunny CDN

- **PoPs**: ~120+ globally. Chicago PoP: yes. Strong in EU/Asia, good in US.
- **Managed TLS**: free Let's Encrypt for custom hostnames via ACME HTTP-01 against the CDN endpoint. No DNS-on-Bunny required. Automatic renewal. ✓
- **Operational simplicity**: **the simplest of the three.** Create pull zone, set origin, attach custom hostname, click issue cert. ~15 minutes from zero for a volunteer with no Bunny background.
- **Cache features**: normal edge caching is built in. **Origin Shield** is an optional free secondary cache layer that consolidates origin misses through one shield region. **Perma-Cache** is optional and uses a Bunny Storage zone to keep long-tail content available from Bunny infrastructure even after edge eviction; useful for low-traffic sites where the long tail is mostly cold.
- **Cost**: Standard network is $0.01/GB for Europe and North America, higher in other regions. Volume network starts at $0.005/GB but uses a smaller 10-PoP network. Bunny has a $1 monthly minimum.
- **Viability**: privately held (BunnyWay d.o.o., Slovenia), founded 2015. Self-described profitable, ~70 employees, 100K+ customers. Smallest of the CDN candidates by a meaningful margin, but the CDN is swappable so the risk is bounded.
- **Verdict**: best operational simplicity. Right CDN for a volunteer-run setup unless viability concerns dominate.

### Fastly CDN

- **PoPs**: ~70, each typically very large. Chicago PoP: very strong. Performance benchmarks consistently rank Fastly among the fastest globally.
- **Managed TLS**: Fastly TLS service issues and renews managed certs via ACME, DNS-host-agnostic. ✓
- **Operational simplicity**: well-designed but more concepts to learn — services, origins, backends, optional VCL/rule snippets, configuration versions, activations. Volunteer onboarding requires real reading.
- **Cost**: free tier covers most launch traffic; past that, ~$0.12/GB egress (closer to AWS than Bunny). Wasabi has an explicit Fastly partnership — Wasabi → Fastly origin egress is free under their alliance.
- **Viability**: publicly traded (NYSE: FSLY), ~$624M 2025 revenue, founded 2011. Solid.
- **Verdict**: best raw perf (slightly), best public-company CDN viability, but operationally heavier than Bunny — cost is paid every time anyone touches the config.

### Akamai CDN (Property Manager)

- **PoPs**: ~4000+, the largest CDN network in the world. Chicago PoP: strong. Best for global reach to underserved regions.
- **Managed TLS**: Default DV certs, ACME-provisioned, DNS-host-agnostic via `_acme-challenge` CNAME. ✓
- **Operational simplicity**: **the heaviest of the three.** Property Manager is the enterprise CDN configuration apparatus: properties, behaviors, rule trees, CP codes, configuration versions and activations to staging and production networks. Same family of complexity as AWS CloudFront — well-designed but requires real expertise to configure.
- **Cost**: Akamai Object Storage's $5/month tier includes storage and a network transfer allowance, but not a self-serve Property Manager CDN product. Akamai CDN pricing is generally separate and quote-oriented.
- **Viability**: publicly traded (NASDAQ: AKAM), ~$4.2B 2025 revenue. Strongest viability of any CDN candidate.
- **Verdict**: best CDN reach and viability, worst operational simplicity. Right pick only if someone is willing to learn Property Manager.

## Decision

**Storage: iDrive e2.**
**CDN: Bunny CDN.**

### Why iDrive e2 for storage

#### Chicago data center

Fastest for CDN misses aka cold reads in the Chicago area

#### Performance

IDrive e2 is consistently faster than Backblaze B2 and Wasabi in terms of Time to First Byte (TTFB). It uses SSDs, avoids B2's HDD-tier latency.

#### Operational simplicity

I got it running very quicly. Clean self-serve dashboard, standard S3-style access keys.

#### No "90-Day Deletion" Trap

This is the biggest advantage over Wasabi.

    The Wasabi Problem: If you upload a 1GB video and delete it 5 minutes later, Wasabi charges you for that 1GB for the next 89 days.

    The IDrive Win: If a volunteer makes a mistake and deletes/replaces a file, the charge stops immediately. It’s much more forgiving for a dev environment.

#### Predictable "Flat" Pricing

    IDrive e2 costs $0.005 per GB/month ($5/TB), with a 1 TB minimum on pay-as-you-go (so a $5/month floor until storage exceeds 1 TB).

##### Generous egress allowance

    Unlike AWS S3, IDrive e2's free egress policy covers downloads up to 3× your active stored volume per month. Since traffic from the bucket to Bunny is bounded by what we store, in practice we expect to stay well within the free tier. Beyond 3× storage, overage egress is $0.01/GB.

#### Modern "Virtual Hosted" Support

Supports modern Virtual Hosted-Style URLs. This makes it 100% compatible with boto3 and Bunny.net’s security signatures. It’s built on a newer architecture than some of the older "Legacy" S3 clones.

#### Team Management

IDrive’s "Users" dashboard is much simpler for a volunteer board to understand than AWS IAM.

    You can invite other museum board members as Admins.

    They get their own logins.

    No one has to share a "Master Password."

#### Viability

iDrive is a privately held but established since 1995, long-running consumer-backup business.

#### Trade-off accepted: smaller developer community

Smaller developer community than B2 or Wasabi.

### Why Bunny for CDN

#### CDN Operational simplicity

I tried it out and it was dead simple to set up.

#### Managed TLS

Managed TLS\*\* via free Let's Encrypt — no DNS migration needed.

#### CDN Performance

Perf is good for our type of content (immutable images served to mostly-US viewers).

#### Chicago PoP

Bunny has Chicago presence, which matters for museum-adjacent cold/warm reads.

#### Supports S3 Private Origin

Bunny supports S3-style origin authentication fields, so it can pull from private S3-compatible buckets depending on the storage provider. Confirmed it works with iDrive E2.

#### Cache features

- Edge caching is built in. Origin Shield is free but must be enabled/configured.

#### Cold cache features

- Perma-Cache available if cold-cache prevalence becomes a problem at low launch traffic, to keep long-tail files warm if normal edge cache eviction causes too many cold origin reads.
