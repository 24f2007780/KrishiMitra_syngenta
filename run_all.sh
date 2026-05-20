#!/bin/bash

# Syngenta KrishiMitra - Microservices Runner
# Starts the active modules in the background.

export PYTHONPATH=$PYTHONPATH:.

echo "🚀 Starting Syngenta KrishiMitra Microservices..."

# Tier 1: Data Foundation
.venv/bin/python3 -m uvicorn farmer_service.main:app --host 0.0.0.0 --port 8001 &
.venv/bin/python3 -m uvicorn product_service.main:app --host 0.0.0.0 --port 8002 &

# Tier 2: Signal Ingestion
.venv/bin/python3 -m uvicorn weather_service.main:app --host 0.0.0.0 --port 8004 &
.venv/bin/python3 -m uvicorn calendar_service.main:app --host 0.0.0.0 --port 8005 &
.venv/bin/python3 -m uvicorn context_service.main:app --host 0.0.0.0 --port 8006 &

.venv/bin/python3 -m uvicorn urgency_scorer.main:app --host 0.0.0.0 --port 8007 &
python3 -m uvicorn campaign_receptivity_engine.main:app --host 0.0.0.0 --port 8008 &

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

echo "✅ Active services (M1, M2, M4, M5, M6, M8) initiated."
echo "Use './stop_all.sh' to terminate all services."
