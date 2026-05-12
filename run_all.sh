#!/bin/bash

# Syngenta KrishiMitra - Microservices Runner
# Starts the active modules in the background.

export PYTHONPATH=$PYTHONPATH:.

echo "🚀 Starting Syngenta KrishiMitra Microservices..."

# Tier 1: Data Foundation
python3 -m uvicorn farmer_service.main:app --host 0.0.0.0 --port 8001 &
python3 -m uvicorn product_service.main:app --host 0.0.0.0 --port 8002 &

# Tier 2: Signal Ingestion
python3 -m uvicorn weather_service.main:app --host 0.0.0.0 --port 8004 &

# The following modules are placeholders or not yet fully implemented
# # Tier 2: Signal Ingestion (Cont.)
# python3 -m uvicorn calendar_service.main:app --host 0.0.0.0 --port 8005 &
# python3 -m uvicorn context_service.main:app --host 0.0.0.0 --port 8006 &

# # Tier 3: Intelligence Engine
# python3 -m uvicorn scoring_service.main:app --host 0.0.0.0 --port 8007 &
# python3 -m uvicorn ranking_service.main:app --host 0.0.0.0 --port 8008 &
# python3 -m uvicorn explainer_service.main:app --host 0.0.0.0 --port 8009 &

# # Tier 4: Content Generation
# python3 -m uvicorn sms_service.main:app --host 0.0.0.0 --port 8010 &
# python3 -m uvicorn whatsapp_service.main:app --host 0.0.0.0 --port 8011 &
# python3 -m uvicorn voice_service.main:app --host 0.0.0.0 --port 8012 &

# # Tier 5: Delivery & Routing
# python3 -m uvicorn routing_service.main:app --host 0.0.0.0 --port 8013 &
# python3 -m uvicorn timing_service.main:app --host 0.0.0.0 --port 8014 &
# python3 -m uvicorn delivery_service.main:app --host 0.0.0.0 --port 8015 &

# # Tier 6: Orchestration
# python3 -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8016 &

echo "✅ Active services (M1, M2, M4) initiated."
echo "Use './stop_all.sh' to terminate all services."
