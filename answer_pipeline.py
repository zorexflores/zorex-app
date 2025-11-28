# answer_pipeline.py — Narrative Summary Engine v3.0
# Creates coherent, story-driven product summaries

import re
import os
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

# ----------------------------- Fuzzy Matching (keep as-is) -----------------------------

def fuzz_ratio(s1: str, s2: str) -> int:
    return int(SequenceMatcher(None, s1.lower(), s2.lower()).ratio() * 100)

def fuzz_partial_ratio(s1: str, s2: str) -> int:
    s1, s2 = s1.lower(), s2.lower()
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    if not s1:
        return 0
    max_ratio = 0
    for i in range(len(s2) - len(s1) + 1):
        substr = s2[i:i+len(s1)]
        ratio = fuzz_ratio(s1, substr)
        max_ratio = max(max_ratio, ratio)
    return max_ratio

def process_extract(query: str, choices: List[str], limit: int = 5) -> List[Tuple[str, int]]:
    if not choices:
        return []
    scored = []
    for choice in choices:
        score = fuzz_partial_ratio(query, choice)
        scored.append((choice, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]

# ----------------------------- Config Loading -----------------------------

def _load_yaml_file(filepath: str) -> dict:
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        import yaml
        return yaml.safe_load(f)

def _init_data():
    global BENEFITS_DATA, INGREDIENTS_DATA
    benefits_path = os.path.join('config', 'benefits.yml')
    BENEFITS_DATA = _load_yaml_file(benefits_path)
    ingredients_path = os.path.join('config', 'ingredients.yml')
    ing_config = _load_yaml_file(ingredients_path)
    INGREDIENTS_DATA = []
    if ing_config and 'ingredients' in ing_config:
        for category_data in ing_config['ingredients'].values():
            if isinstance(category_data, dict) and 'items' in category_data:
                INGREDIENTS_DATA.extend(category_data['items'])

BENEFITS_DATA = {}
INGREDIENTS_DATA = []
_init_data()

# ----------------------------- Text Processing -----------------------------

def _clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r"The U\.S\. Food and Drug Administration.*", "", text, flags=re.I | re.DOTALL)
    return text.strip()

def _split_sentences(text: str) -> List[str]:
    text = _clean_text(text)
    abbrevs = ['Dr', 'Mr', 'Mrs', 'Ms', 'Ph', 'B', 'D', 'O', 'U', 'S', 'vs', 'etc', 'i.e', 'e.g']
    for abbrev in abbrevs:
        text = re.sub(rf'\b{abbrev}\.', f'{abbrev}<PERIOD>', text, flags=re.IGNORECASE)
    sentences = re.split(r'[.!?]+', text)
    result = []
    for sent in sentences:
        sent = sent.replace('<PERIOD>', '.').strip()
        if len(sent) > 20 and len(sent.split()) >= 3:
            result.append(sent)
    return result

def _detect_format(text: str) -> str:
    text_lower = text.lower()
    if 'clinical guide' in text_lower or 'clinical applications:' in text_lower:
        return 'clinical_guide'
    elif 'newsletter' in text_lower or 'better health news' in text_lower:
        return 'newsletter'
    else:
        return 'product_sheet'

# ----------------------------- NARRATIVE EXTRACTION -----------------------------

def _extract_primary_purpose(text: str) -> Optional[str]:
    """What does this product do?"""
    
    # Pattern 1: delivers X through
    delivers_match = re.search(r"delivers\s+([\w\s]+?)\s+(?:through|via)", text, re.IGNORECASE)
    if delivers_match:
        return delivers_match.group(1).strip()
    
    # Pattern 2: provides X for/through
    provides_match = re.search(r"provides?\s+([\w\s]+?)\s+(?:for|through|via)", text, re.IGNORECASE)
    if provides_match:
        return provides_match.group(1).strip()
    
    # Pattern 3: Clinical applications
    app_match = re.search(r"clinical applications?:(.*?)(?:\n\n|\Z)", text, re.IGNORECASE | re.DOTALL)
    if app_match:
        apps_text = app_match.group(1)
        bullets = re.findall(r'[•\-]\s*(.+?)(?:\n|$)', apps_text)
        if bullets:
            if len(bullets) >= 2:
                return f"{bullets[0].strip()} and {bullets[1].strip()}"
            return bullets[0].strip()
    
    return None

