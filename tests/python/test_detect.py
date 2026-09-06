"""Tests for Detect.js logic (ported to Python for testing)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "python"))

# Since Detect.js is JavaScript, we test the Python equivalents in demo.py
# This is a placeholder for when we port detection logic to Python or add a JS test runner

import pytest


def test_slug():
    """Test slug function from demo.py"""
    from omaping.demo import slug

    assert slug("Google Chrome") == "google-chrome"
    assert slug("app.slack.com") == "app-slack-com"
    assert slug("KDE Connect") == "kde-connect"
    assert slug("  spaces  ") == "spaces"
    assert slug("UPPERCASE") == "uppercase"
    assert slug("special!@#chars") == "special-chars"


def test_identity():
    """Test identity function from demo.py"""
    from omaping.demo import identity

    # Web notification
    web_notif = {"web": "app.slack.com", "summary": "#design", "body": "test"}
    result = identity(web_notif)
    assert result["key"] == "web:app.slack.com"
    assert result["source"] == "app.slack.com"
    assert result["app"] == "Google Chrome"
    assert result["icon"] == "google-chrome"

    # App notification
    app_notif = {"app": "kitty", "icon": "kitty", "summary": "Tests", "body": "passed"}
    result = identity(app_notif)
    assert result["key"] == "app:kitty"
    assert result["source"] == "kitty"
    assert result["app"] == "kitty"
    assert result["icon"] == "kitty"

    # Notify-send fallback
    bare_notif = {"summary": "Test", "body": "body"}
    result = identity(bare_notif)
    assert result["key"] == "app:notify-send"
    assert result["app"] == "notify-send"


def test_web_body_wrapper():
    """Test web() function wraps body with origin anchor"""
    from omaping.demo import web

    result = web("app.slack.com", "Hello world")
    assert 'href="https://app.slack.com/"' in result
    assert "app.slack.com" in result
    assert "Hello world" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])