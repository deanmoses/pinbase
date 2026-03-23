"""DB-driven vocabulary maps for feature/reward-type/tag/cabinet classification.

These maps are built from the live database and shared by the IPDB and OPDB
ingest commands.  All keys are lowercased for case-insensitive lookup.
"""

from __future__ import annotations


def build_feature_slug_map() -> dict[str, str]:
    """Return {lowercase_term: slug} from GameplayFeature names + aliases."""
    from apps.catalog.models import GameplayFeature, GameplayFeatureAlias

    result: dict[str, str] = {}
    for slug, name in GameplayFeature.objects.values_list("slug", "name"):
        result[name.lower()] = slug
    for slug, value in GameplayFeatureAlias.objects.select_related(
        "feature"
    ).values_list("feature__slug", "value"):
        result[value.lower()] = slug
    return result


def build_reward_type_map() -> dict[str, str]:
    """Return {lowercase_term: slug} from RewardType names + aliases."""
    from apps.catalog.models import RewardType, RewardTypeAlias

    result: dict[str, str] = {}
    for slug, name in RewardType.objects.values_list("slug", "name"):
        result[name.lower()] = slug
    for slug, value in RewardTypeAlias.objects.select_related(
        "reward_type"
    ).values_list("reward_type__slug", "value"):
        result[value.lower()] = slug
    return result


def build_tag_map() -> dict[str, str]:
    """Return {lowercase_term: slug} from Tag names."""
    from apps.catalog.models import Tag

    return {
        name.lower(): slug for slug, name in Tag.objects.values_list("slug", "name")
    }


def build_cabinet_map() -> dict[str, str]:
    """Return {lowercase_term: slug} from Cabinet names."""
    from apps.catalog.models import Cabinet

    return {
        name.lower(): slug for slug, name in Cabinet.objects.values_list("slug", "name")
    }