def _extract_key_mechanism(text: str) -> Optional[str]:
    """Find the most specific mechanism sentence"""
    
    text_normalized = re.sub(r'\s+', ' ', text)
    sentences = re.split(r'[.!?]+', text_normalized)
    scored = []
    
    for sent in sentences:
        sent = sent.strip()
        if len(sent.split()) < 8:
            continue
        
        # Clean headers
        sent_clean = re.sub(r'^(?:[A-Z][a-z]+\s+){1,4}(?=[a-z])', '', sent)
        sent_clean = re.sub(r'^.*?\s+The\s+', 'The ', sent_clean)
        
        # Capitalize if lowercase after cleaning
        if sent_clean and sent_clean[0].islower():
            sent_clean = sent_clean[0].upper() + sent_clean[1:]
        
        sent_lower = sent_clean.lower()
        score = 0
        
        # KILL SHOTS
        if any(bad in sent_lower for bad in ['this product is not intended', 'not intended to diagnose', 'food and drug administration', 'product specifications', 'formulation details', 'dosing protocols', 'dosing protocol', 'clinical guide', 'product profile']):
            continue
        
        # HIGHEST value
        if 'serving as' in sent_lower and 'filter' in sent_lower:
            score += 5
        elif 'serving as' in sent_lower or ('filter' in sent_lower and 'blue' in sent_lower):
            score += 4
        
        # High value: EXPANDED action verbs
        if any(word in sent_lower for word in ['accumulate', 'block', 'prevent', 'protect', 'reduce', 'inhibit', 'modulate', 'addresses']):
            score += 3
        
        # Medium value: biological terms
        if any(word in sent_lower for word in ['cellular', 'mitochondrial', 'oxidative', 'retinal', 'macular', 'fovea', 'pigment', 'neurotransmitter', 'enzyme', 'proteolytic', 'inflammatory', 'adrenal', 'hpa', 'axis', 'pituitary', 'hypothalamus', 'glandular']):
            score += 2
        
        # Low value: general actions
        if any(word in sent_lower for word in ['support', 'maintain', 'improve', 'enhance', 'provide']):
            score += 1
        
        # PENALTIES
        if any(bad in sent_lower for bad in ['comprehensive', 'professional', 'advanced formulation']):
            score -= 2
        
        if sent_lower.count(':') >= 2 or sent_lower.count(',') >= 5:
            score -= 3
        
        if not sent_clean[0].isupper():
            continue
        
        if score > 1:
            scored.append((score, sent_clean))
    
    if scored:
        scored.sort(reverse=True, key=lambda x: x[0])
        return scored[0][1]
    
    return None

def _extract_unique_value(text: str) -> Optional[str]:
    """What makes this product special?"""
    text_lower = text.lower()
    
    # Look for comparative statements
    unique_patterns = [
        r"(superior [\w\s]+ compared to [\w\s%]+)",
        r"(99% pure [\w]+ compared to [\d]+% [\w\s]+)",
        r"(only [\w\s]+ formula (?:that|to) [\w\s,]{15,80})",
        r"(sets [\w\s]+ apart[^.]{10,80})",
        r"(most (?:effective|potent|bioavailable) [\w\s]{10,60})",
    ]
    
    for pattern in unique_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            unique = match.group(1).strip()
            unique = re.sub(r'\s+', ' ', unique)
            if unique:
                unique = unique[0].upper() + unique[1:]
            return unique
    
    return None

def _extract_usage_guidance(text: str) -> Dict[str, str]:
    """When and how to use it"""
    text_lower = text.lower()
    guidance = {}
    
    # Dosing patterns
    dose_patterns = [
        (r"(?:maintenance|long-term|prevention).*?(\d+[^.]{10,60}(?:daily|day|b\.?i\.?d))", 'maintenance'),
        (r"(?:acute|infection|therapeutic).*?(\d+[^.]{10,60}(?:daily|day|b\.?i\.?d))", 'acute'),
        (r"recommendations?:?\s*(\d+[^.]{10,60})", 'general'),
    ]
    
    for pattern, dose_type in dose_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match and dose_type not in guidance:
            dose = match.group(1).strip()
            dose = re.sub(r'^\s*[:\-]\s*', '', dose)
            guidance[dose_type] = dose
    
    # Clinical context
    context_patterns = [
        r"should be considered for ([\w\s,]{15,80})",
        r"particularly (?:useful|effective) for ([\w\s,]{15,80})",
        r"best (?:used|suited) for ([\w\s,]{15,80})",
    ]
    
    for pattern in context_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            context = match.group(1).strip()
            guidance['context'] = context
            break
    
    return guidance

# ----------------------------- NARRATIVE ASSEMBLY -----------------------------

