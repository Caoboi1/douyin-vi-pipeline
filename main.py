#!/usr/bin/env python3
"""
Douyin → Vietnamese Video Pipeline
Automatically convert Douyin videos to Vietnamese dubbed version with subtitles

Using Google Gemini 1.5 Flash (45x cheaper than Claude!)

Usage:
    python main.py single <url>
    python main.py batch <urls_file>
    python main.py preview <url>
    python main.py translate <srt_file>
    python main.py config  # Configure TTS voice & quality
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Literal
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import google.generativeai as genai
from tqdm import tqdm
import pysrt

from utils import (
    parse_srt_timing,
    format_srt_timing,
    extract_video_id,
    format_duration,
    estimate_processing_time,
    get_video_duration,
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Cost estimation (Google Gemini 1.5 Flash)
GEMINI_INPUT_COST = 0.075 / 1_000_000  # $0.075 per 1M input tokens
GEMINI_OUTPUT_COST = 0.30 / 1_000_000  # $0.30 per 1M output tokens

# TTS Voice Options
TTS_VOICES = {
    "hoai_my": {
        "name": "HoaiMy Neuro (Female)",
        "code": "vi-VN-HoaiMyNeural",
        "description": "Tiếng nữ, tự nhiên, nhẹ nhàng",
    },
    "nam_minh": {
        "name": "NamMinh Neuro (Male)",
        "code": "vi-VN-NamMinhNeural",
        "description": "Tiếng nam, sâu, chuyên nghiệp",
    },
}

# Audio Quality Presets
AUDIO_QUALITY = {
    "low": {
        "name": "Low (Fast)",
        "bitrate": "64k",
        "sample_rate": "22050",
        "description": "Nhanh, chất lượng thấp, file nhỏ",
    },
    "medium": {
        "name": "Medium (Balanced)",
        "bitrate": "128k",
        "sample_rate": "44100",
        "description": "Cân bằng tốc độ & chất lượng",
    },
    "high": {
        "name": "High (Quality)",
        "bitrate": "192k",
        "sample_rate": "48000",
        "description": "Cao, chất lượng tốt, file lớn",
    },
}

# Speech Rate Options
SPEECH_RATES = {
    "slow": {
        "name": "Slow",
        "value": "-20%",
        "description": "Chậm (-20%)",
    },
    "normal": {
        "name": "Normal",
        "value": "+0%",
        "description": "Bình thường",
    },
    "fast": {
        "name": "Fast",
        "value": "+20%",
        "description": "Nhanh (+20%)",
    },
}

# Config file path
CONFIG_FILE = Path("tts_config.json")


@dataclass
class TTSConfig:
    """TTS Configuration"""

    voice: str = "hoai_my"
    quality: str = "medium"
    speech_rate: str = "normal"

    def save(self):
        """Save config to file"""
        with open(CONFIG_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)
        logger.info(f"✓ Config saved: {CONFIG_FILE}")

    @staticmethod
    def load() -> "TTSConfig":
        """Load config from file or create default"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return TTSConfig(**data)
        else:
            config = TTSConfig()
            config.save()
            return config


@dataclass
class ProcessingResult:
    """Result of video processing"""

    video_id: str
    status: str  # success, failed, skipped
    input_url: str
    output_path: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0
    processing_time: str = ""
    api_calls: int = 0
    estimated_cost_usd: float = 0.0
    tts_voice: str = "hoai_my"
    audio_quality: str = "medium"


