from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from shared.models import CropStageInfo
from app.services.calendar_loader import get_crop_stage, get_supported_states, get_supported_crops
from typing import List

router = APIRouter(prefix="/calendar", tags=["calendar"])

@router.get("", response_model=CropStageInfo)
async def get_calendar(
    state: str = Query(..., description="State name"),
    crop: str = Query(..., description="Crop name"),
    month: str = Query(None, description="Optional month name (defaults to current month)")
):
    """
    Returns the current crop stage information for a given state, crop, and month.
    If month is not provided, it automatically detects the current month.
    """
    # Detect current month if not provided
    if not month:
        month = datetime.now().strftime("%B").lower()
    else:
        month = month.lower()
        
    stage_info = get_crop_stage(state, crop, month)
    
    if not stage_info:
        # Check why it failed to provide specific error messages
        supported_states = [s.lower() for s in get_supported_states()]
        if state.lower() not in supported_states:
            raise HTTPException(status_code=404, detail=f"State '{state}' not supported.")
            
        # If state exists, check crop
        calendar_data = get_crop_stage(state, "rice", "may") # dummy check for state existence
        # Re-fetch state specifically to check crops
        from app.services.calendar_loader import load_calendar
        all_data = load_calendar()
        normalized_state = next((s for s in all_data.keys() if s.lower() == state.lower()), None)
        
        if normalized_state:
            state_data = all_data[normalized_state]
            if crop.lower() not in state_data:
                raise HTTPException(status_code=404, detail=f"Crop '{crop}' not supported for state '{state}'.")
            
            if month not in state_data[crop.lower()]:
                raise HTTPException(status_code=404, detail=f"Missing month data for '{month}' in {state}/{crop}.")

        raise HTTPException(status_code=404, detail="Crop stage information not found.")
        
    return stage_info

@router.get("/states", response_model=List[str])
async def list_states():
    """
    Returns a list of supported states.
    """
    return get_supported_states()

@router.get("/crops", response_model=List[str])
async def list_crops():
    """
    Returns a list of supported crops.
    """
    return get_supported_crops()
