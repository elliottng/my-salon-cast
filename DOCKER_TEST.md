# MySalonCast API Local Docker Test

## Setup and Run

### 1. Build the Docker container:
```bash
docker build -t mysaloncast-api .
```

### 2. Run the container locally:
```bash
docker run -p 8000:8000 mysaloncast-api
```

The API will be available at `http://localhost:8000`

### 3. Test the API:
```bash
python test_api_local.py \
  --source-urls "https://example.com/article1,https://example.com/article2" \
  --prominent-people "Einstein,Marie Curie" \
  --length "15 minutes"
```

### Additional test options:
```bash
# Open browser automatically when audio is ready
python test_api_local.py \
  --source-urls "https://example.com/article" \
  --prominent-people "Tesla" \
  --length "10 minutes" \
  --open-browser

# Use custom API URL
python test_api_local.py \
  --source-urls "https://example.com/article" \
  --prominent-people "Tesla" \
  --length "10 minutes" \
  --base-url "http://localhost:9000"
```

## What the test does:

1. **POST** `/generate/podcast_async/` - Creates podcast with your parameters
2. **GET** `/status/{task_id}` - Polls every 60 seconds until completion  
3. **GET** `/podcast/{task_id}/audio` - Gets the web page with audio player

**Note:** Both endpoints now consistently use `task_id` as the identifier - the same UUID generated during podcast creation.

The final step returns a web page with an embedded audio player pointed at the MP3 file.