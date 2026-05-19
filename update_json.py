import json

with open('product-catalog/canonical_products.json', 'r') as f:
    products = json.load(f)

for p in products:
    if p['name'] == 'Topik 15 WP':
        p['active_ingredients'] = "Clodinafop-propargyl 15% WP (150 g/kg)"
        p['description'] = "Selective post-emergence herbicide for control of grassy weeds, especially Phalaris minor (Canary grass), in wheat crops."
        p['target_crop'] = "wheat"
        p['target_pest'] = "Phalaris minor (Canary grass), grassy weeds"
        p['effective_stages'] = "post-emergence, 30-35 DAS, weed 3-4 leaf stage, tillering"
        p['treatment_intent'] = "curative"
        p['efficacy_rating'] = 0.9
        p['price_tier'] = "mid"
        p['application_mode'] = "foliar spray"
        p['systemic'] = True
        p['rain_sensitive_hours'] = 2
        p['moa_group'] = "HRAC-A"
        p['moa_class'] = "ACCase inhibitor"
        p['resistance_management'] = "Use in rotation with herbicides having different modes of action to delay resistance development in grassy weeds."
        p['epa_number'] = None
        p['logo_url'] = "https://www.syngenta.co.in/sites/g/files/kgtney376/files/styles/brand_logo/public/media/image/2021/12/16/topik-thumbnail_with_background.png?itok=f_FdmQi1"
        p['product_url'] = "https://www.syngenta.co.in/product/crop-protection/topik-15-wp"
        p['directions'] = "Apply 30-35 days after sowing when grassy weeds are at 3-4 leaf stage. Mix 400 g in 375-400 litres of water per hectare. Spray uniformly using a flat fan nozzle. Best results are obtained on actively growing weeds. Do not spray before rain or on stressed crops."
    elif p['name'] == 'Score 250 EC':
        p['active_ingredients'] = "Difenoconazole 250 g/L"
        p['description'] = "Broad-spectrum systemic triazole fungicide effective against leaf rust, leaf spots, blight, and mildew diseases in multiple crops."
        p['target_crop'] = "wheat, mustard, chickpea, lentil, barley, oilseed rape, cabbage, cauliflower, broccoli, kale, brussels sprouts"
        p['target_pest'] = "leaf rust, leaf spot, blight, mildew, fungal diseases"
        p['effective_stages'] = "tillering, flowering, pod formation, canopy development, general"
        p['treatment_intent'] = "preventive, curative"
        p['efficacy_rating'] = 0.9
        p['price_tier'] = "mid"
        p['application_mode'] = "foliar spray"
        p['systemic'] = True
        p['rain_sensitive_hours'] = 1
        p['moa_group'] = "FRAC-3"
        p['moa_class'] = "DMI triazole"
        p['resistance_management'] = "Avoid repeated consecutive applications of FRAC Group 3 fungicides. Rotate with fungicides of different modes of action."
        p['epa_number'] = None
        p['logo_url'] = None
        p['product_url'] = None
        p['directions'] = "Mix 20 ml in 20 litres of water for knapsack spraying. Spray evenly on crop foliage at early disease appearance or preventively. Use 200 ml per acre or 500 ml per hectare. Do not spray during strong sunlight or rain. Maintain a 14-day interval before harvest."

with open('product-catalog/canonical_products.json', 'w') as f:
    json.dump(products, f, indent=4)
