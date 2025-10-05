#!/usr/bin/env python3

from flask import Flask, request, render_template, abort
from flask_caching import Cache
from urllib.parse import unquote
import requests
import re
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

app = Flask(__name__)

# Get cache timeouts from environment variables
CACHE_TIMEOUT = int(os.getenv("CACHE_TIMEOUT", "30"))
CACHE_FILE_TIMEOUT = int(os.getenv("CACHE_FILE_TIMEOUT", "30"))

# Configure Flask-Caching
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = CACHE_TIMEOUT

cache = Cache(app)


class OrgSocialParser:
    def __init__(self):
        self.metadata = {}
        self.posts = []

    def parse_content(self, content):
        """Parse the org social content and extract metadata and posts"""
        self.metadata = {}
        self.posts = []

        # Extract global metadata
        self._extract_metadata(content)

        # Extract posts
        self._extract_posts(content)

        return self.posts

    def _extract_metadata(self, content):
        """Extract global metadata from the org file"""
        metadata_patterns = {
            "TITLE": r"^\s*\#\+TITLE:\s*(.+)$",
            "NICK": r"^\s*\#\+NICK:\s*(.+)$",
            "DESCRIPTION": r"^\s*\#\+DESCRIPTION:\s*(.+)$",
            "AVATAR": r"^\s*\#\+AVATAR:\s*(.+)$",
        }

        for key, pattern in metadata_patterns.items():
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                self.metadata[key] = match.group(1).strip()

    def _extract_posts(self, content):
        """Extract all posts from the org file"""
        # Find the Posts section
        posts_pattern = r"^\*\s+Posts\s*$"
        posts_section_match = re.search(posts_pattern, content, re.MULTILINE)
        if not posts_section_match:
            print("Posts section not found")
            return

        posts_content = content[posts_section_match.end() :]

        # Find all ** headers (posts) - looking for ** at start of line
        post_pattern = r"^(\*\*)\s*$"
        post_positions = []

        for match in re.finditer(post_pattern, posts_content, re.MULTILINE):
            post_positions.append(match.end())

        if not post_positions:
            print("No headers found in Posts section")
            return

        print(f"Found {len(post_positions)} headers")

        # Extract content between ** headers
        for i, start_pos in enumerate(post_positions):
            # Find the end of this post (next ** or end of content)
            if i + 1 < len(post_positions):
                # Find the next ** header
                next_start = post_positions[i + 1]
                # Go back to find the actual ** line
                temp_content = posts_content[:next_start]
                last_newline = temp_content.rfind("\n**")
                if last_newline != -1:
                    end_pos = last_newline
                else:
                    end_pos = next_start
            else:
                end_pos = len(posts_content)

            block = posts_content[start_pos:end_pos].strip()

            if block:
                post = self._parse_post_block(block)
                if post and post.get("ID"):
                    self.posts.append(post)
                    print(f"Post added with ID: {post.get('ID')}")

    def _parse_post_block(self, block):
        """Parse a single post block"""
        post = {}

        # Extract properties
        properties_match = re.search(r":PROPERTIES:\s*\n(.*?)\n:END:", block, re.DOTALL)
        if properties_match:
            properties_content = properties_match.group(1)

            # Parse each property using simple string operations
            for line in properties_content.split("\n"):
                line = line.strip()
                if line and line.startswith(":") and line.count(":") >= 2:
                    # Find the second colon
                    first_colon = line.find(":", 1)
                    if first_colon != -1:
                        key = line[1:first_colon].strip()
                        value = line[first_colon + 1 :].strip()
                        if key:
                            post[key] = value

        # Extract post content (everything after :END:)
        end_match = re.search(r":END:\s*\n", block)
        if end_match:
            content = block[end_match.end() :].strip()
            post["content"] = content
        else:
            # No properties block, entire block is content
            post["content"] = block

        return post

    def find_post_by_id(self, post_id):
        """Find a specific post by ID"""
        for post in self.posts:
            if post.get("ID") == post_id:
                return post
        return None


