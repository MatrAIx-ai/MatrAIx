import json
import sys
import os

def main():
    # Allow running from anywhere by finding the personas directory relative to repo root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    json_path = os.path.join(repo_root, 'personas', 'dimensions+new.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        dimensions = data.get('dimensions', [])
        
        # 1. Check for synthlab or placeholder dimensions (should be 0)
        synthlab_count = sum(1 for d in dimensions if 'synthlab' in json.dumps(d).lower())
        
        # 2. Check marital status duplicates
        has_demo = any(d.get('id') == 'demo_marital_status' for d in dimensions)
        has_wiki = any(d.get('id') == 'wiki_marital_status' for d in dimensions)
        
        print("=== Phase 1 Validation Results ===")
        print(f"Total dimensions loaded: {len(dimensions)}")
        print(f"SynthLabs placeholders found: {synthlab_count} (Expected: 0)")
        print(f"demo_marital_status exists: {has_demo} (Expected: True)")
        print(f"wiki_marital_status exists: {has_wiki} (Expected: False)")
        
        if synthlab_count == 0 and has_demo and not has_wiki:
            print("\nValidation passed.")
            sys.exit(0)
        else:
            print("\nValidation failed.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
