"""End-to-end tests for the 8 simple-taxonomy entities' create/delete/restore.

Covers representative entities per the Phase 2 plan: ``tag`` (parentless),
``technology-subgeneration`` (parented), ``technology-generation`` (parent
with active-children blocking), and ``reward-type`` (shares the detail
schema for PATCH but uses the shared ``TaxonomySchema`` on create).
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.catalog.models import (
    DisplaySubtype,
    DisplayType,
    MachineModel,
    RewardType,
    RewardTypeAlias,
    Tag,
    TechnologyGeneration,
    TechnologySubgeneration,
    Title,
)
from apps.provenance.models import ChangeSet, ChangeSetAction, Claim

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="editor")


@pytest.fixture
def staff(db):
    return User.objects.create_user(username="admin", is_staff=True)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _post(client, path: str, body: dict):
    return client.post(path, data=json.dumps(body), content_type="application/json")


# ── Create: parentless (Tag) ────────────────────────────────────────


@pytest.mark.django_db
class TestTagCreate:
    def test_anonymous_rejected(self, client):
        resp = _post(client, "/api/tags/", {"name": "Widebody", "slug": "widebody"})
        assert resp.status_code in (401, 403)
        assert not Tag.objects.filter(slug="widebody").exists()

    def test_creates_tag_with_three_claims(self, client, user):
        client.force_login(user)
        resp = _post(client, "/api/tags/", {"name": "Widebody", "slug": "widebody"})
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["slug"] == "widebody"
        assert body["name"] == "Widebody"

        tag = Tag.objects.get(slug="widebody")
        assert tag.status == "active"

        cs = ChangeSet.objects.get(user=user, action=ChangeSetAction.CREATE)
        fields = set(
            Claim.objects.filter(changeset=cs).values_list("field_name", flat=True)
        )
        assert fields == {"name", "slug", "status"}

    def test_duplicate_name_rejected(self, client, user):
        Tag.objects.create(name="Widebody", slug="widebody-existing", status="active")
        client.force_login(user)
        resp = _post(client, "/api/tags/", {"name": "Widebody", "slug": "widebody-2"})
        assert resp.status_code == 422
        assert "name" in resp.json()["detail"]["field_errors"]

    def test_invalid_slug_rejected(self, client, user):
        client.force_login(user)
        resp = _post(
            client, "/api/tags/", {"name": "Widebody", "slug": "Widebody_Case"}
        )
        assert resp.status_code == 422
        assert "slug" in resp.json()["detail"]["field_errors"]

    def test_duplicate_slug_rejected(self, client, user):
        # Reserve the slug via a soft-deleted row — the slug is still taken
        # at the DB level, and the pre-check must surface a field error
        # rather than letting the insert fail with an IntegrityError.
        Tag.objects.create(name="Existing", slug="widebody", status="deleted")
        client.force_login(user)
        resp = _post(client, "/api/tags/", {"name": "Widebody", "slug": "widebody"})
        assert resp.status_code == 422
        assert "slug" in resp.json()["detail"]["field_errors"]
        assert not Tag.objects.filter(slug="widebody", status="active").exists()

    def test_name_too_long_rejected(self, client, user):
        client.force_login(user)
        resp = _post(
            client,
            "/api/tags/",
            {"name": "x" * 201, "slug": "too-long"},
        )
        assert resp.status_code == 422
        assert "name" in resp.json()["detail"]["field_errors"]


# ── Create: rate limit ─────────────────────────────────────────────


@pytest.mark.django_db
class TestCreateRateLimit:
    def test_non_staff_blocked_after_limit(self, client, user, settings):
        # Use whatever the shipped bucket is — just show enforcement bites.
        from apps.provenance.rate_limits import CREATE_RATE_LIMIT_SPEC

        client.force_login(user)
        limit = CREATE_RATE_LIMIT_SPEC.limit
        for i in range(limit):
            r = _post(client, "/api/tags/", {"name": f"Tag {i}", "slug": f"tag-{i}"})
            assert r.status_code == 201, r.content
        r = _post(client, "/api/tags/", {"name": "Tag over", "slug": "tag-over"})
        assert r.status_code == 429

    def test_staff_bypasses(self, client, staff):
        from apps.provenance.rate_limits import CREATE_RATE_LIMIT_SPEC

        client.force_login(staff)
        limit = CREATE_RATE_LIMIT_SPEC.limit
        for i in range(limit + 1):
            r = _post(client, "/api/tags/", {"name": f"Tag {i}", "slug": f"tag-{i}"})
            assert r.status_code == 201, r.content


# ── Create: parented (TechnologySubgeneration) ─────────────────────


@pytest.mark.django_db
class TestSubgenerationCreate:
    @pytest.fixture
    def parent(self, db):
        return TechnologyGeneration.objects.create(
            name="Solid State", slug="solid-state", status="active"
        )

    def test_creates_subgen_under_active_parent(self, client, user, parent):
        client.force_login(user)
        resp = _post(
            client,
            f"/api/technology-generations/{parent.slug}/subgenerations/",
            {"name": "MPU", "slug": "mpu"},
        )
        assert resp.status_code == 201, resp.content

        sub = TechnologySubgeneration.objects.get(slug="mpu")
        assert sub.technology_generation_id == parent.pk

        cs = ChangeSet.objects.get(user=user, action=ChangeSetAction.CREATE)
        claims = {c.field_name: c.value for c in Claim.objects.filter(changeset=cs)}
        assert claims.keys() == {"name", "slug", "status", "technology_generation"}
        # FK claim stores the parent's slug string, not the PK.
        assert claims["technology_generation"] == parent.slug

    def test_unknown_parent_slug_returns_404(self, client, user):
        client.force_login(user)
        resp = _post(
            client,
            "/api/technology-generations/does-not-exist/subgenerations/",
            {"name": "MPU", "slug": "mpu"},
        )
        assert resp.status_code == 404

    def test_deleted_parent_returns_404(self, client, user, parent):
        parent.status = "deleted"
        parent.save(update_fields=["status"])
        client.force_login(user)
        resp = _post(
            client,
            f"/api/technology-generations/{parent.slug}/subgenerations/",
            {"name": "MPU", "slug": "mpu"},
        )
        assert resp.status_code == 404


# ── Create: reward-types shares the same shape ──────────────────────


@pytest.mark.django_db
class TestRewardTypeCreate:
    def test_creates_reward_type(self, client, user):
        client.force_login(user)
        resp = _post(
            client,
            "/api/reward-types/",
            {"name": "Extra Ball", "slug": "extra-ball"},
        )
        assert resp.status_code == 201, resp.content
        assert RewardType.objects.get(slug="extra-ball").status == "active"


# ── Delete ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTagDelete:
    @pytest.fixture
    def tag(self, db):
        return Tag.objects.create(name="Widebody", slug="widebody", status="active")

    def test_preview_unblocked(self, client, user, tag):
        client.force_login(user)
        resp = client.get(f"/api/tags/{tag.slug}/delete-preview/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["slug"] == tag.slug
        assert body["blocked_by"] == []
        assert body["active_children_count"] == 0

    def test_delete_happy_path(self, client, user, tag):
        client.force_login(user)
        resp = _post(client, f"/api/tags/{tag.slug}/delete/", {})
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["affected_slugs"] == [tag.slug]

        tag.refresh_from_db()
        assert tag.status == "deleted"

        cs = ChangeSet.objects.get(pk=body["changeset_id"])
        assert cs.action == ChangeSetAction.DELETE


@pytest.mark.django_db
class TestTechGenDeleteBlockedByActiveChild:
    """Parents refuse to delete while they have active children.

    Response body must carry ``blocked_by: []`` (empty list, not missing) so
    the shared frontend classifier in delete-flow.ts treats the 422 as a
    ``blocked`` outcome rather than a generic form error.
    """

    @pytest.fixture
    def tech_gen(self, db):
        return TechnologyGeneration.objects.create(
            name="Solid State", slug="solid-state", status="active"
        )

    @pytest.fixture
    def subgen(self, db, tech_gen):
        return TechnologySubgeneration.objects.create(
            name="MPU",
            slug="mpu",
            status="active",
            technology_generation=tech_gen,
        )

    def test_preview_surfaces_child_count(self, client, user, tech_gen, subgen):
        client.force_login(user)
        resp = client.get(
            f"/api/technology-generations/{tech_gen.slug}/delete-preview/"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["active_children_count"] == 1
        # Blocked → provenance count short-circuits to zero.
        assert body["changeset_count"] == 0

    def test_delete_blocked_with_structured_body(self, client, user, tech_gen, subgen):
        client.force_login(user)
        resp = _post(client, f"/api/technology-generations/{tech_gen.slug}/delete/", {})
        assert resp.status_code == 422
        body = resp.json()
        assert body["blocked_by"] == []
        assert body["active_children_count"] == 1

        tech_gen.refresh_from_db()
        assert tech_gen.status == "active"

    def test_delete_proceeds_after_child_deleted(self, client, user, tech_gen, subgen):
        subgen.status = "deleted"
        subgen.save(update_fields=["status"])
        client.force_login(user)
        resp = _post(client, f"/api/technology-generations/{tech_gen.slug}/delete/", {})
        assert resp.status_code == 200, resp.content


@pytest.mark.django_db
class TestTechGenDeleteBlockedByProtectReferrer:
    """PROTECT referrer (an active MachineModel pointing at the tech-gen)
    must block with ``blocked_by`` populated by the generic walker."""

    def test_delete_blocked_by_protect_referrer(self, client, user, db):
        tech_gen = TechnologyGeneration.objects.create(
            name="Solid State", slug="solid-state", status="active"
        )
        title = Title.objects.create(
            name="Addams Family", slug="addams-family", status="active"
        )
        MachineModel.objects.create(
            name="Addams Family",
            slug="addams-family",
            title=title,
            status="active",
            technology_generation=tech_gen,
        )

        client.force_login(user)
        resp = _post(client, f"/api/technology-generations/{tech_gen.slug}/delete/", {})
        assert resp.status_code == 422
        body = resp.json()
        assert len(body["blocked_by"]) >= 1
        assert body["active_children_count"] == 0


# ── Restore ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTagRestore:
    def test_restores_deleted_tag(self, client, user):
        tag = Tag.objects.create(name="Widebody", slug="widebody", status="deleted")
        client.force_login(user)
        resp = _post(client, f"/api/tags/{tag.slug}/restore/", {})
        assert resp.status_code == 200, resp.content
        tag.refresh_from_db()
        assert tag.status == "active"

        cs = ChangeSet.objects.filter(user=user, action=ChangeSetAction.EDIT).latest(
            "pk"
        )
        fields = set(
            Claim.objects.filter(changeset=cs).values_list("field_name", flat=True)
        )
        assert fields == {"status"}

    def test_restore_rejects_active(self, client, user):
        Tag.objects.create(name="Widebody", slug="widebody", status="active")
        client.force_login(user)
        resp = _post(client, "/api/tags/widebody/restore/", {})
        assert resp.status_code == 422


@pytest.mark.django_db
class TestSubgenRestoreRequiresActiveParent:
    def test_blocked_when_parent_deleted(self, client, user, db):
        parent = TechnologyGeneration.objects.create(
            name="Solid State", slug="solid-state", status="deleted"
        )
        sub = TechnologySubgeneration.objects.create(
            name="MPU", slug="mpu", status="deleted", technology_generation=parent
        )
        client.force_login(user)
        resp = _post(client, f"/api/technology-subgenerations/{sub.slug}/restore/", {})
        assert resp.status_code == 422
        # Loose match — the exact wording can drift; the contract is that the
        # body surfaces the parent's name so the UI can prompt for that first.
        assert parent.name in resp.json()["detail"]

        sub.refresh_from_db()
        assert sub.status == "deleted"

    def test_succeeds_when_parent_active(self, client, user, db):
        parent = TechnologyGeneration.objects.create(
            name="Solid State", slug="solid-state", status="active"
        )
        sub = TechnologySubgeneration.objects.create(
            name="MPU", slug="mpu", status="deleted", technology_generation=parent
        )
        client.force_login(user)
        resp = _post(client, f"/api/technology-subgenerations/{sub.slug}/restore/", {})
        assert resp.status_code == 200, resp.content


# ── Display-subtype mirrors subgeneration ───────────────────────────


@pytest.mark.django_db
class TestDisplaySubtypeCreate:
    def test_nested_route_and_fk_claim(self, client, user, db):
        parent = DisplayType.objects.create(name="LCD", slug="lcd", status="active")
        client.force_login(user)
        resp = _post(
            client,
            f"/api/display-types/{parent.slug}/subtypes/",
            {"name": "HD LCD", "slug": "hd-lcd"},
        )
        assert resp.status_code == 201, resp.content
        assert DisplaySubtype.objects.get(slug="hd-lcd").display_type_id == parent.pk


@pytest.mark.django_db
class TestDisplaySubtypeRestoreRequiresActiveParent:
    """Symmetry with subgeneration — same code path, wired via a different
    ``parent_field`` kwarg on the registration. Covered so that a future
    edit to the display-subtype registration can't silently drop the
    deleted-parent check."""

    def test_blocked_when_parent_deleted(self, client, user, db):
        parent = DisplayType.objects.create(name="LCD", slug="lcd", status="deleted")
        sub = DisplaySubtype.objects.create(
            name="HD LCD", slug="hd-lcd", status="deleted", display_type=parent
        )
        client.force_login(user)
        resp = _post(client, f"/api/display-subtypes/{sub.slug}/restore/", {})
        assert resp.status_code == 422
        assert parent.name in resp.json()["detail"]

        sub.refresh_from_db()
        assert sub.status == "deleted"


# ── Delete-preview carries parent breadcrumb on parented entities ────


@pytest.mark.django_db
class TestParentedDeletePreviewBreadcrumb:
    """Preview must surface ``parent_name``/``parent_slug`` for subgen and
    subtype so the delete confirmation UI can render the breadcrumb without
    a second round-trip. Parentless entities return null for both."""

    def test_subgeneration_preview_includes_parent(self, client, user, db):
        parent = TechnologyGeneration.objects.create(
            name="Solid State", slug="solid-state", status="active"
        )
        sub = TechnologySubgeneration.objects.create(
            name="MPU", slug="mpu", status="active", technology_generation=parent
        )
        client.force_login(user)
        resp = client.get(f"/api/technology-subgenerations/{sub.slug}/delete-preview/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["parent_name"] == parent.name
        assert body["parent_slug"] == parent.slug

    def test_parentless_preview_has_null_parent(self, client, user, db):
        tag = Tag.objects.create(name="Widebody", slug="widebody", status="active")
        client.force_login(user)
        resp = client.get(f"/api/tags/{tag.slug}/delete-preview/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["parent_name"] is None
        assert body["parent_slug"] is None


# ── Delete blocked by active M2M referrer ────────────────────────────


def _title_with_model(slug: str) -> tuple[Title, MachineModel]:
    title = Title.objects.create(name=slug.title(), slug=slug, status="active")
    mm = MachineModel.objects.create(
        name=slug.title(), slug=f"{slug}-pro", title=title, status="active"
    )
    return title, mm


@pytest.mark.django_db
class TestTagDeleteBlockedByActiveMachineModel:
    """Active MachineModel applying a Tag via ``MachineModelTag`` must block
    Tag delete. The through-table has no lifecycle of its own, so the
    walker reaches the referrer through ``soft_delete_usage_blockers``."""

    def test_preview_surfaces_blocker(self, client, user):
        tag = Tag.objects.create(name="Widebody", slug="widebody", status="active")
        _, mm = _title_with_model("mm")
        mm.tags.add(tag)

        client.force_login(user)
        resp = client.get(f"/api/tags/{tag.slug}/delete-preview/")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["blocked_by"]) == 1
        assert body["blocked_by"][0]["entity_type"] == "model"
        assert body["changeset_count"] == 0  # short-circuited while blocked

    def test_delete_returns_422_blocked_body(self, client, user):
        tag = Tag.objects.create(name="Widebody", slug="widebody", status="active")
        _, mm = _title_with_model("mm")
        mm.tags.add(tag)

        client.force_login(user)
        resp = _post(client, f"/api/tags/{tag.slug}/delete/", {})
        assert resp.status_code == 422
        body = resp.json()
        assert len(body["blocked_by"]) == 1
        tag.refresh_from_db()
        assert tag.status == "active"

    def test_delete_proceeds_when_referrer_soft_deleted(self, client, user):
        tag = Tag.objects.create(name="Widebody", slug="widebody", status="active")
        _, mm = _title_with_model("mm")
        mm.tags.add(tag)
        mm.status = "deleted"
        mm.save(update_fields=["status"])

        client.force_login(user)
        resp = _post(client, f"/api/tags/{tag.slug}/delete/", {})
        assert resp.status_code == 200, resp.content


@pytest.mark.django_db
class TestRewardTypeDeleteBlockedByActiveMachineModel:
    def test_delete_returns_422_blocked_body(self, client, user):
        rt = RewardType.objects.create(
            name="Extra Ball", slug="extra-ball", status="active"
        )
        _, mm = _title_with_model("mm")
        mm.reward_types.add(rt)

        client.force_login(user)
        resp = _post(client, f"/api/reward-types/{rt.slug}/delete/", {})
        assert resp.status_code == 422
        body = resp.json()
        assert len(body["blocked_by"]) == 1
        rt.refresh_from_db()
        assert rt.status == "active"


# ── Alias-collision on create ───────────────────────────────────────


@pytest.mark.django_db
class TestRewardTypeCreateAliasCollision:
    """Per RecordCreateDelete.md, aliases must count as results for duplicate
    prevention — the API must reject a create whose name collides with an
    existing alias, not just with another entity's canonical name."""

    def test_create_rejects_name_matching_existing_alias(self, client, user):
        existing = RewardType.objects.create(
            name="Extra Ball", slug="extra-ball", status="active"
        )
        RewardTypeAlias.objects.create(reward_type=existing, value="Shoot Again")

        client.force_login(user)
        resp = _post(
            client,
            "/api/reward-types/",
            {"name": "Shoot Again", "slug": "shoot-again"},
        )
        assert resp.status_code == 422
        assert "name" in resp.json()["detail"]["field_errors"]
        assert not RewardType.objects.filter(slug="shoot-again").exists()
