# Org Social Live Preview

Live preview server for [Org Social](https://github.com/tanrax/org-social) posts. This application generates social media-like preview cards for any Org Social post URL in real-time.

![Screenshot](screenshot.png)

## Quick Start

```bash
# Copy environment configuration
cp .env.example .env

# Start the server with Docker Compose
docker compose up
```

The server will be available at `http://localhost:8080` (or the port configured in `.env`)

## Configuration

Edit `.env` to customize:

```env
# Flask configuration
FLASK_ENV=production          # Flask environment (production/development)
FLASK_DEBUG=False             # Enable/disable debug mode (True/False)

# Server URL configuration
PROTOCOL=http                 # Protocol: http or https
DOMAIN=localhost              # Domain name
EXTERNAL_PORT=8080            # External port (exposed on host)

# Cache timeouts in seconds
CACHE_TIMEOUT=30              # Preview cards cache duration
CACHE_FILE_TIMEOUT=30         # Remote social.org files cache duration
```

### Port visibility
- **Debug mode** (`FLASK_DEBUG=True`): Shows port in URLs (e.g., `http://localhost:8081`)
- **Production mode** (`FLASK_DEBUG=False`): Hides port (e.g., `https://preview.example.com`)

## Usage

### Docker Compose (Recommended)

```bash
# Start the server
docker compose up

# Rebuild and start
docker compose up --build

# Run in background
docker compose up -d
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask server
python app.py
```

### Access Preview Cards

Access the preview by passing a post URL as a query parameter:

```
http://localhost:8080/?post=https://foo.org/social.org#2025-02-03T23:05:00+0100
```

**Important**: The URL must be URL-encoded:

```
http://localhost:8080/?post=https%3A%2F%2Ffoo.org%2Fsocial.org%232025-02-03T23%3A05%3A00%2B0100
```

## Caching

Flask-Caching with SimpleCache improves performance:

- **Preview cards**: Cached based on the `CACHE_TIMEOUT` setting
- **Remote social.org files**: Cached based on the `CACHE_FILE_TIMEOUT` setting

Caching reduces load on remote servers and improves response times for repeated requests.

## Template Customization

### Preview Card Template (`templates/post.html`)

Customize the post preview card appearance:

- Styling and layout
- Open Graph metadata
- Post display format
- Color scheme and fonts

Available template variables:

- `nick`: User nickname
- `formatted_content`: Processed post content
- `mood`: Post mood emoji
- `tags`: List of tags
- `formatted_time`: Formatted timestamp
- `avatar_url`: User avatar URL
- `post_url`: Post permalink

### Welcome Page Template (`templates/welcome.html`)

Customize the homepage shown when no post parameter is provided.

## License

This project is open source. See the main [Org Social repository](https://github.com/tanrax/org-social) for more information.
