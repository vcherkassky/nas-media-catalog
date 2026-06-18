"""Unit tests for the M3U parser used by /playlists/import."""

import pytest

from nas_media_catalog.main import _parse_m3u


@pytest.mark.unit
def test_parse_minimal_m3u():
    content = "#EXTM3U\n#EXTINF:-1,Title\nhttp://example.com/a.mp4\n"
    parsed = _parse_m3u(content, fallback_name="fb")
    assert parsed["name"] == "fb"
    assert parsed["description"] == ""
    assert parsed["urls"] == ["http://example.com/a.mp4"]


@pytest.mark.unit
def test_parse_uses_playlist_directive_as_name():
    content = (
        "#EXTM3U\n"
        "#PLAYLIST:Road Trip Mix\n"
        "#EXTINF:-1,Song\n"
        "http://example.com/song.mp3\n"
    )
    parsed = _parse_m3u(content, fallback_name="ignored")
    assert parsed["name"] == "Road Trip Mix"


@pytest.mark.unit
def test_parse_collects_description_comments_skipping_vlc_instructions():
    """Description comments after #PLAYLIST are kept; our exporter's VLC instructions are skipped."""
    content = (
        "#EXTM3U\n"
        "#PLAYLIST:My Mix\n"
        "# A weekend listening list\n"
        "# Curated 2026\n"
        "# TO OPEN IN VLC:\n"
        "# Right-click this file -> Open With -> VLC\n"
        "\n"
        "#EXTINF:-1,Song\n"
        "http://example.com/a.mp3\n"
    )
    parsed = _parse_m3u(content, fallback_name="fb")
    assert parsed["name"] == "My Mix"
    assert "weekend listening" in parsed["description"]
    assert "TO OPEN IN VLC" not in parsed["description"]
    assert "Right-click" not in parsed["description"]


@pytest.mark.unit
def test_parse_deduplicates_urls_preserving_order():
    content = (
        "#EXTM3U\n"
        "http://example.com/a.mp4\n"
        "http://example.com/b.mp4\n"
        "http://example.com/a.mp4\n"
    )
    parsed = _parse_m3u(content, fallback_name="fb")
    assert parsed["urls"] == [
        "http://example.com/a.mp4",
        "http://example.com/b.mp4",
    ]


@pytest.mark.unit
def test_parse_rejects_missing_extm3u_header():
    with pytest.raises(ValueError, match="EXTM3U"):
        _parse_m3u("http://example.com/a.mp4\n", fallback_name="fb")


@pytest.mark.unit
def test_parse_rejects_when_no_urls_present():
    content = "#EXTM3U\n#PLAYLIST:Empty\n# Just a description\n"
    with pytest.raises(ValueError, match="No media URLs"):
        _parse_m3u(content, fallback_name="fb")


@pytest.mark.unit
def test_parse_strips_bom_and_handles_crlf():
    content = "﻿#EXTM3U\r\n#PLAYLIST:Windows\r\nhttp://example.com/a.mp4\r\n"
    parsed = _parse_m3u(content, fallback_name="fb")
    assert parsed["name"] == "Windows"
    assert parsed["urls"] == ["http://example.com/a.mp4"]


@pytest.mark.unit
def test_parse_round_trip_with_real_exporter_output():
    """Feed the parser the exact shape our /media/{id}/download.m3u writes."""
    content = (
        "#EXTM3U\n"
        "#PLAYLIST:_05x02\n"
        "# \n"
        "# TO OPEN IN VLC:\n"
        "# • Right-click this file → Open With → VLC\n"
        "# • OR drag this file into VLC window\n"
        "# • OR use Terminal: open -a VLC filename.m3u\n"
        "# (Double-clicking opens Apple Music, not VLC!)\n"
        "\n"
        "#EXTINF:-1,._05x02\n"
        "http://192.168.178.1:49200/VIDEO/DLNA-8-0/Shows/X/._05x02.avi\n"
    )
    parsed = _parse_m3u(content, fallback_name="fallback")
    assert parsed["name"] == "_05x02"
    # All description content was VLC instructions, so description is empty
    assert parsed["description"] == ""
    assert parsed["urls"] == [
        "http://192.168.178.1:49200/VIDEO/DLNA-8-0/Shows/X/._05x02.avi"
    ]