def _build_narrative_summary(
    purpose: Optional[str],
    mechanism: Optional[str],
    unique_value: Optional[str],
    usage: Dict[str, str]
) -> str:
    """Assemble a coherent narrative"""
    
    # Start with purpose (the "why")
    if purpose:
        # Clean up purpose to be a complete sentence
        narrative = f"Designed to support {purpose.lower()}."
    else:
        narrative = "Professional-grade nutritional support formula."
    
    # Add mechanism (the "how")
    if mechanism:
        # Make sure it flows naturally
        if not mechanism.endswith('.'):
            mechanism += '.'
        narrative += f" {mechanism}"
    
    # Add unique value (the "what sets it apart")
    if unique_value:
        if not unique_value.endswith('.'):
            unique_value += '.'
        narrative += f" {unique_value}"
    
    return narrative

# ----------------------------- MAIN SUMMARY FUNCTION -----------------------------

def make_answer(
    query: str,
    raw_chunks: List[str],
    product_hint: str = "",
    product_doc_titles: Optional[List[str]] = None
) -> dict:
    """Generate MI-team-focused practical summary"""
    
    all_text = " ".join(raw_chunks)
    format_type = _detect_format(all_text)
    
    # Extract components
    purpose = _extract_primary_purpose(all_text)
    mechanism = _extract_key_mechanism(all_text)
    unique_value = _extract_unique_value(all_text)
    usage = _extract_usage_guidance(all_text)
    
    # Get clinical applications
    clinical_apps = []
    app_match = re.search(r"clinical (?:applications?|considerations?):(.*?)(?:\n\n|\Z)", all_text, re.IGNORECASE | re.DOTALL)
    if app_match:
        apps_text = app_match.group(1)
        bullets = re.findall(r'[•\-]\s*(.+?)(?:\n|$)', apps_text)
        clinical_apps = [b.strip() for b in bullets[:3]]
    
    # Build practical summary
    summary = ""
    
    # PRIMARY INDICATIONS (what it's for)
    if clinical_apps:
        if len(clinical_apps) >= 2:
            summary = f"<strong>What conditions:</strong> {clinical_apps[0]} and {clinical_apps[1].lower()}."
        else:
            summary = f"**Primary indication:** {clinical_apps[0]}."
    elif purpose:
        summary = f"**Primary indication:** {purpose}."
    
    # MECHANISM (how it works)
    if mechanism:
        # Clean up mechanism
        mech_clean = mechanism.strip()
        
        # Ensure it's a complete sentence (starts with capital)
        if mech_clean and not mech_clean[0].isupper():
            # Probably a fragment, skip it
            mech_clean = ""
        
        # Remove redundant starts if present
        if mech_clean:
            mech_clean = re.sub(r'^(?:The combination of|The formula)\s+', '', mech_clean, flags=re.I)
        summary += f" <strong>How does it work?</strong> {mech_clean}."
    
    # KEY ADVANTAGE (what makes it special)
    if unique_value:
        unique_clean = unique_value
        if not unique_clean[0].isupper():
            unique_clean = unique_clean[0].upper() + unique_clean[1:]
        if not unique_clean.endswith('.'):
            unique_clean += '.'
        summary += f" <strong>Why choose this?</strong> {unique_clean}"
    
    blocks = []
    
    # Single summary block
    if summary:
        blocks.append(f"<div class='summary-section'><h3>Summary</h3><p>{summary}</p></div>")
    
    # Usage guidance
    
    # Show dosing only if extracted
    if usage:
        usage_text = ""
        if 'maintenance' in usage:
            usage_text += f"<strong>Maintenance:</strong> {usage['maintenance']}<br>"
        if 'acute' in usage:
            usage_text += f"<strong>Acute/Therapeutic:</strong> {usage['acute']}<br>"
        if 'general' in usage and 'maintenance' not in usage:
            usage_text += f"{usage['general']}"
        
        if usage_text:
            blocks.append(f"<div class='summary-section'><h3>Dosing</h3><p>{usage_text}</p></div>")
    
    return {"blocks": blocks}

# ----------------------------- Testing -----------------------------

if __name__ == "__main__":
    test_text = """
    Eye Defense: Clinical Guide
    
    Eye Defense provides comprehensive ocular support through an advanced formulation
    containing therapeutic concentrations of macular carotenoids. Each two-capsule serving 
    delivers superior 99% pure mesozeaxanthin compared to the 66% pure form used in most 
    competing ocular supplements. The combination with astaxanthin provides additional 
    benefits for dynamic focus—the ability to refocus when shifting gaze between near and 
    far objects—by supporting ocular muscle performance.
    
    Clinical Applications:
    • Age-related macular degeneration (dry and wet AMD)
    • Visual performance enhancement and protection
    • Blue light induced retinal damage
    
    Recommendations: 2 capsules daily for maintenance.
    """
    
    result = make_answer(
        query="eye health",
        raw_chunks=[test_text],
        product_hint="Eye Defense"
    )
    
    print("Narrative Summary Test:")
    for block in result["blocks"]:
        print(f"\n{block}")