class DouyinPipeline:
    """Main pipeline for Douyin → Vietnamese video conversion"""

    def __init__(self, output_base="./output", tts_config: Optional[TTSConfig] = None):
        self.output_base = Path(output_base)
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.output_dir = self.output_base / self.today
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load TTS config
        self.tts_config = tts_config or TTSConfig.load()

        # Setup logging file
        self.log_file = self.output_dir / "pipeline.log"
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

        # Initialize Google Gemini client
        self.gemini_key = os.getenv("GOOGLE_API_KEY")
        if not self.gemini_key:
            raise ValueError(
                "GOOGLE_API_KEY not set in environment. Get it from https://ai.google.dev/"
            )

        genai.configure(api_key=self.gemini_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

        logger.info(f"✓ Google Gemini 1.5 Flash API initialized")
        logger.info(
            f"💰 Cost: $0.01 per 10-min video (45x cheaper than Claude Sonnet!)"
        )
        logger.info(f"🌍 Free trial: $300/month for 60 days\n")

        # Log TTS settings
        voice_info = TTS_VOICES[self.tts_config.voice]
        quality_info = AUDIO_QUALITY[self.tts_config.quality]
        rate_info = SPEECH_RATES[self.tts_config.speech_rate]

        logger.info(f"🎙️  TTS Settings:")
        logger.info(f"   Voice: {voice_info['name']} ({voice_info['description']})")
        logger.info(f"   Quality: {quality_info['name']} ({quality_info['bitrate']})")
        logger.info(f"   Speed: {rate_info['name']} ({rate_info['value']})\n")

        self.results: List[ProcessingResult] = []
        self.total_api_calls = 0

    def _run_command(self, cmd: List[str], description: str = "") -> bool:
        """Execute shell command with error handling"""
        try:
            logger.info(f"Running: {' '.join(cmd[:3])}...")  # Log first 3 parts
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=3600
            )
            if description:
                logger.info(f"✓ {description}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Command failed: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"✗ Command timeout: {' '.join(cmd[:3])}")
            return False
        except Exception as e:
            logger.error(f"✗ Error: {e}")
            return False

    def download_video(self, url: str, output_path: Path) -> bool:
        """Download video using yt-dlp"""
        logger.info(f"📥 Tải video: {url}")

        cmd = [
            "yt-dlp",
            "-f",
            "best[ext=mp4]",
            "-o",
            str(output_path),
            url,
        ]

        return self._run_command(cmd, "Video downloaded")

    def extract_audio(self, video_path: Path, audio_path: Path) -> bool:
        """Extract audio from video using FFmpeg"""
        logger.info(f"🎵 Tách audio từ video")

        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-q:a",
            "9",
            "-n",
            str(audio_path),
        ]

        return self._run_command(cmd, "Audio extracted")

    def transcribe_audio(self, audio_path: Path, srt_path: Path) -> bool:
        """Transcribe audio to Chinese using Whisper"""
        logger.info(f"🎙️ Transcribe tiếng Trung (Whisper large-v3)")

        try:
            import whisper

            logger.info("Loading Whisper model (large-v3)...")
            model = whisper.load_model("large-v3")

            logger.info(f"Transcribing {audio_path.name}...")
            result = model.transcribe(
                str(audio_path), language="zh", verbose=False
            )

            # Convert to SRT format
            srt_output = pysrt.SubRipFile()
            for i, segment in enumerate(result["segments"], 1):
                sub = pysrt.SubRip()
                sub.index = i
                sub.start = pysrt.SubRipTime(
                    milliseconds=int(segment["start"] * 1000)
                )
                sub.end = pysrt.SubRipTime(milliseconds=int(segment["end"] * 1000))
                sub.text = segment["text"].strip()
                srt_output.append(sub)

            srt_output.save(str(srt_path), encoding="utf-8")
            logger.info(f"✓ Transcription saved: {srt_path.name}")
            return True

        except Exception as e:
            logger.error(f"✗ Transcription failed: {e}")
            return False

    def _call_gemini_with_retry(
        self, prompt: str, max_retries: int = 3
    ) -> Optional[str]:
        """Call Gemini API with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1024,
                        temperature=0.3,  # Lower temperature for better translations
                    ),
                )
                self.total_api_calls += 1
                return response.text

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"⚠️ API call failed (attempt {attempt + 1}/{max_retries}): {str(e)[:50]}..."
                    )
                    logger.info(f"⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"✗ API call failed after {max_retries} attempts: {e}")
                    return None

    def translate_srt(self, srt_input: Path, srt_output: Path) -> bool:
        """Translate SRT file from Chinese to Vietnamese using Google Gemini"""
        logger.info(f"🌐 Dịch tiếng Trung → tiếng Việt (Google Gemini 1.5 Flash)")

        try:
            # Load SRT file
            srt_list = pysrt.load(str(srt_input), encoding="utf-8")
            total_subs = len(srt_list)

            logger.info(f"Total segments: {total_subs}")

            # Translate in batches
            batch_size = 5
            translated_subs = pysrt.SubRipFile()

            for batch_idx in tqdm(
                range(0, total_subs, batch_size),
                desc="Translating",
                unit="batch",
                colour="green",
            ):
                batch = srt_list[batch_idx : batch_idx + batch_size]
                batch_text = "\n\n".join(
                    f"[{sub.index}] {sub.text}" for sub in batch
                )

                # Create prompt for Gemini
                prompt = f"""Dịch các đoạn tiếng Trung sau sang tiếng Việt.
