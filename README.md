# NBA Prediction Cover Generator

A Flask-based service for generating NBA game cover images with custom backgrounds, player images, and Chinese text overlays.

## Features

- Generate custom NBA game cover images
- Support for team logos and player images
- Integration with Google Cloud Storage
- Docker containerization for easy deployment
- Cloud Run deployment support

## Project Structure

```
nba_prediction/
├── frontpage-gen/          # Main application directory
│   ├── app.py             # Flask API server
│   ├── generate_cover.py  # Cover generation logic
│   ├── gcs_utils.py       # Google Cloud Storage utilities
│   ├── Dockerfile         # Docker configuration for cover generator
│   ├── assets/            # Static assets (fonts, images)
│   ├── backgrounds/       # Background images
│   ├── logos/             # Team logos
│   ├── players/           # Player images
│   ├── qimen/             # Qimen images
│   └── output/            # Generated cover images
└── n8n/                   # n8n workflow automation
    ├── Dockerfile         # Docker configuration for n8n
    └── n8n_cloudrun_deploy.sh  # Deploy n8n with PostgreSQL
```

## Setup

1. Install dependencies:
```bash
cd frontpage-gen
pip install -r requirements.txt
```

2. Set up Google Cloud Storage (optional):
   - See `frontpage-gen/GCS_SETUP.md` for detailed instructions
   - Set `GCS_BUCKET` environment variable if using GCS

3. Run locally:
```bash
cd frontpage-gen
python app.py
```

## API Endpoints

- `GET /health` - Health check
- `GET /` - API documentation
- `POST /generate` - Generate cover image

See `frontpage-gen/app.py` for detailed API documentation.

## Deployment

The project includes scripts for deploying to Google Cloud Run:
- `frontpage-gen/deploy_cloudrun.sh` - Deploy the frontpage generator
- `n8n/n8n_cloudrun_deploy.sh` - Deploy n8n workflow with PostgreSQL
- `n8n/n8n_cloudrun_deploy_sqlite.sh` - Deploy n8n workflow with SQLite

## License

[Add your license here]

