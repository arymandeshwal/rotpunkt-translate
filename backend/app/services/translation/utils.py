def filter_relevant_glossary(texts: list[str], glossary: dict[str, str] | None) -> dict[str, str]:
    """
    Scans a list of texts and returns only the glossary terms that actually appear in them.
    This saves LLM token costs and prevents the model from being confused by irrelevant terms.
    
    The match is strictly case-sensitive for the MVP.
    
    Args:
        texts: A list of strings that are about to be translated.
        glossary: A dictionary mapping source terms to target terms.
        
    Returns:
        A smaller dictionary containing only the glossary terms present in the texts.
    """
    if not glossary:
        return {}
        
    relevant = {}
    # Combine texts to do a single efficient pass for each term
    combined_text = " ".join(texts)
    
    for source_term, target_term in glossary.items():
        if source_term in combined_text:
            relevant[source_term] = target_term
            
    return relevant
