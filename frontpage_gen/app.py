"""
HTTP server wrapper for generate_cover.py
Exposes the cover generation functionality as a REST API for Cloud Run deployment.
"""
from flask import Flask, request, jsonify, send_file
import os
from generate_cover import generate_cover, get_random_background, get_player_paths
from gcs_utils import download_from_gcs, is_gcs_path
import traceback

app = Flask(__name__)

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# GCS bucket configuration (set via environment variable, e.g., GCS_BUCKET=my-bucket)
# If not set, will use local paths
GCS_BUCKET = os.environ.get('GCS_BUCKET', None)

def get_asset_path(asset_type, filename=None):
    """
    Get asset path (GCS or local).
    
    Args:
        asset_type: Type of asset ('backgrounds', 'players', 'qimen', 'assets')
        filename: Optional filename
    
    Returns:
        GCS path (gs://bucket/type/filename) or local path
        Note: 'assets' type always returns local path (bundled in image)
    """
    # Assets folder is always local (bundled in Docker image)
    if asset_type == "assets":
        if filename:
            return os.path.join(SCRIPT_DIR, asset_type, filename)
        else:
            return os.path.join(SCRIPT_DIR, asset_type)
    
    # Other asset types can be from GCS or local
    if GCS_BUCKET:
        from gcs_utils import get_gcs_path
        if filename:
            return get_gcs_path(GCS_BUCKET, asset_type, filename)
        else:
            return get_gcs_path(GCS_BUCKET, asset_type)
    else:
        # Local paths
        if filename:
            return os.path.join(SCRIPT_DIR, asset_type, filename)
        else:
            return os.path.join(SCRIPT_DIR, asset_type)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Cloud Run"""
    return jsonify({"status": "healthy"}), 200

@app.route('/generate', methods=['POST'])
def generate():
    """
    Generate a cover image.
    
    Expected JSON payload:
    {
        "date": "2025-11-26",
        "away_team": "HOU",
        "home_team": "GSW",
        "title": ["火旺克金形势显", "刺锋遇曜力难前"],
        "circle_cells": [2, 4]  // optional
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400
        
        # Validate required fields
        required_fields = ['date', 'away_team', 'home_team', 'title']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Extract parameters
        today_str = data['date']
        away_team = data['away_team']
        home_team = data['home_team']
        title_lines = data['title'] if isinstance(data['title'], list) else [data['title']]
        circle_cells = data.get('circle_cells', [])
        
        # Define paths (GCS or local based on GCS_BUCKET env var)
        backgrounds_dir = get_asset_path("backgrounds")
        bg_path = get_random_background(backgrounds_dir=backgrounds_dir)
        
        qimen_file = f"{today_str}.jpg"
        qimen_path = get_asset_path("qimen", qimen_file)
        
        # Get player paths
        players_dir = get_asset_path("players")
        player_paths = get_player_paths(
            away_team, 
            home_team, 
            players_dir=players_dir
        )
        
        # Build asset paths
        taiji_path = get_asset_path("assets", "taiji.png")
        fog_path = get_asset_path("assets", "fog.png")
        circle_path = get_asset_path("assets", "circle-red.png")
        footer_path = get_asset_path("assets", "footer.png")
        output_dir = os.path.join(SCRIPT_DIR, "output")
        
        # Download files from GCS if needed (convert GCS paths to local paths)
        # Note: assets/ (taiji, fog, circle, footer) are bundled in the image, so don't download from GCS
        bg_path = download_from_gcs(bg_path) if is_gcs_path(bg_path) else bg_path
        qimen_path = download_from_gcs(qimen_path) if is_gcs_path(qimen_path) else qimen_path
        player_paths = [download_from_gcs(p) if is_gcs_path(p) else p for p in player_paths]
        # Assets are bundled in the image, so they should already be local paths
        # taiji_path, fog_path, circle_path, footer_path are not downloaded from GCS
        
        # Generate cover (all paths are now local)
        output_name = f"cover_{today_str}.jpg"
        generate_cover(
            bg_path=bg_path,
            qimen_path=qimen_path,
            player_paths=player_paths,
            title_lines=title_lines,
            today_str=today_str,
            output_filename=output_name,
            output_dir=output_dir,
            taiji_path=taiji_path,
            fog_path=fog_path,
            circle_path=circle_path,
            circle_cells=circle_cells,
            footer_path=footer_path
        )
        
        # Return the generated file
        output_path = os.path.join(output_dir, output_name)
        if os.path.exists(output_path):
            return send_file(
                output_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=output_name
            )
        else:
            return jsonify({"error": "Cover generation completed but file not found"}), 500
            
    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({
            "error": "Failed to generate cover",
            "message": error_msg,
            "traceback": traceback.format_exc()
        }), 500

@app.route('/', methods=['GET'])
def index():
    """API documentation endpoint"""
    return jsonify({
        "service": "NBA Cover Generator",
        "endpoints": {
            "GET /health": "Health check",
            "POST /generate": "Generate cover image",
            "GET /": "This documentation"
        },
        "usage": {
            "endpoint": "POST /generate",
            "payload": {
                "date": "YYYY-MM-DD",
                "away_team": "Team code (e.g., HOU)",
                "home_team": "Team code (e.g., GSW)",
                "title": ["Line 1", "Line 2"],
                "circle_cells": [2, 4]  # optional
            }
        }
    }), 200

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

