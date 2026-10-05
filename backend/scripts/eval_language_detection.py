import json
from dataclasses import dataclass

from app.services.language_detection import is_translatable

@dataclass
class EvalExample:
    text: str
    expected_to_translate: bool
    description: str

DATASET = [
    # --- PURE GERMAN (Must Translate) - 30 items ---
    EvalExample("Küche", True, "German word"),
    EvalExample("Arbeitsplatte", True, "German word"),
    EvalExample("Spüle", True, "German word"),
    EvalExample("Mülltrennsystem", True, "German word"),
    EvalExample("Scharnier", True, "German word"),
    EvalExample("Griffleiste", True, "German word"),
    EvalExample("Sockel", True, "German word"),
    EvalExample("Korpus", True, "German word"),
    EvalExample("Fronten", True, "German word"),
    EvalExample("Furnier", True, "German word"),
    EvalExample("Massivholz", True, "German word"),
    EvalExample("Kunststoff", True, "German word"),
    EvalExample("Montageanleitung", True, "German word"),
    EvalExample("Wandbefestigung", True, "German word"),
    EvalExample("Zulässiges Gesamtgewicht", True, "German phrase"),
    EvalExample("Lieferumfang", True, "German word"),
    EvalExample("Zubehör", True, "German word"),
    EvalExample("Achtung! Lebensgefahr bei unsachgemäßer Montage.", True, "German warning"),
    EvalExample("Bitte lesen Sie diese Anleitung sorgfältig durch.", True, "German sentence"),
    EvalExample("Pflegehinweise für Hochglanzfronten", True, "German phrase"),
    EvalExample("Schubkasten mit Vollauszug", True, "German phrase"),
    EvalExample("Einlegeboden höhenverstellbar", True, "German phrase"),
    EvalExample("Dämpfungssystem integriert", True, "German phrase"),
    EvalExample("Nischenverkleidung", True, "German word"),
    EvalExample("Hängeschrank", True, "German word"),
    EvalExample("Unterschrank", True, "German word"),
    EvalExample("Eckschrank", True, "German word"),
    EvalExample("Spülenunterschrank", True, "German word"),
    EvalExample("Geräteumbauschrank", True, "German word"),
    EvalExample("Rotpunkt Küchen GmbH", True, "Company Name / German"),

    # --- MIXED / MULTILINGUAL (Must Translate) - 20 items ---
    EvalExample("Arbeitsplatte / Worktop", True, "Mixed DE/EN"),
    EvalExample("Spüle - Sink", True, "Mixed DE/EN"),
    EvalExample("Montageanleitung (Assembly instructions)", True, "Mixed DE/EN"),
    EvalExample("Korpus / Carcase / Caisson", True, "Mixed DE/EN/FR"),
    EvalExample("Sockelhöhe | Plinth height", True, "Mixed DE/EN"),
    EvalExample("Frontausführung: Lack / Lacquer", True, "Mixed DE/EN"),
    EvalExample("Grifflos / Handleless", True, "Mixed DE/EN"),
    EvalExample("Eiche natur / Natural oak", True, "Mixed DE/EN"),
    EvalExample("Auszug / Pull-out / Tiroir", True, "Mixed DE/EN/FR"),
    EvalExample("Achtung / Warning / Attention", True, "Mixed DE/EN/FR"),
    EvalExample("Breite Width Largeur", True, "Mixed DE/EN/FR"),
    EvalExample("Tiefe Depth Profondeur", True, "Mixed DE/EN/FR"),
    EvalExample("Höhe Height Hauteur", True, "Mixed DE/EN/FR"),
    EvalExample("Art.-Nr. / Item no. / Réf.", True, "Mixed DE/EN/FR"),
    EvalExample("Farbe/Colour:", True, "Mixed DE/EN"),
    EvalExample("DE / EN / FR", True, "Language codes"),
    EvalExample("Maße (Dimensions)", True, "Mixed DE/EN"),
    EvalExample("Gewicht / Weight: 25 kg", True, "Mixed DE/EN + Number"),
    EvalExample("Inklusive / Included", True, "Mixed DE/EN"),
    EvalExample("Designlinie / Design line", True, "Mixed DE/EN"),

    # --- CODES, NUMBERS, SYMBOLS (Must Translate) - 15 items ---
    EvalExample("19 mm", True, "Measurement"),
    EvalExample("120 x 60 cm", True, "Dimensions"),
    EvalExample("U100", True, "Article Code"),
    EvalExample("HS60-2", True, "Article Code"),
    EvalExample("GSP 60", True, "Article Code"),
    EvalExample("12345", True, "Number"),
    EvalExample("€ 1.999,00", True, "Price"),
    EvalExample("A+", True, "Energy Label"),
    EvalExample("X", True, "Single char"),
    EvalExample("2026-10-05", True, "Date"),
    EvalExample("1.", True, "List item number"),
    EvalExample("a)", True, "List item letter"),
    EvalExample("-", True, "Dash/Symbol"),
    EvalExample("L", True, "Single char"),
    EvalExample("15 kg", True, "Measurement"),

    # --- PURE FOREIGN (Must Skip) - 35 items ---
    EvalExample("Kitchen", False, "English word"),
    EvalExample("Worktop", False, "English word"),
    EvalExample("Sink", False, "English word"),
    EvalExample("Waste bin", False, "English word"),
    EvalExample("Hinge", False, "English word"),
    EvalExample("Handleless", False, "English word"),
    EvalExample("Plinth", False, "English word"),
    EvalExample("Carcase", False, "English word"),
    EvalExample("Fronts", False, "English word"),
    EvalExample("Assembly instructions", False, "English phrase"),
    EvalExample("Warning! Risk of fatal injury if incorrectly installed.", False, "English warning"),
    EvalExample("Please read these instructions carefully.", False, "English sentence"),
    EvalExample("Care instructions for high-gloss fronts", False, "English phrase"),
    EvalExample("Fully extending drawer", False, "English phrase"),
    EvalExample("Height-adjustable shelf", False, "English phrase"),
    EvalExample("Integrated soft-closing system", False, "English phrase"),
    EvalExample("Wall unit", False, "English word"),
    EvalExample("Base unit", False, "English word"),
    EvalExample("Corner unit", False, "English word"),
    EvalExample("Appliance housing", False, "English word"),
    EvalExample("Cuisine", False, "French word"),
    EvalExample("Plan de travail", False, "French word"),
    EvalExample("Évier", False, "French word"),
    EvalExample("Charnière", False, "French word"),
    EvalExample("Sans poignée", False, "French phrase"),
    EvalExample("Socle", False, "French word"),
    EvalExample("Caisson", False, "French word"),
    EvalExample("Façades", False, "French word"),
    EvalExample("Instructions de montage", False, "French phrase"),
    EvalExample("Attention ! Danger de mort en cas de montage incorrect.", False, "French warning"),
    EvalExample("Veuillez lire attentivement ces instructions.", False, "French sentence"),
    EvalExample("Keuken", False, "Dutch word"),
    EvalExample("Werkblad", False, "Dutch word"),
    EvalExample("Montagehandleiding", False, "Dutch phrase"),
    EvalExample("Lees deze handleiding zorgvuldig door.", False, "Dutch sentence"),
]

