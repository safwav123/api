from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel
import json
import uvicorn
import base64
from PIL import Image
import io
import os

# Create FastAPI app
app = FastAPI(title="Body Measurements and Abaya Recommendations API")

# Add CORS middleware to allow Flutter app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define body type recommendations data
BODY_TYPE_RECOMMENDATIONS = {
    "hourglass": [
        {"id": 1, "style": "Fitted", "body_type": "hourglass", "description": "Fitted abayas that accentuate the waist"},
        {"id": 2, "style": "Belt-Cinched", "body_type": "hourglass", "description": "Styles with belts to highlight the waistline"}
    ],
    "pear": [
        {"id": 3, "style": "A-Line", "body_type": "pear", "description": "A-line cuts that flow from the hip"},
        {"id": 4, "style": "Empire Waist", "body_type": "pear", "description": "Empire waist styles to draw attention upward"}
    ],
    "inverted_triangle": [
        {"id": 5, "style": "Flared", "body_type": "inverted_triangle", "description": "Flared bottom abayas to balance shoulders"},
        {"id": 6, "style": "Layered", "body_type": "inverted_triangle", "description": "Layered styles to add volume to lower body"}
    ],
    "rectangle": [
        {"id": 7, "style": "Pleated", "body_type": "rectangle", "description": "Pleated styles to create curves"},
        {"id": 8, "style": "Draped", "body_type": "rectangle", "description": "Draped abayas to add dimension"}
    ],
    "apple": [
        {"id": 9, "style": "Empire Line", "body_type": "apple", "description": "Empire line cuts to draw attention away from midsection"},
        {"id": 10, "style": "Straight Cut", "body_type": "apple", "description": "Straight cuts with flowing fabric"}
    ]
}

# Root endpoint to check if API is running
@app.get("/")
async def root():
    return {"message": "Body Measurements and Abaya Recommendations API is running"}

# Process measurements endpoint
@app.post("/process-measurements")
async def process_measurements(
    user_height_cm: float = Form(...),
    image: Optional[UploadFile] = File(None),
    manual_measurements: Optional[str] = Form(None)
):
    # Check if at least one of image or manual_measurements is provided
    if image is None and manual_measurements is None:
        raise HTTPException(status_code=400, detail="Either image or manual_measurements must be provided")
    
    # Process image if provided
    if image:
        try:
            # Here you would implement your image processing logic
            # This is a placeholder for your actual implementation
            image_content = await image.read()
            
            # Placeholder for your image processing algorithm
            # In a real implementation, you would extract measurements from the image
            
            # Return placeholder results - replace with actual processing logic
            results = [{
                "measurements": {
                    "bust": 92.5,
                    "waist": 73.2,
                    "hips": 98.8
                },
                "body_analysis": {
                    "type": "hourglass",
                    "confidence": "high",
                    "ratios": {
                        "waist_to_bust": 0.79,
                        "waist_to_hip": 0.74
                    }
                }
            }]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    
    # Process manual measurements if provided
    elif manual_measurements:
        try:
            # Parse the manual measurements JSON
            measurements_dict = json.loads(manual_measurements)
            
            # Determine body type based on measurements
            # This is a placeholder - implement your actual logic
            # For example:
            bust = measurements_dict.get("bust", 0)
            waist = measurements_dict.get("waist", 0)
            hips = measurements_dict.get("hips", 0)
            
            # Simple ratio-based body type determination
            body_type = "rectangle"  # default
            waist_to_bust_ratio = waist / bust if bust else 0
            waist_to_hip_ratio = waist / hips if hips else 0
            
            if waist_to_bust_ratio < 0.8 and waist_to_hip_ratio < 0.8:
                body_type = "hourglass"
            elif waist_to_bust_ratio > 0.8 and waist_to_hip_ratio < 0.8:
                body_type = "pear"
            elif waist_to_bust_ratio < 0.8 and waist_to_hip_ratio > 0.8:
                body_type = "inverted_triangle"
            elif waist_to_bust_ratio > 0.85 and waist_to_hip_ratio > 0.85:
                body_type = "apple"
            
            # Create response
            results = [{
                "measurements": measurements_dict,
                "body_analysis": {
                    "type": body_type,
                    "confidence": "medium",
                    "ratios": {
                        "waist_to_bust": waist_to_bust_ratio,
                        "waist_to_hip": waist_to_hip_ratio
                    }
                }
            }]
            
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in manual_measurements")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing measurements: {str(e)}")
    
    return {"results": results}

# Recommend abaya endpoint
@app.post("/recommend-abaya")
async def recommend_abaya(request: dict):
    try:
        body_type = request.get("body_type", "").lower()
        
        if body_type not in BODY_TYPE_RECOMMENDATIONS:
            # If body type not found, return general recommendations
            recommendations = [BODY_TYPE_RECOMMENDATIONS[bt][0] for bt in BODY_TYPE_RECOMMENDATIONS]
        else:
            recommendations = BODY_TYPE_RECOMMENDATIONS[body_type]
        
        # Add placeholder base64 images (in a real implementation, you'd load actual images)
        for rec in recommendations:
            # In an actual implementation, you would load and encode real images
            # This creates a tiny placeholder image
            img = Image.new('RGB', (100, 150), color=(73, 109, 137))
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            rec["image_base64"] = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return {"recommendations": recommendations}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")

# Run the API server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)