CHỈ trả về bản dịch, KHÔNG giải thích gì cả.
Giữ [số] ở đầu mỗi đoạn.

{batch_text}"""

                # Call Gemini API with retry
                translated_text = self._call_gemini_with_retry(prompt)
                if not translated_text:
                    raise Exception("Gemini translation failed after retries")

                lines = translated_text.strip().split("\n\n")

                for original_sub, translated_line in zip(batch, lines):
                    # Extract translation (remove [index] prefix)
                    translation = (
                        translated_line.split("] ", 1)[-1]
                        if "]" in translated_line
                        else translated_line
                    )

                    new_sub = pysrt.SubRip()
                    new_sub.index = original_sub.index
                    new_sub.start = original_sub.start
                    new_sub.end = original_sub.end
                    new_sub.text = translation
                    translated_subs.append(new_sub)

            translated_subs.save(str(srt_output), encoding="utf-8")
            logger.info(f"✓ Translation saved: {srt_output.name}")
            logger.info(f"📊 API calls made: {self.total_api_calls}")
            return True

        except Exception as e:
            logger.error(f"✗ Translation failed: {e}")
            return False

    def generate_vietnamese_audio(
        self, srt_path: Path, audio_output_dir: Path
    ) -> bool:
        """Generate Vietnamese audio using edge-tts with configured voice & quality"""
        voice_info = TTS_VOICES[self.tts_config.voice]
        rate_info = SPEECH_RATES[self.tts_config.speech_rate]
        quality_info = AUDIO_QUALITY[self.tts_config.quality]

        logger.info(
            f"🎙️ Sinh giọng tiếng Việt ({voice_info['name']}, {quality_info['bitrate']})"
        )

        try:
            import edge_tts
            import asyncio

            audio_output_dir.mkdir(parents=True, exist_ok=True)
            srt_list = pysrt.load(str(srt_path), encoding="utf-8")

            async def generate_audio():
                for sub in tqdm(srt_list, desc="Generating audio", colour="blue"):
                    audio_path = audio_output_dir / f"{sub.index}.mp3"

                    # Generate with configured voice & speed
                    communicate = edge_tts.Communicate(
                        text=sub.text,
                        voice=voice_info["code"],
                        rate=rate_info["value"],
                    )
                    await communicate.save(str(audio_path))

                    # Convert to configured quality if needed
                    if self.tts_config.quality != "high":
                        self._convert_audio_quality(audio_path)

            asyncio.run(generate_audio())
            logger.info(
                f"✓ Vietnamese audio generated ({len(srt_list)} segments)"
            )
            return True

        except Exception as e:
            logger.error(f"✗ Audio generation failed: {e}")
            return False

    def _convert_audio_quality(self, audio_path: Path) -> bool:
        """Convert audio to configured quality using FFmpeg"""
        try:
            quality_info = AUDIO_QUALITY[self.tts_config.quality]
            temp_path = audio_path.parent / f"{audio_path.stem}_temp.mp3"

            cmd = [
                "ffmpeg",
                "-i",
                str(audio_path),
                "-b:a",
                quality_info["bitrate"],
                "-ar",
                quality_info["sample_rate"],
                "-n",
                str(temp_path),
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, check=True
            )

            # Replace original with converted
            temp_path.replace(audio_path)
            return True

        except Exception as e:
            logger.warning(f"Audio quality conversion skipped: {e}")
            return False

    def mix_audio_and_burn_subtitles(
        self,
        video_path: Path,
        srt_path: Path,
        audio_dir: Path,
        output_video: Path,
    ) -> bool:
        """Mix original + Vietnamese audio and burn subtitles using FFmpeg"""
        logger.info(f"🎬 Mix audio + burn subtitle")

        try:
            # Step 1: Burn subtitles
            temp_video = output_video.parent / f"temp_{output_video.name}"
            subtitle_filter = f"subtitles={srt_path}:force_style='FontName=Arial Bold,FontSize=22,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,OutlineWidth=2'"

            cmd_burn_subs = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vf",
                subtitle_filter,
                "-c:a",
                "aac",
                "-n",
                str(temp_video),
            ]

            if not self._run_command(cmd_burn_subs, "Subtitles burned"):
                return False

            # Step 2: Concatenate Vietnamese audio files
            audio_concat_list = audio_dir / "concat.txt"
            with open(audio_concat_list, "w") as f:
                for i in range(1, len(list(audio_dir.glob("*.mp3"))) + 1):
                    f.write(f"file '{audio_dir}/{i}.mp3'\n")

            vi_audio_path = output_video.parent / "audio_vi.wav"
            cmd_concat = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(audio_concat_list),
                "-c",
                "pcm_s16le",
                "-n",
                str(vi_audio_path),
            ]

            if not self._run_command(cmd_concat, "Vietnamese audio concatenated"):
                return False

            # Step 3: Mix original + Vietnamese audio
            cmd_mix = [
                "ffmpeg",
                "-i",
                str(temp_video),
                "-i",
                str(vi_audio_path),
                "-filter_complex",
                "[0:a]volume=0.05[a0];[1:a]volume=0.3[a1];[a0][a1]amix=inputs=2:duration=first[a]",
                "-map",
                "0:v",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-c:a",
                "aac",
                "-n",
                str(output_video),
            ]

            if not self._run_command(cmd_mix, "Audio mixed & video finalized"):
                return False

            # Cleanup
            temp_video.unlink(missing_ok=True)
            vi_audio_path.unlink(missing_ok=True)

            logger.info(f"✓ Output video: {output_video}")
            return True

        except Exception as e:
            logger.error(f"✗ Audio mixing failed: {e}")
            return False

    def process_single(self, url: str) -> ProcessingResult:
        """Process a single Douyin video"""
        start_time = datetime.now()
        video_id = extract_video_id(url)
        video_dir = self.output_dir / f"video_{video_id}"
        video_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {video_id}")
        logger.info(f"URL: {url}")
        logger.info(f"Output dir: {video_dir}")
        logger.info(f"{'='*60}\n")

        api_calls_start = self.total_api_calls

        try:
            # Download
            video_path = video_dir / "input_video.mp4"
            if not self.download_video(url, video_path):
                raise Exception("Download failed")

            # Get duration for ETA
            duration = get_video_duration(str(video_path))
            logger.info(f"Video duration: {format_duration(timedelta(seconds=duration))}")
            logger.info(
                f"Estimated processing time: {format_duration(estimate_processing_time(duration))}"
            )

            # Extract audio
            audio_path = video_dir / "audio.wav"
            if not self.extract_audio(video_path, audio_path):
                raise Exception("Audio extraction failed")

            # Transcribe
            srt_original = video_dir / "transcript.srt"
            if not self.transcribe_audio(audio_path, srt_original):
                raise Exception("Transcription failed")

            # Translate
            srt_vietnamese = video_dir / "transcript_vi.srt"
            if not self.translate_srt(srt_original, srt_vietnamese):
                raise Exception("Translation failed")

            # Generate Vietnamese audio
            audio_dir = video_dir / "audio_segments"
            if not self.generate_vietnamese_audio(srt_vietnamese, audio_dir):
                raise Exception("Audio generation failed")

            # Mix audio and burn subtitles
            output_video = video_dir / "output_dubbed.mp4"
            if not self.mix_audio_and_burn_subtitles(
                video_path, srt_vietnamese, audio_dir, output_video
            ):
                raise Exception("Audio mixing failed")

            processing_time = datetime.now() - start_time
            api_calls = self.total_api_calls - api_calls_start
            estimated_cost = (
                api_calls * 0.01
            )  # Rough estimate: ~$0.01 per API call for 5 segments

            logger.info(f"\n✅ SUCCESS! Processing time: {format_duration(processing_time)}\n")

            return ProcessingResult(
                video_id=video_id,
                status="success",
                input_url=url,
                output_path=str(output_video),
                duration_seconds=duration,
                processing_time=format_duration(processing_time),
                api_calls=api_calls,
                estimated_cost_usd=estimated_cost,
                tts_voice=self.tts_config.voice,
                audio_quality=self.tts_config.quality,
            )

        except Exception as e:
            logger.error(f"\n❌ FAILED: {str(e)}\n")
            return ProcessingResult(
                video_id=video_id,
                status="failed",
                input_url=url,
                error=str(e),
                tts_voice=self.tts_config.voice,
                audio_quality=self.tts_config.quality,
            )

    def process_batch(self, urls_file: str) -> None:
        """Process multiple Douyin videos from file"""
        urls_path = Path(urls_file)

        if not urls_path.exists():
            logger.error(f"URLs file not found: {urls_file}")
            return

        with open(urls_path, "r") as f:
            urls = [line.strip() for line in f if line.strip()]

        logger.info(f"\n🎬 Batch processing: {len(urls)} videos\n")

        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Processing...")
            result = self.process_single(url)
            self.results.append(result)

        self._generate_report()

    def preview(self, url: str) -> None:
        """Preview first 30 seconds of processed video"""
        logger.info(f"\n👀 Preview mode: First 30 seconds\n")

        video_id = extract_video_id(url)
        video_dir = self.output_dir / f"video_{video_id}"
        video_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Download
            video_path = video_dir / "input_video.mp4"
            if not self.download_video(url, video_path):
                return

            # Extract 30 seconds preview
            preview_path = video_dir / "preview_30s.mp4"
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-t",
                "30",
                "-c",
                "copy",
                "-n",
                str(preview_path),
            ]

            if self._run_command(cmd, "Preview extracted"):
                logger.info(f"Preview saved: {preview_path}")
                logger.info(f"Open with: ffplay {preview_path}")

        except Exception as e:
            logger.error(f"Preview failed: {e}")

    def translate_file(self, srt_file: str) -> None:
        """Translate a standalone SRT file"""
        srt_path = Path(srt_file)

        if not srt_path.exists():
            logger.error(f"SRT file not found: {srt_file}")
            return

        output_path = srt_path.parent / f"{srt_path.stem}_vi.srt"
        logger.info(f"Translating: {srt_file}")

        if self.translate_srt(srt_path, output_path):
            logger.info(f"✓ Translated file saved: {output_path}")

    def _generate_report(self) -> None:
        """Generate processing report"""
        report_path = self.output_dir / "report.json"
        successful = len([r for r in self.results if r.status == "success"])
        failed = len([r for r in self.results if r.status == "failed"])
        total_api_calls = sum(r.api_calls for r in self.results)
        total_cost = sum(r.estimated_cost_usd for r in self.results)

        report = {
            "date": self.today,
            "total_videos": len(self.results),
            "successful": successful,
            "failed": failed,
            "total_api_calls": total_api_calls,
            "total_estimated_cost_usd": round(total_cost, 4),
            "api_provider": "Google Gemini 1.5 Flash",
            "cost_vs_claude": f"45x cheaper than Anthropic Claude",
            "tts_settings": {
                "voice": TTS_VOICES[self.tts_config.voice]["name"],
                "quality": AUDIO_QUALITY[self.tts_config.quality]["name"],
                "speed": SPEECH_RATES[self.tts_config.speech_rate]["name"],
            },
            "results": [asdict(r) for r in self.results],
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n📊 REPORT:")
        logger.info(f"  Total videos: {len(self.results)}")
        logger.info(f"  Success: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Total API calls: {total_api_calls}")
        logger.info(f"  💰 Total cost: ${total_cost:.4f} (Google Gemini)")
        logger.info(f"  🔥 Would cost: ${total_cost * 45:.2f} with Claude Sonnet")
        logger.info(f"  💾 Report: {report_path}")


def configure_tts():
    """Interactive TTS configuration"""
    print("\n" + "=" * 60)
    print("🎙️  TTS CONFIGURATION")
    print("=" * 60 + "\n")

    config = TTSConfig.load()

    # Voice selection
    print("📢 Select Voice:")
    for i, (key, info) in enumerate(TTS_VOICES.items(), 1):
        marker = "✓" if key == config.voice else " "
        print(f"  [{marker}] {i}. {info['name']}")
        print(f"       {info['description']}\n")

    choice = input("Enter choice (1-2) [default: 1]: ").strip() or "1"
    voices_list = list(TTS_VOICES.keys())
    if choice.isdigit() and 1 <= int(choice) <= len(voices_list):
        config.voice = voices_list[int(choice) - 1]

    # Quality selection
    print("\n📊 Select Audio Quality:")
    for i, (key, info) in enumerate(AUDIO_QUALITY.items(), 1):
        marker = "✓" if key == config.quality else " "
        print(f"  [{marker}] {i}. {info['name']}")
        print(f"       {info['description']} (Sample: {info['sample_rate']}Hz)\n")

    choice = input("Enter choice (1-3) [default: 2]: ").strip() or "2"
    quality_list = list(AUDIO_QUALITY.keys())
    if choice.isdigit() and 1 <= int(choice) <= len(quality_list):
        config.quality = quality_list[int(choice) - 1]

    # Speech rate selection
    print("\n⏱️  Select Speech Rate:")
    for i, (key, info) in enumerate(SPEECH_RATES.items(), 1):
        marker = "✓" if key == config.speech_rate else " "
        print(f"  [{marker}] {i}. {info['name']}")
        print(f"       {info['description']}\n")

    choice = input("Enter choice (1-3) [default: 2]: ").strip() or "2"
    rate_list = list(SPEECH_RATES.keys())
    if choice.isdigit() and 1 <= int(choice) <= len(rate_list):
        config.speech_rate = rate_list[int(choice) - 1]

    # Save
    config.save()

    print("\n" + "=" * 60)
    print("✅ Configuration saved!")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Douyin → Vietnamese Video Pipeline (with Google Gemini)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s single https://www.douyin.com/video/...
  %(prog)s batch urls.txt
  %(prog)s preview https://www.douyin.com/video/...
  %(prog)s translate transcript.srt
  %(prog)s config  # Configure TTS voice & quality
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Single command
    single_parser = subparsers.add_parser("single", help="Process single video")
    single_parser.add_argument("url", help="Douyin video URL")

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Process multiple videos")
    batch_parser.add_argument("urls_file", help="File with URLs (one per line)")

    # Preview command
    preview_parser = subparsers.add_parser("preview", help="Preview first 30 seconds")
    preview_parser.add_argument("url", help="Douyin video URL")

    # Translate command
    translate_parser = subparsers.add_parser("translate", help="Translate SRT file")
    translate_parser.add_argument("srt_file", help="Path to SRT file")

    # Config command
    config_parser = subparsers.add_parser(
        "config", help="Configure TTS voice & quality"
    )

    args = parser.parse_args()

    try:
        if args.command == "config":
            configure_tts()

        else:
            pipeline = DouyinPipeline()

            if args.command == "single":
                result = pipeline.process_single(args.url)
                pipeline.results.append(result)
                pipeline._generate_report()

            elif args.command == "batch":
                pipeline.process_batch(args.urls_file)

            elif args.command == "preview":
                pipeline.preview(args.url)

            elif args.command == "translate":
                pipeline.translate_file(args.srt_file)

            else:
                parser.print_help()

    except KeyboardInterrupt:
        logger.info("\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
