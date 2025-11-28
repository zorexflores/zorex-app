from answer_pipeline_wrapper import AnswerPipeline
import re

pipeline = AnswerPipeline()
products = pipeline.get_product_list()

print("="*80)
print("SUMMARY QUALITY REVIEW - ALL PRODUCTS")
print("="*80)
print(f"\nTotal products: {len(products)}\n")

for i, product in enumerate(products, 1):
    summary = pipeline.get_cached_summary(product)
    
    # Extract components
    indications = re.search(r'<strong>Primary indications:</strong> ([^<]+)', summary)
    mechanism = re.search(r'<strong>Mechanism:</strong> ([^<]+)', summary)
    advantage = re.search(r'<strong>Key advantage:</strong> ([^<]+)', summary)
    
    print(f"\n[{i}/{len(products)}] {product}")
    print("-" * 80)
    
    if indications:
        ind_text = indications.group(1).strip()
        print(f"✓ Indications: {ind_text[:100]}{'...' if len(ind_text) > 100 else ''}")
    else:
        print("✗ Indications: MISSING")
    
    if mechanism:
        mech_text = mechanism.group(1).strip()
        # Flag potential issues
        issues = []
        if len(mech_text.split()) < 8:
            issues.append("TOO SHORT")
        if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z]', mech_text):
            issues.append("HEADER LEAK")
        if not mech_text[0].isupper():
            issues.append("LOWERCASE START")
        
        status = "⚠️" if issues else "✓"
        flag = f" [{', '.join(issues)}]" if issues else ""
        print(f"{status} Mechanism: {mech_text[:100]}{'...' if len(mech_text) > 100 else ''}{flag}")
    else:
        print("✗ Mechanism: MISSING")
    
    if advantage:
        adv_text = advantage.group(1).strip()
        print(f"✓ Advantage: {adv_text[:100]}{'...' if len(adv_text) > 100 else ''}")
    else:
        print("  (No advantage)")

print("\n" + "="*80)
print("Review complete. Look for ✗ (missing) and ⚠️ (issues) markers.")
print("="*80)
