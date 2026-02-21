# IPDB ManufacturerIds to skip during ingestion.
# 0 = no manufacturer assigned, 328 = "Unknown Manufacturer" placeholder.
IPDB_SKIP_MANUFACTURER_IDS: frozenset[int] = frozenset({0, 328})
