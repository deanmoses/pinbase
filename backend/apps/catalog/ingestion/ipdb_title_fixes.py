"""Manual corrections for IPDB titles.

Two categories:
1. Encoding damage (U+FFFD) — the IPDB export lost trademark symbols,
   accented characters, and apostrophes.
2. Spurious wrapping quotes — IPDB wrapped some titles in double quotes
   that aren't part of the actual game name.

Applied during IPDB ingestion before claiming the title.
"""

# ipdb_id → corrected title
TITLE_FIXES: dict[int, str] = {
    # --- Quote corrections (high confidence) ---
    1718: "1 2 3",
    2105: "7-11",
    4687: "Trio",
    5858: "Lucky Boy",
    6174: "Le Paris",
    6886: "IT",
    # --- Encoding corrections ---
    180: "Barrel O' Fun",
    181: "Barrel O' Fun '61",
    182: "Barrel O' Fun '62",
    3120: "Glamor-Girls",
    4130: "PIN*BOT",
    4470: "Sérénade",
    4489: "Wizard Blocks!",
    4615: "Six-Star",
    4891: "Wonder Wizard Demolition Derby",
    4936: "Imo Nürburg",
    4967: "Sub-Marine",
    5065: "Home Run '44",
    5247: "1·2·3...",
    5260: "Les Flèches",
    5423: "Unknown ('Four Crowns')",
    5482: "Ametrallador Atomico 1ª",
    5642: "Wonder Wizard CB Charlie",
    5738: "S. João",
    5754: "Transformers Autobot Crimson Limited Edition",
    5755: "Transformers Decepticon Violet Limited Edition",
    5810: "Gran Dominó",
    5827: "Ol' South",
    5881: "Competición",
    5934: "1ª División",
    5978: "'Rodello'",
    6011: "4-IN-1 (Willy's Cup)",
    6032: "Elvis Gold (Limited Edition)",
    6147: "Les Étoiles",
    6186: "Pinball Roulette",
    6187: "Pinball Roulette (Gold Panther)",
    6188: "Pinball Roulette (Silver Panther)",
    6189: "Panther Roulette",
    6190: "Panther Roulette II",
    6200: "Competición Penalty",
    6218: "Millón",
    6352: "Dialed In! (Collector's Edition)",
    6373: "Avengers The Pin",
    6517: "Feitiço",
    6586: "Domino's Spectacular Pinball Adventure (Limited Edition)",
    6735: "Ametrallador Atomico 1ª",
    6794: "Constelación",
    6832: "Bride of Pin*bot 25th Anniversary",
    6833: "The Big Lebowski Pinball (Second Model)",
    6911: '"Corinthian" 22',
}