class PreviewGenerator:
    def __init__(self, template_dir=".", template_name="template.html"):
        self.env = Environment(loader=FileSystemLoader(template_dir))

        def og_description(value, max_length=120):
            import re

            # Replace newlines with spaces
            text = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
            # Collapse all whitespace to single spaces
            text = re.sub(r"\s+", " ", text)
            # HTML tag filter
            text = re.sub(r"<[^>]+>", "", text)
            # Collapse multiple spaces
            text = re.sub(r" +", " ", text)
            if len(text) > max_length:
                text = text[:max_length].rstrip() + "..."
            return text.strip()

        self.env.filters["og_description"] = og_description
        self.template = self.env.get_template(template_name)

    def generate_preview(self, post, metadata, feed_url=""):
        """Generate HTML preview for a single post"""
        context = self._prepare_context(post, metadata, feed_url)
        return self.template.render(**context)

    def _prepare_context(self, post, metadata, feed_url):
        """Prepare context data for template rendering"""
        post_id = post.get("ID", "")
        content = post.get("content", "")
        mood = post.get("MOOD", "")
        lang = post.get("LANG", "es")
        tags = post.get("TAGS", "")
        reply_to = post.get("REPLY_TO", "")
        client = post.get("CLIENT", "")

        formatted_content = self._format_content(content, mood, reply_to)

        nick = metadata.get("NICK", "User")
        title = metadata.get("TITLE", "social.org")
        description = metadata.get("DESCRIPTION", "")
        avatar_url = metadata.get("AVATAR", "")

        formatted_time = self._format_timestamp(post_id)
        tags_list = tags.split() if tags else []

        post_url = f"{feed_url}#{post_id}" if feed_url and post_id else ""

        return {
            "post_id": post_id,
            "content": content,
            "formatted_content": formatted_content,
            "mood": mood,
            "language": lang,
            "tags": tags_list,
            "tags_string": tags,
            "reply_to": reply_to,
            "client": client,
            "is_reply": bool(reply_to),
            "has_mood": bool(mood),
            "has_tags": bool(tags),
            "has_content": bool(content.strip()),
            "nick": nick,
            "title": title,
            "description": description,
            "avatar_url": avatar_url,
            "has_avatar": bool(avatar_url),
            "user_initial": nick[0].upper() if nick else "U",
            "formatted_time": formatted_time,
            "timestamp": post_id,
            "post_url": post_url,
        }

    def _format_content(self, content, mood, reply_to):
        """Format post content"""
        if not content.strip() and mood:
            return f'<span style="font-size: 20px;">{mood}</span>'

        formatted = content

        # Handle org-social mentions
        formatted = re.sub(
            r"\[\[org-social:([^\]]+)\]\[([^\]]+)\]\]",
            r'<a href="#" style="color: #1d9bf0;">@\2</a>',
            formatted,
        )

        # Handle regular links
        formatted = re.sub(
            r"\[\[([^\]]+)\]\[([^\]]+)\]\]",
            r'<a href="\1" style="color: #1d9bf0;" target="_blank">\2</a>',
            formatted,
        )

        # Handle simple URLs
        formatted = re.sub(
            r"\[\[([^\]]+)\]\]",
            r'<a href="\1" style="color: #1d9bf0;" target="_blank">\1</a>',
            formatted,
        )

        # Convert line breaks
        formatted = formatted.replace("\n", "<br>")

        return formatted or "No content"

    def _format_timestamp(self, timestamp):
        """Format timestamp for display"""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return "2024-01-01"


def parse_post_url(post_url):
    """
    Parse a post URL to extract the social.org file URL and post ID.
    Example: https://foo.org/social.org#2025-02-03T23:05:00+0100
    Returns: (file_url, post_id)
    """
    if "#" not in post_url:
        return None, None

    parts = post_url.split("#", 1)
    file_url = parts[0]
    post_id = parts[1] if len(parts) > 1 else None

    return file_url, post_id


@cache.memoize(timeout=CACHE_FILE_TIMEOUT)
def fetch_social_org(url):
    """Fetch a social.org file from a URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


@app.route("/")
@cache.cached(timeout=CACHE_TIMEOUT, query_string=True)
def preview():
    """Main route to display post preview"""
    post_url = request.args.get("post")

    if not post_url:
        domain = os.getenv("DOMAIN", "localhost")
        port = os.getenv("EXTERNAL_PORT", "8080")
        protocol = os.getenv("PROTOCOL", "http")
        debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
        flask_env = os.getenv("FLASK_ENV", "production")

        # Show port only in debug mode or development
        show_port = debug_mode or flask_env == "development"

        return render_template(
            "welcome.html",
            domain=domain,
            port=port,
            protocol=protocol,
            show_port=show_port,
        )

    # Decode the URL parameter
    post_url = unquote(post_url)

    # Parse the post URL
    file_url, post_id = parse_post_url(post_url)

    if not file_url or not post_id:
        abort(
            400,
            "Invalid post URL format. Expected: https://example.org/social.org#POST_ID",
        )

    # Fetch the social.org file
    content = fetch_social_org(file_url)
    if not content:
        abort(500, f"Could not fetch social.org file from {file_url}")

    # Parse the content
    parser = OrgSocialParser()
    parser.parse_content(content)

    # Find the specific post
    post = parser.find_post_by_id(post_id)
    if not post:
        abort(404, f"Post with ID {post_id} not found")

    # Generate preview
    generator = PreviewGenerator(template_dir="templates", template_name="post.html")
    html = generator.generate_preview(post, parser.metadata, feed_url=file_url)

    return html


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    app.run(host="0.0.0.0", port=8080, debug=debug_mode)
