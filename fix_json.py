import json

with open('product-catalog/canonical_products.json', 'r') as f:
    content = f.read()

content = content.replace('null', 'None')
content = content.replace('true', 'True')
content = content.replace('false', 'False')

try:
    data = eval(content)
    with open('product-catalog/canonical_products.json', 'w') as f:
        json.dump(data, f, indent=4)
    print("Successfully fixed JSON format.")
except Exception as e:
    print(f"Failed to parse and fix: {e}")
