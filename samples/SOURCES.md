# Sample documents

Real-world reference documents from [rotpunktkuechen.de/downloads](https://www.rotpunktkuechen.de/downloads).
They are © Rotpunkt Küchen GmbH and are **not** committed to this repository.
Run `python samples/fetch_samples.py` to download them into `samples/downloads/` (gitignored).

Rotpunkt only publishes PDFs, which is why Part 1 ingests PDF. Committed test fixtures are
synthetic PDFs that mirror the structure and vocabulary of these documents
(see `backend/tests/fixtures/`); the real files are used for local, manual testing.

| File | Languages | Why it is useful |
|---|---|---|
| Checkliste_Rotpunkt_Kuechen_{DE,EN,FR,NL}.pdf | 4 parallel files | Kitchen planning checklist; aligned term pairs (units, appliances, fronts) |
| HPL_XTreme.pdf | DE/EN/NL/FR in one file | Care instructions; technical prose with product names |
| Drawer Solutions flyer | DE/EN/FR side by side | Short marketing text with an article ID (`ID-No. 21103380`) |
| less_is_more-2023.pdf | DE/EN/FR/ES | Catalogue with front/colour names that must not be translated |

## Seed terminology

Term pairs taken from the parallel DE/EN checklists, used to seed the development glossary:

| DE | EN |
|---|---|
| Korpus | carcase |
| Front | front |
| Arbeitsplatte | worktop |
| Schubkasten | drawer |
| Auszug | pull-out |
| grifflos | handleless |
| Hochschrank | tall unit |
| Unterschrank | base unit |
| Spülunterschrank | sink base unit |
| Eckschrank | corner unit |
| Apothekerhochschrank | tall apothecary unit |
| Besteckschublade | cutlery drawer |
| Nischenverkleidung | recess panelling |
| Kochfeld | hob |
| Dunstabzugshaube | extractor hood |
| Umluft / Abluft | recirculation / exhaust |
| Geschirrspülmaschine | dishwasher |
| Abtropffläche | draining board |
| Hochdruckschichtstoff (HPL) | high-pressure laminate |
| Pflegehinweise | care instructions |

Protected names (never translated): Zerox HPL XT, Zerox FX, Class VM, Memory RI, XTreme,
FENIX, Drawer Solutions, WALL SOLUTIONS, Greenline, colour names such as Clay Dark,
Beach Grey, Loft Nature Oak.
