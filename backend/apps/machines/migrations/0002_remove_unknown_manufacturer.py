"""Remove the "Unknown Manufacturer" placeholder.

IPDB ManufacturerId=328 is a placeholder meaning "manufacturer unknown."
It was ingested as a real manufacturer, giving it 296 machines. This
migration nulls out the FK on those machines, deletes the entity, and
deletes the manufacturer.
"""

from django.db import migrations


def remove_unknown_manufacturer(apps, schema_editor):
    Claim = apps.get_model("machines", "Claim")
    ManufacturerEntity = apps.get_model("machines", "ManufacturerEntity")
    PinballModel = apps.get_model("machines", "PinballModel")

    entity = ManufacturerEntity.objects.filter(ipdb_manufacturer_id=328).first()
    if not entity:
        return

    mfr = entity.manufacturer

    # Null out FK only on machines assigned via the placeholder claim (value=328),
    # not all machines on the manufacturer (which may have other valid entities).
    placeholder_model_ids = list(
        Claim.objects.filter(
            field_name="manufacturer", value=328, is_active=True
        ).values_list("model_id", flat=True)
    )
    PinballModel.objects.filter(id__in=placeholder_model_ids).update(manufacturer=None)

    # Delete only the placeholder entity.
    entity.delete()

    # Delete the manufacturer only if nothing still references it.
    has_entities = ManufacturerEntity.objects.filter(manufacturer=mfr).exists()
    has_models = PinballModel.objects.filter(manufacturer=mfr).exists()
    if not has_entities and not has_models:
        mfr.delete()


def restore_unknown_manufacturer(apps, schema_editor):
    # Not worth restoring; re-running ingest_manufacturers would recreate it
    # if the skip list were reverted.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("machines", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            remove_unknown_manufacturer,
            restore_unknown_manufacturer,
        ),
    ]
