import asyncio
import json
import os
import sys
from pathlib import Path
import sacrebleu
from tabulate import tabulate

from dotenv import load_dotenv

# Add the backend dir to sys.path so we can import the app
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

load_dotenv()
from app.services.translation.deepl_provider import DeepLProvider
from app.services.translation.gemini_provider import GeminiProvider

DATA_PATH = Path(__file__).parent / "data" / "rotpunkt_eval.json"

async def run_eval(provider_name: str, provider, dataset: list[dict]):
    print(f"\nRunning eval for {provider_name}...")
    
    # Tracking metrics
    results = []
    glossary_hits = 0
    glossary_total = 0
    dnt_hits = 0
    dnt_total = 0
    
    # Group dataset by language pair
    from collections import defaultdict
    batches_by_lang = defaultdict(list)
    for item in dataset:
        src = item.get("source_lang", "de")
        tgt = item.get("target_lang", "en")
        batches_by_lang[(src, tgt)].append(item)
        
    for (src, tgt), items in batches_by_lang.items():
        batch_size = 20
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            texts_source = [item["source_text"] for item in batch]
            
            # Build the combined glossary for this batch
            combined_glossary = {}
            for item in batch:
                combined_glossary.update(item.get("required_glossary", {}))
                for dnt in item.get("do_not_translate", []):
                    combined_glossary[dnt] = dnt
                    
            try:
                translations = await provider.translate(
                    texts_source, src, tgt, glossary=combined_glossary
                )
            except Exception as e:
                print(f"Error during {provider_name} translation for {src}->{tgt}: {e}")
                translations = [""] * len(batch)

            for item, trans in zip(batch, translations, strict=True):
                # 1. Glossary Adherence
                for source_term, tgt_term in item.get("required_glossary", {}).items():
                    glossary_total += 1
                    if tgt_term.lower() in trans.lower():
                        glossary_hits += 1
                        
                # 2. DNT Adherence
                for dnt in item.get("do_not_translate", []):
                    dnt_total += 1
                    if dnt in trans:
                        dnt_hits += 1

                results.append({
                    "id": item["id"],
                    "source": item["source_text"],
                    "ground_truth": item["ground_truth"],
                    "output": trans,
                    "category": item["category"]
                })
            
    # Calculate chrF and BLEU over the whole corpus
    refs = [[r["ground_truth"] for r in results]]
    sys = [r["output"] for r in results]
    
    chrf = sacrebleu.corpus_chrf(sys, refs)
    bleu = sacrebleu.corpus_bleu(sys, refs)
    
    glos_score = (glossary_hits / glossary_total * 100) if glossary_total > 0 else 100
    dnt_score = (dnt_hits / dnt_total * 100) if dnt_total > 0 else 100
    
    return {
        "Provider": provider_name,
        "chrF Score": round(chrf.score, 2),
        "BLEU Score": round(bleu.score, 2),
        "Glossary Adherence (%)": f"{round(glos_score, 1)}% ({glossary_hits}/{glossary_total})",
        "DNT Adherence (%)": f"{round(dnt_score, 1)}% ({dnt_hits}/{dnt_total})",
    }


async def main():
    if not DATA_PATH.exists():
        print(f"Dataset not found at {DATA_PATH}")
        return
        
    dataset = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(dataset)} evaluation strings.")
    
    providers_to_test = {}
    
    deepl_key = os.getenv("DEEPL_API_KEY")
    if deepl_key:
        providers_to_test["DeepL"] = DeepLProvider(api_key=deepl_key)
        
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        providers_to_test["Gemini (3.5 Flash Lite)"] = GeminiProvider(api_key=gemini_key)
        
    if not providers_to_test:
        print("No API keys found in .env. Skipping evaluation.")
        return
        
    summary = []
    for name, provider in providers_to_test.items():
        metrics = await run_eval(name, provider, dataset)
        summary.append(metrics)
        
    print("\n" + "="*80)
    print(" ROTPUNKT TRANSLATION EVALUATION REPORT ".center(80))
    print("="*80 + "\n")
    print(tabulate(summary, headers="keys", tablefmt="github"))
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(main())
