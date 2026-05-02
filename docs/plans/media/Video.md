# Video Plan

> **⚠️ Outdated.** This plan predates the move to iDrive e2 + Bunny CDN and needs to be updated before it drives any work. The transcoding/playback vendor referenced below should be revisited; the rest of the architecture (claims, ownership boundary, separation of catalog truth from delivery infrastructure) still applies.

This document describes the product and architecture direction for user-uploaded video in this project. It covers Flipcommons-hosted video uploads only. Third-party videos remain external.

## Background

Video is not an image with a larger file size. It introduces a different class of product and operational concerns:

- uploads are much larger
- processing takes longer
- playback must adapt to device and network conditions
- users expect posters, scrubbing, and reliable streaming
- failures and long-running states are normal rather than exceptional

This project's current media architecture is intentionally simple for images. Upload happens in one request, processing is synchronous, and the request either succeeds or fails immediately. That model is a poor fit for video.

If this project handled video entirely itself, it would need a more complex ingestion pipeline: direct uploads, background processing, transcoding workers, status transitions, retries, monitoring, and streaming delivery concerns. That is a substantial amount of infrastructure for a feature that is not this project's core product.

## Justification

This project should own the product truth around video, but it should not own the transcoding platform.

The important things this project must control are:

- who uploaded the video
- which catalog entity it is attached to
- which category it belongs to
- whether it is primary
- whether it is published, visible, or moderated

Those are product and editorial concerns, and they fit naturally into this project's existing media and claims architecture.

Encoding pipelines, adaptive bitrate packaging, playback manifests, and streaming delivery are infrastructure concerns. They are expensive to build, easy to get partly wrong, and not where this project should spend its complexity budget.

Cloudflare Stream is a better fit for that layer. It provides direct uploads, asynchronous processing, managed playback formats, and globally distributed delivery without requiring this project to build and operate its own transcoding queue.

## Decision

This project should use Cloudflare Stream for Flipcommons-hosted video uploads and playback.

The key distinction is:

- This project remains the system of record for media ownership, attachment, moderation, and editorial decisions.
- Cloudflare Stream becomes the managed service for video ingestion, transcoding, storage, and playback delivery.

This is not "transcode on every request." Stream's model is upload first, process asynchronously, then serve the prepared video once ready. That is the right shape for user-uploaded video.

## Goals

- Support user-uploaded Flipcommons-hosted video without building our own transcoding stack.
- Keep media attachment truth claims-based and consistent with the rest of the media system.
- Provide a clear processing lifecycle for video assets.
- Support reliable playback across devices and connection qualities.
- Keep direct upload and large-file handling out of the main Django request path.
- Preserve the legal rule that third-party media stays external.

## Non-Goals

- No self-hosted transcoding worker system in this project.
- No re-hosting or proxying of third-party videos.
- No live streaming product in the initial plan.
- No in-app video editing suite, clipping workflow, or creator tools beyond upload and playback.
- No attempt to make video behave like synchronous image upload.

## Product Shape

From the user's perspective, video should behave like a managed asset with a visible lifecycle:

- uploading
- processing
- ready
- failed

That state is part of the product, not an implementation leak. Video cannot honestly promise the instant, atomic behavior that images can.

The UI should set that expectation clearly. Users upload a file, this project records the intended attachment, and the video becomes playable once processing is complete. Posters and playback should feel native to this project, but the system should not pretend that video is immediate when it is not.

## Architecture Shape

At a high level, the architecture should be:

1. This project creates the logical media asset and attachment intent.
2. The client uploads the video directly to Cloudflare Stream using a one-time upload flow.
3. Cloudflare Stream processes the video asynchronously.
4. This project learns the processing result through callbacks or status synchronization and updates the asset lifecycle.
5. Once ready, this project serves video metadata and playback references as part of its normal media APIs.

That keeps the heavy transfer and processing path out of the application server while preserving this project's control over product truth.

## Why Not Build This In-House

An in-house video pipeline would force this project to own several concerns that are not central to the product:

- large-file upload infrastructure
- resumable or direct-to-storage upload flows
- background job orchestration
- transcoding reliability
- poster generation
- stream packaging
- playback compatibility
- operational monitoring for long-running media jobs

That is a lot of surface area for a feature that can be delivered more safely through a managed service.

The result would not just be more code. It would be more operational burden, more failure modes, and more product delay.

## Relationship To Existing Media Architecture

This plan extends the current media model rather than replacing it.

`MediaAsset` still represents the logical uploaded item. `EntityMedia` still represents the resolved attachment truth. The difference is that video assets have a meaningful processing lifecycle and rely on an external managed video backend for their derived outputs and playback delivery.

That means the application model stays coherent:

- This project owns the asset record
- This project owns the attachment record
- Cloudflare Stream owns the video processing and delivery machinery

## Ownership Boundary

The same ownership rule used for images applies here.

This project video support is for media that this project has the right to store and display, such as videos uploaded by users under this project's terms or videos owned by The Flip Museum. Third-party videos remain references, not ingested assets.

This boundary matters for both legal reasons and system design. The managed video pipeline should only be used for content this project is actually entitled to host.

## Delivery and Access

Playback should be treated as a delivery concern, not a catalog-truth concern.

This project should decide which viewers are allowed to access a given video and what metadata the UI should see. Cloudflare Stream should handle the mechanics of delivering a playable video efficiently. If this project later needs signed playback, restricted access, or more nuanced publication states, that can be layered on top without changing the basic division of responsibility.

## Rollout Direction

The rollout should be staged:

1. Introduce video as a new media kind in the this project media model.
2. Add a product-visible processing lifecycle for video assets.
3. Integrate direct uploads to Cloudflare Stream.
4. Connect Stream processing results back into this project's asset status.
5. Add playback surfaces once the ingest and status model are stable.

This sequence keeps the work honest. This project should model the lifecycle first and only then expose polished playback on top of it.

## Success Criteria

This plan is successful when:

- This project can support user-uploaded video without operating our own transcoding queue
- large uploads do not flow through the normal application request path
- the UI can accurately show upload, processing, ready, and failed states
- playback is reliable across devices
- video remains consistent with this project's claims-based media attachment model
- third-party video remains outside our hosted storage
