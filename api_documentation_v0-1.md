# MySalonCast API Documentation

This document describes the endpoints available in the MySalonCast API for generating podcasts from various content sources.

## Base URL

For local development: `http://localhost:8080`

## Content Processing Endpoints

### Process PDF File

Extract text content from a PDF file.

- **URL**: `/process/pdf/`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| pdf_file  | File | Yes      | PDF file to process |

#### Response

```json
{
  "filename": "document.pdf",
  "message": "PDF received, validated, and text extracted successfully.",
  "extracted_text_snippet": "The beginning of the extracted text...",
  "total_extracted_characters": 12345
}
```

#### Error Response

```json
{
  "detail": "Invalid PDF file. Please upload a valid PDF document."
}
```

---

### Process URL

Extract content from a web URL.

- **URL**: `/process/url/`
- **Method**: `POST`
- **Content-Type**: `application/x-www-form-urlencoded`

#### Request Parameters

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| url       | String | Yes      | URL to process |

#### Response

```json
{
  "url": "https://example.com/article",
  "message": "URL received, validated, and content extracted successfully.",
  "extracted_content_snippet": "The beginning of the extracted content...",
  "total_extracted_characters": 12345
}
```

#### Error Response

```json
{
  "detail": "Invalid URL provided. Please enter a valid HTTP/HTTPS/FTP URL."
}
```

---

### Process YouTube URL

Extract transcript from a YouTube video.

- **URL**: `/process/youtube/`
- **Method**: `POST`
- **Content-Type**: `application/x-www-form-urlencoded`

#### Request Parameters

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| url       | String | Yes      | YouTube video URL |

#### Response

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "message": "YouTube URL received, validated, and transcript extracted successfully.",
  "transcript_snippet": "The beginning of the transcript...",
  "total_transcript_characters": 12345
}
```

#### Error Response

```json
{
  "detail": "Invalid YouTube URL provided. Please enter a valid YouTube video URL."
}
```

## Podcast Generation

### Generate Podcast

Generate a podcast from source content and specified parameters.

- **URL**: `/generate/podcast_elements/`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### Request Body

```json
{
  "source_urls": ["https://example.com/article"],
  "source_pdf_path": null,
  "prominent_persons": ["Ruth Bader Ginsburg", "Clarence Thomas"],
  "desired_podcast_length_str": "15 minutes",
  "custom_prompt_for_outline": "Focus on the legal implications of the case",
  "host_invented_name": "Julia Michaels",
  "host_gender": "female",
  "custom_prompt_for_dialogue": "Make the dialogue engaging and informative"
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| source_urls | Array[String] | Yes* | List of URLs to source content from |
| source_pdf_path | String | Yes* | Path to a PDF file (must be previously uploaded) |
| prominent_persons | Array[String] | No | List of names of prominent people to feature in the podcast |
| desired_podcast_length_str | String | No | Target length of podcast (e.g., "10 minutes") |
| custom_prompt_for_outline | String | No | Custom instructions for generating the podcast outline |
| host_invented_name | String | No | Name for the podcast host |
| host_gender | String | No | Gender of the host for voice synthesis ("male", "female", or "neutral") |
| custom_prompt_for_dialogue | String | No | Custom instructions for dialogue generation |

*At least one of `source_urls` or `source_pdf_path` must be provided

#### Response

```json
{
  "podcast_id": "a1b2c3d4",
  "title": "The Supreme Court and Constitutional Interpretation",
  "outline": {
    "title": "The Supreme Court and Constitutional Interpretation",
    "description": "A discussion about judicial philosophy and constitutional interpretation",
    "segments": [
      {
        "segment_id": 1,
        "title": "Introduction to Originalism",
        "summary": "Discussion of originalist approach to constitutional interpretation"
      },
      {
        "segment_id": 2,
        "title": "Living Constitution Theory",
        "summary": "Examination of the living constitution judicial philosophy"
      }
    ]
  },
  "audio_url": "/listen/a1b2c3d4",
  "segment_urls": [
    "/listen/a1b2c3d4/segment/1",
    "/listen/a1b2c3d4/segment/2"
  ]
}
```

## Podcast Playback

### Get Full Podcast Audio

Get the complete podcast audio with a web player.

- **URL**: `/listen/{podcast_id}`
- **Method**: `GET`
- **Response Format**: HTML page with audio player

#### URL Parameters

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| podcast_id | String | Yes      | ID of the podcast |

#### Response

HTML page containing an audio player for the complete podcast, with download option.

### Get Podcast Segment Audio

Get an individual segment of the podcast with a web player.

- **URL**: `/listen/{podcast_id}/segment/{segment_id}`
- **Method**: `GET`
- **Response Format**: HTML page with audio player

#### URL Parameters

| Parameter  | Type   | Required | Description |
|------------|--------|----------|-------------|
| podcast_id | String | Yes      | ID of the podcast |
| segment_id | Integer| Yes      | ID of the segment |

#### Response

HTML page containing an audio player for the specified podcast segment, with download option.

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Request succeeded
- `400 Bad Request` - Invalid input parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

Error responses include a `detail` field with an explanation of the error.

## Example Usage

### Generate a Podcast from a URL

```
curl -X POST http://localhost:8080/api/podcasts/generate \
  -H "Content-Type: application/json" \
  -d '{
    "source_urls": ["https://example.com/article-about-supreme-court"],
    "prominent_persons": ["Ruth Bader Ginsburg", "Clarence Thomas"],
    "desired_podcast_length_str": "15 minutes",
    "host_invented_name": "Julia Michaels",
    "host_gender": "female"
  }'
```

### Play a Generated Podcast

Open in browser: `http://localhost:8080/listen/a1b2c3d4`
