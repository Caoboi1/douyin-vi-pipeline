# Project: Douyin → Vietnamese Video Pipeline

## 📋 Context
Tự động hoá pipeline: tải video Douyin → nhận diện tiếng Trung → dịch VI → lồng tiếng + sub → xuất video hoàn chỉnh.

## 🔄 Workflow

```
Douyin URL
    ↓
yt-dlp → Tải video .mp4
    ↓
FFmpeg → Tách audio .wav
    ↓
Whisper large-v3 → .srt tiếng Trung + timestamps
    ↓
Claude 3.5 Sonnet → Dịch VI (giữ timing)
    ↓
edge-tts vi-VN-HoaiMyNeural → Audio VI
    ↓
FFmpeg → Burn sub + mix audio → Output .mp4 ✅
```

## ⚙️ Technical Specifications

### Video Processing
- **Source**: Douyin videos (TikTok China)
- **Download**: `yt-dlp` (best[ext=mp4])
- **Format**: MP4 container

### Audio/Speech
- **Transcription**: Whisper large-v3 (Chinese)
- **Subtitle Timing**: Original SRT timestamps preserved
- **Vietnamese Voice**: edge-tts `vi-VN-HoaiMyNeural`
- **Audio Mixing**:
  - Dubbed Vietnamese: **-3dB** (main)
  - Original Chinese: **-20dB** (background)

### Subtitle Rendering
- **Font**: Arial Bold
- **Size**: 22px
- **Color**: White (#FFFFFF)
- **Outline**: Black with 2px width
- **Background**: Black with 50% transparency
- **Encoding**: UTF-8

### Translation Engine
- **Model**: Claude 3.5 Sonnet
- **Batch Size**: 5 segments per API call
- **Preservation**: Timestamps and line breaks maintained

### Output Structure
```
output/
└── YYYY-MM-DD/
    ├── video_<video_id>/
    │   ├── input_video.mp4          (Original)
    │   ├── audio.wav                (Extracted)
    │   ├── transcript.srt           (Chinese)
    │   ├── transcript_vi.srt        (Vietnamese)
    │   ├── audio_segments/
    │   │   ├── 1.mp3
    │   │   ├── 2.mp3
    │   │   └── ...
    │   └── output_dubbed.mp4        (Final ✅)
    ├── pipeline.log
    └── report.json
```

## 🎯 Commands

### Single Video
```bash
python main.py single "https://www.douyin.com/video/..."
```

### Batch Processing
```bash
python main.py batch urls.txt
```
File format (urls.txt):
```
https://www.douyin.com/video/...
https://www.douyin.com/video/...
```

### Preview (30 seconds)
```bash
python main.py preview "https://www.douyin.com/video/..."
```

### Translate SRT File
```bash
python main.py translate transcript.srt
```
Output: `transcript_vi.srt`

## 📦 Installation

### 1. System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg python3.10 pip

# macOS
brew install ffmpeg python@3.10

# Windows
# Download from: https://ffmpeg.org/download.html
```

### 2. Python Environment
```bash
cd douyin-vi-pipeline
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup API Key
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## 🔐 API Configuration

### Anthropic API
1. Get API key: https://console.anthropic.com/
2. Create `.env` file:
```bash
cp .env.example .env
echo "ANTHROPIC_API_KEY=sk-ant-your-key" >> .env
```

### Cost Estimation
- **Claude 3.5 Sonnet**: $3/$15 per 1M tokens (input/output)
- Per video (10 min):
  - Transcription: ~50,000 tokens
  - Translation: ~20,000 tokens
  - **Total**: ~$0.25-0.50 per video

## 📊 Progress & Logging

### Terminal Output
```
2026-04-30 10:30:45 - INFO - Processing: 7123456789012345678
2026-04-30 10:30:45 - INFO - 📥 Tải video: https://www.douyin.com/video/...
2026-04-30 10:31:02 - INFO - ✓ Video downloaded
2026-04-30 10:31:02 - INFO - 🎵 Tách audio từ video
2026-04-30 10:31:05 - INFO - ✓ Audio extracted
[Transcribing...] 45%|████▌     | 45/100 [00:23<00:28, 1.94s/it]
[Translating...] 100%|██████████| 20/20 [00:45<00:00, 2.25s/batch]
[Generating audio...] 100%|██████████| 100/100 [02:30<00:00, 1.50s/segment]
2026-04-30 10:35:30 - INFO - ✓ Output video: ./output/2026-04-30/video_7123456789012345678/output_dubbed.mp4
2026-04-30 10:35:30 - INFO - ✅ SUCCESS! Processing time: 5m 2s
```

### Log Files
- `output/YYYY-MM-DD/pipeline.log` - Detailed step-by-step log
- `output/YYYY-MM-DD/report.json` - Summary report

## 🛠️ Troubleshooting

### FFmpeg Not Found
```bash
# Install FFmpeg
sudo apt-get install ffmpeg  # Linux
brew install ffmpeg           # macOS
```

### ANTHROPIC_API_KEY Not Set
```bash
# Verify .env file
cat .env
# Should see: ANTHROPIC_API_KEY=sk-ant-...
```

### Whisper Model Download Failed
```bash
# The model will auto-download (2.9GB) on first run
# If stuck, manually download:
python3 -c "import whisper; whisper.load_model('large-v3')"
```

### Out of Memory
For long videos (>30min), process in batches or increase swap:
```bash
# Increase virtual memory (Linux)
sudo fallocate -l 10G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 📈 Performance

| Operation | Duration (per 10min video) |
|-----------|---------------------------|
| Download | ~2-5 minutes |
| Audio Extract | ~30 seconds |
| Transcribe (Whisper) | ~5-10 minutes |
| Translate (Claude) | ~2-3 minutes |
| Generate Audio | ~3-4 minutes |
| Mix/Burn Subtitles | ~2-3 minutes |
| **Total** | **~15-30 minutes** |

## 📝 Rules & Standards

✅ **Always preserve**:
- Original timestamps when translating
- UTF-8 encoding for all text files
- Video resolution and aspect ratio
- Audio quality (AAC codec)

✅ **Quality Standards**:
- Subtitle timing accuracy: ±100ms
- Dubbed audio lip-sync: Best effort
- Translation fluency: Natural Vietnamese
- No hardcoded watermarks

❌ **Do NOT**:
- Modify video resolution
- Remove original audio completely
- Change subtitle encoding
- Process copyrighted content without permission

## 🚀 Example Workflow

```bash
# 1. Single video
python main.py single "https://www.douyin.com/video/7123456789012345678"

# 2. Check output
ls -la output/2026-04-30/video_7123456789012345678/

# 3. View final video
ffplay output/2026-04-30/video_7123456789012345678/output_dubbed.mp4

# 4. Check report
cat output/2026-04-30/report.json
```

## 📞 Support

- **Issues**: Check `pipeline.log` in output directory
- **API Errors**: Verify `ANTHROPIC_API_KEY` in `.env`
- **FFmpeg Errors**: Run `ffmpeg -version` to verify installation
- **Whisper Issues**: Check internet (for model download)

## 📅 Version History

- **v1.0** (2026-04-30): Initial release
  - Single video processing
  - Batch mode
  - Preview functionality
  - SRT file translation
  - Full subtitle + audio mixing

---

**Created**: 2026-04-30  
**Author**: Caoboi1  
**License**: MIT
