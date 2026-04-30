#!/usr/bin/env python3
"""
Utility functions for Douyin → Vietnamese Video Pipeline
"""

import re
from datetime import timedelta
from typing import Tuple, Optional


def parse_srt_timing(time_str: str) -> float:
    """
    Parse SRT timestamp to seconds
    Format: HH:MM:SS,mmm

    Args:
        time_str: Timestamp string

    Returns:
        Time in seconds as float
    """
    try:
        parts = time_str.replace(",", ".").split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return 0.0


def format_srt_timing(seconds: float) -> str:
    """
    Format seconds to SRT timestamp
    Format: HH:MM:SS,mmm

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    ms = int((secs % 1) * 1000)
    secs = int(secs)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from Douyin URL

    Args:
        url: Douyin URL

    Returns:
        Video ID or None
    """
    # Pattern for Douyin URLs
    patterns = [
        r"video/(\d+)",  # douyin.com/video/1234567890
        r"v/(\w+)",  # Short URL
        r"dy\.com/(\w+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Fallback: use URL hash
    return url.split("/")[-1].split("?")[0]


def format_duration(td: timedelta) -> str:
    """
    Format timedelta to readable string

    Args:
        td: timedelta object

    Returns:
        Formatted string (e.g., "1h 23m 45s")
    """
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def estimate_processing_time(video_duration_seconds: float) -> timedelta:
    """
    Estimate total processing time

    Rough estimates:
    - Download: 10% of video duration
    - Extract audio: 5% of video duration
    - Transcribe: 50% of video duration (whisper is slow)
    - Translate: 30% per segment (~5s per segment)
    - Generate audio: 40% of video duration (edge-tts)
    - Mix audio/subtitles: 5% of video duration

    Total: ~140% of video duration

    Args:
        video_duration_seconds: Video duration in seconds

    Returns:
        Estimated processing time
    """
    estimate = video_duration_seconds * 1.4  # seconds
    return timedelta(seconds=estimate)


def parse_srt_file(filepath: str) -> list:
    """
    Parse SRT file and return list of subtitle dictionaries

    Args:
        filepath: Path to SRT file

    Returns:
        List of dicts with keys: index, start, end, text
    """
    import pysrt

    try:
        srt_list = pysrt.load(filepath, encoding="utf-8")
        result = []

        for sub in srt_list:
            result.append(
                {
                    "index": sub.index,
                    "start": str(sub.start),
                    "end": str(sub.end),
                    "text": sub.text,
                }
            )

        return result
    except Exception as e:
        print(f"Error parsing SRT file: {e}")
        return []


def get_video_duration(video_path: str) -> float:
    """
    Get video duration using FFprobe

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds
    """
    import subprocess
    import json

    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return 0.0
