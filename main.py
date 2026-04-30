#!/usr/bin/env python3
"""
Douyin → Vietnamese Video Pipeline
Automatically convert Douyin videos to Vietnamese dubbed version with subtitles

Usage:
    python main.py single <url>
    python main.py batch <urls_file>
    python main.py preview <url>
    python main.py translate <srt_file>
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import anthropic
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


class DouyinPipeline:
    """Main pipeline for Douyin → Vietnamese video conversion"""

    def __init__(self, output_base="./output"):
        self.output_base = Path(output_base)
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.output_dir = self.output_base / self.today
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging file
        self.log_file = self.output_dir / "pipeline.log"
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

        # Initialize Anthropic client
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        self.client = anthropic.Anthropic(api_key=self.anthropic_key)

        self.results: List[ProcessingResult] = []

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

    def translate_srt(self, srt_input: Path, srt_output: Path) -> bool:
        """Translate SRT file from Chinese to Vietnamese using Claude"""
        logger.info(f"🌐 Dịch tiếng Trung → tiếng Việt (Claude 3.5 Sonnet)")

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

                # Call Claude API
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    messages=[
                        {
                            "role": "user",
                            "content": f"""Dịch các đoạn tiếng Trung sau sang tiếng Việt.
CHỈ trả về bản dịch, KHÔNG giải thích gì cả.
Giữ [số] ở đầu mỗi đoạn.

{batch_text}""",
                        }
                    ],
                ):
                    pass

                translated_text = response.content[0].text
                lines = translated_text.strip().split("\n\n")

                for original_sub, translated_line in zip(batch, lines):
                    # Extract translation (remove [index] prefix)
                    translation = translated_line.split("] ", 1)[-1] if "]" in translated_line else translated_line

                    new_sub = pysrt.SubRip()
                    new_sub.index = original_sub.index
                    new_sub.start = original_sub.start
                    new_sub.end = original_sub.end
                    new_sub.text = translation
                    translated_subs.append(new_sub)

            translated_subs.save(str(srt_output), encoding="utf-8")
            logger.info(f"✓ Translation saved: {srt_output.name}")
            return True

        except Exception as e:
            logger.error(f"✗ Translation failed: {e}")
            return False

    def generate_vietnamese_audio(
        self, srt_path: Path, audio_output_dir: Path
    ) -> bool:
        """Generate Vietnamese audio using edge-tts"""
        logger.info(f"🎙️ Sinh giọng tiếng Việt (edge-tts HoaiMyNeural)")

        try:
            import edge_tts
            import asyncio

            audio_output_dir.mkdir(parents=True, exist_ok=True)
            srt_list = pysrt.load(str(srt_path), encoding="utf-8")

            async def generate_audio():
                for sub in tqdm(srt_list, desc="Generating audio", colour="blue"):
                    audio_path = audio_output_dir / f"{sub.index}.mp3"

                    communicate = edge_tts.Communicate(
                        text=sub.text,
                        voice="vi-VN-HoaiMyNeural",
                        rate="+0%",
                    )
                    await communicate.save(str(audio_path))

            asyncio.run(generate_audio())
            logger.info(f"✓ Vietnamese audio generated")
            return True

        except Exception as e:
            logger.error(f"✗ Audio generation failed: {e}")
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
            # Step 1: Create fontconfig file for subtitle styling
            fontconfig_file = Path("/tmp/fontconfig.txt")
            fontconfig_file.write_text(
                """FontName=Arial Bold
FontSize=22
FontColor=&HFFFFFF&
OutlineColor=&H000000&
OutlineWidth=2
BackColour=&H000000&
BackAlpha=128
"""
            )

            # Step 2: Burn subtitles
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

            # Step 3: Concatenate Vietnamese audio files
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

            # Step 4: Mix original + Vietnamese audio
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
            logger.info(f"\n✅ SUCCESS! Processing time: {format_duration(processing_time)}\n")

            return ProcessingResult(
                video_id=video_id,
                status="success",
                input_url=url,
                output_path=str(output_video),
                duration_seconds=duration,
                processing_time=format_duration(processing_time),
            )

        except Exception as e:
            logger.error(f"\n❌ FAILED: {str(e)}\n")
            return ProcessingResult(
                video_id=video_id,
                status="failed",
                input_url=url,
                error=str(e),
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

        report = {
            "date": self.today,
            "total_videos": len(self.results),
            "successful": successful,
            "failed": failed,
            "results": [asdict(r) for r in self.results],
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n📊 REPORT:")
        logger.info(f"  Total: {len(self.results)}")
        logger.info(f"  Success: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Report: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Douyin → Vietnamese Video Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s single https://www.douyin.com/video/...
  %(prog)s batch urls.txt
  %(prog)s preview https://www.douyin.com/video/...
  %(prog)s translate transcript.srt
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

    args = parser.parse_args()

    try:
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