def main():
    print(f"Running language detection evaluation on {len(DATASET)} realistic examples...\n")
    
    tp = tn = fp = fn = 0
    errors = []
    
    for ex in DATASET:
        # Use our actual implemented logic!
        will_translate = is_translatable(ex.text, "de")
        
        if will_translate and ex.expected_to_translate:
            tp += 1
        elif not will_translate and not ex.expected_to_translate:
            tn += 1
        elif will_translate and not ex.expected_to_translate:
            fp += 1 # Wasted quota
            errors.append(f"FP (Wasted Quota): '{ex.text}' -> Sent, but should skip ({ex.description})")
        elif not will_translate and ex.expected_to_translate:
            fn += 1 # Fatal error (lost text)
            errors.append(f"FN (Lost Text): '{ex.text}' -> Skipped, but should translate! ({ex.description})")

    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    
    print(f"Total Evaluated: {len(DATASET)}")
    print(f"True Positives (Correctly Translated): {tp}")
    print(f"True Negatives (Correctly Skipped):    {tn}")
    print(f"False Positives (Wasted Quota):        {fp}")
    print(f"False Negatives (Fatal Text Loss):     {fn}\n")
    
    print(f"Recall (Did we catch all German?): {recall * 100:.1f}%")
    print(f"Precision (How strict was the filter?): {precision * 100:.1f}%\n")
    
    print("--- Detailed Errors ---")
    for err in errors:
        print(err)

if __name__ == "__main__":
    main()
