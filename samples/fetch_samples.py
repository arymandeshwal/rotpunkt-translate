"""Download the public Rotpunkt sample documents listed in SOURCES.md into samples/downloads/."""

import urllib.request
from pathlib import Path

BASE = "https://www.rotpunktkuechen.de/fileadmin/30_Downloads/"
FILES = [
    "10_Kuechencheckliste/Checkliste_Rotpunkt_Kuechen_DE.pdf",
    "10_Kuechencheckliste/Checkliste_Rotpunkt_Kuechen_EN.pdf",
    "10_Kuechencheckliste/Checkliste_Rotpunkt_Kuechen_FR.pdf",
    "10_Kuechencheckliste/Checkliste_Rotpunkt_Kuechen_NL.pdf",
    "02_Flyer/HPL_XTreme.pdf",
    "02_Flyer/230315_RP_Flyer_Drawer_Solutions_148x210_AB_RZ_Ansicht.pdf",
    "01_Kataloge/less_is_more-2023.pdf",
]

target = Path(__file__).parent / "downloads"
target.mkdir(exist_ok=True)

for path in FILES:
    dest = target / Path(path).name
    if dest.exists():
        print(f"skip  {dest.name}")
        continue
    print(f"fetch {dest.name}")
    urllib.request.urlretrieve(BASE + path, dest)
