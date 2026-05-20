"""
M9 Campaign Receptivity — Unit Tests
Run: pytest test/test_predictor.py -v
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from datetime import date
from shared.models import (
    ReceptivityRequest, CropType, DeviceType,
    FarmerSegment, CampaignFormat,
)
from campaign_receptivity_engine.predictor import predict_receptivity


def make_req(**kwargs) -> ReceptivityRequest:
    defaults = dict(crop=CropType.wheat, scoring_date=date(2026, 1, 15))
    defaults.update(kwargs)
    return ReceptivityRequest(**defaults)


class TestSegmentation:

    def test_high_clicker_is_digital_active(self):
        req = make_req(historical_click_rate=0.12, historical_open_rate=0.6)
        result = predict_receptivity(req)
        assert result.segment == FarmerSegment.digital_active

    def test_opener_not_clicker_is_passive(self):
        req = make_req(historical_click_rate=0.02, historical_open_rate=0.5)
        result = predict_receptivity(req)
        assert result.segment == FarmerSegment.digital_passive

    def test_keypad_user_is_offline(self):
        req = make_req(device_type=DeviceType.keypad)
        result = predict_receptivity(req)
        assert result.segment == FarmerSegment.offline_only

    def test_new_smartphone_user_is_new_farmer(self):
        req = make_req(device_type=DeviceType.smartphone)
        result = predict_receptivity(req)
        assert result.segment == FarmerSegment.new_farmer


class TestReceptivity:

    def test_active_farmer_high_receptivity(self):
        req = make_req(historical_click_rate=0.15, historical_open_rate=0.7)
        result = predict_receptivity(req)
        assert result.receptivity_score >= 0.5

    def test_offline_farmer_low_receptivity(self):
        req = make_req(device_type=DeviceType.keypad)
        result = predict_receptivity(req)
        assert result.receptivity_score <= 0.4

    def test_score_in_valid_range(self):
        req = make_req()
        result = predict_receptivity(req)
        assert 0.0 <= result.receptivity_score <= 1.0


class TestFormatRecommendations:

    def test_returns_formats(self):
        req = make_req(device_type=DeviceType.smartphone)
        result = predict_receptivity(req)
        assert len(result.recommended_formats) > 0

    def test_keypad_excludes_whatsapp(self):
        req = make_req(device_type=DeviceType.keypad)
        result = predict_receptivity(req)
        for fmt in result.recommended_formats:
            assert "whatsapp" not in fmt.format.value

    def test_active_segment_prefers_visual(self):
        req = make_req(historical_click_rate=0.15, historical_open_rate=0.7)
        result = predict_receptivity(req)
        top_format = result.recommended_formats[0].format
        assert top_format in (CampaignFormat.whatsapp_image, CampaignFormat.whatsapp_video)

    def test_offline_segment_prefers_field_or_voice(self):
        req = make_req(device_type=DeviceType.keypad)
        result = predict_receptivity(req)
        top_format = result.recommended_formats[0].format
        assert top_format in (CampaignFormat.field_demo, CampaignFormat.voice_ivr)


class TestFatigue:

    def test_many_messages_high_fatigue(self):
        req = make_req(messages_received_last_30d=10)
        result = predict_receptivity(req)
        assert result.fatigue_risk >= 0.6

    def test_few_messages_low_fatigue(self):
        req = make_req(messages_received_last_30d=0)
        result = predict_receptivity(req)
        assert result.fatigue_risk <= 0.3


class TestCreativeSuggestions:

    def test_suggestions_returned(self):
        req = make_req()
        result = predict_receptivity(req)
        assert len(result.creative_suggestions) > 0

    def test_fatigue_warning_when_high(self):
        req = make_req(messages_received_last_30d=12)
        result = predict_receptivity(req)
        has_fatigue_warning = any("fatigue" in s.lower() for s in result.creative_suggestions)
        assert has_fatigue_warning


class TestEndToEnd:

    def test_full_response_structure(self):
        req = make_req(
            grower_id="G_001",
            district="Jaipur",
            device_type=DeviceType.smartphone,
            farm_size_acres=3.0,
            grower_age=35,
            previously_clicked=True,
        )
        result = predict_receptivity(req)
        assert result.grower_id == "G_001"
        assert result.segment is not None
        assert 0.0 <= result.segment_confidence <= 1.0
        assert 0.0 <= result.receptivity_score <= 1.0
        assert len(result.recommended_formats) > 0
        assert result.best_day_of_week is not None
        assert result.best_time_window is not None
        assert 0.0 <= result.fatigue_risk <= 1.0
        assert result.model_version is not None

    def test_model_version(self):
        req = make_req()
        result = predict_receptivity(req)
        assert "receptivity" in result.model_version


class TestAPI:

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from campaign_receptivity_engine.main import app
        self.client = TestClient(app)

    def test_post_predict_api(self):
        payload = {
            "crop": "wheat",
            "district": "Jaipur",
            "device_type": "smartphone",
            "farm_size_acres": 3.0,
            "grower_age": 35,
            "messages_received_last_30d": 5,
            "previously_clicked": True
        }
        response = self.client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "segment" in data
        assert "receptivity_score" in data
        assert "recommended_formats" in data

    def test_get_predict_by_grower_id_api(self):
        from unittest.mock import MagicMock, patch
        from shared.models import Farmer

        # Create a mock database session
        mock_db = MagicMock()

        # Mock Farmer query
        mock_farmer = MagicMock()
        mock_farmer.grower_id = "GRW_00004"
        mock_farmer.crops = "wheat"
        mock_farmer.district = "Jaipur"
        mock_farmer.device_type = "smartphone"
        mock_farmer.grower_farm_size = 4.5
        mock_farmer.grower_age = 40
        mock_farmer.product_name = "Kavach 75 WP"
        mock_farmer.messages_received_last_30d = 3
        mock_farmer.messages_opened_last_30d = 2
        mock_farmer.product_scan = True
        mock_farmer.offline_campaign_attended = False

        # Set up query chains
        # Query for Farmer
        # Query for WhatsAppCampaign
        def mock_query(model):
            q = MagicMock()
            if model == Farmer:
                q.filter.return_value.first.return_value = mock_farmer
            else:
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = mock_query

        with patch("campaign_receptivity_engine.main.SessionLocal", return_value=mock_db):
            response = self.client.get("/predict/GRW_00004")
            assert response.status_code == 200
            data = response.json()
            print(data)
            assert data["grower_id"] == "GRW_00004"
            assert "segment" in data
            assert "receptivity_score" in data

    def test_get_predict_by_grower_id_not_found(self):
        from unittest.mock import MagicMock, patch

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("campaign_receptivity_engine.main.SessionLocal", return_value=mock_db):
            response = self.client.get("/predict/GRW_05989")
            print(response.json())
            assert response.status_code == 404
            assert "Farmer not found" in response.json()["detail"]
