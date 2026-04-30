# 🎬 Douyin → Vietnamese Video Pipeline

Tự động hoá pipeline: tải video Douyin → nhận diện tiếng Trung → dịch VI → lồng tiếng + sub → xuất video hoàn chỉnh.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![Status Active](https://img.shields.io/badge/status-active-success)

## ✨ Features

✅ **Tự động tải video** từ Douyin (dùng yt-dlp)  
✅ **Nhận diện tiếng Trung** (Whisper large-v3)  
✅ **Dịch sang tiếng Việt** (Claude 3.5 Sonnet)  
✅ **Sinh giọng VI** (edge-tts HoaiMyNeural)  
✅ **Lồng tiếng + subtitle** (FFmpeg)  
✅ **Batch mode** xử lý hàng loạt  
✅ **Progress bar** chi tiết  
✅ **JSON report** khi hoàn thành  

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Caoboi1/douyin-vi-pipeline.git
cd douyin-vi-pipeline
```

### 2. Install Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg python3.10 pip

# macOS
brew install ffmpeg python@3.10
```

### 3. Setup Python Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 4. Install Python Packages
```bash
pip install -r requirements.txt
```

### 5. Configure API Key
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
# Get key from: https://console.anthropic.com/
```

### 6. Run Pipeline
```bash
# Single video
python main.py single "https://www.douyin.com/video/..."

# Batch mode
python main.py batch urls.txt

# Preview 30 seconds
python main.py preview "https://www.douyin.com/video/..."
```

## 📖 Usage Guide

### Single Video Processing
```bash
python main.py single "https://www.douyin.com/video/7123456789012345678"
```

**Output**:
```
output/2026-04-30/video_7123456789012345678/
├── input_video.mp4
├── audio.wav
├── transcript.srt (Chinese)
├── transcript_vi.srt (Vietnamese)
├── audio_segments/
│   ├── 1.mp3
│   ├── 2.mp3
│   └── ...
└── output_dubbed.mp4 ✅
```

### Batch Processing
```bash
# Create urls.txt
cat > urls.txt << EOF
https://www.douyin.com/video/7123456789012345678
https://www.douyin.com/video/7123456789012345679
https://www.douyin.com/video/7123456789012345680
EOF

# Process all
python main.py batch urls.txt
```

### Preview Mode
```bash
python main.py preview "https://www.douyin.com/video/..."
# Extracts first 30 seconds to preview
```

### Translate SRT File
```bash
python main.py translate transcript.srt
# Output: transcript_vi.srt
```

## ⚙️ Configuration

### .env File
```bash
# Required: Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Optional: Custom output directory
# OUTPUT_BASE_DIR=./output

# Optional: Tool paths (if not in system PATH)
# FFMPEG_PATH=/usr/bin/ffmpeg
# YT_DLP_PATH=/usr/local/bin/yt-dlp
```

### Subtitle Styling
Edit `main.py` function `mix_audio_and_burn_subtitles()`:
```python
subtitle_filter = f"subtitles={srt_path}:force_style='FontName=Arial Bold,FontSize=22,...'"
```

### Audio Levels
```python
# In mix_audio_and_burn_subtitles():
# Original audio: -20dB (background)
# Dubbed audio: -3dB (main)
"-filter_complex",
"[0:a]volume=0.05[a0];[1:a]volume=0.3[a1];[a0][a1]amix=inputs=2:duration=first[a]"
```

## 📊 Output Report

**report.json** example:
```json
{
  "date": "2026-04-30",
  "total_videos": 3,
  "successful": 2,
  "failed": 1,
  "results": [
    {
      "video_id": "7123456789012345678",
      "status": "success",
      "input_url": "https://www.douyin.com/video/...",
      "output_path": "./output/2026-04-30/video_7123456789012345678/output_dubbed.mp4",
      "duration_seconds": 120.5,
      "processing_time": "12m 34s"
    }
  ]
}
```

## 🔧 Troubleshooting

### ❌ FFmpeg not found
```bash
# Verify installation
ffmpeg -version
ffprobe -version

# Install if missing
sudo apt-get install ffmpeg  # Linux
brew install ffmpeg           # macOS
```

### ❌ ANTHROPIC_API_KEY error
```bash
# Check .env file exists
ls -la .env

# Verify key format
grep ANTHROPIC_API_KEY .env
# Should output: ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### ❌ Whisper model download stuck
```bash
# The model downloads on first run (~2.9GB)
# Manually test:
python3 << 'EOF'
import whisper
model = whisper.load_model('large-v3')
print("✓ Model loaded successfully")
EOF
```

### ❌ Out of memory
```bash
# Process shorter videos first
# Or increase swap space:
sudo fallocate -l 10G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### ❌ Rate limit error (429)
```
# Anthropic API rate limited
# Wait a few minutes before retrying
# Check usage at: https://console.anthropic.com/usage
```

## 📈 Performance Tips

1. **Batch Processing**: Process multiple videos at once
   ```bash
   python main.py batch urls.txt
   ```

2. **GPU Acceleration**: Use CUDA for Whisper (if available)
   ```bash
   # Install CUDA-enabled torch
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

3. **Parallel Processing**: Run multiple instances
   ```bash
   python main.py single "url1" &
   python main.py single "url2" &
   python main.py single "url3" &
   wait
   ```

## 💰 Cost Estimation

**Claude 3.5 Sonnet Pricing** (per 1M tokens):
- Input: $3
- Output: $15

**Per 10-minute video**:
- Transcription: ~50,000 tokens
- Translation: ~20,000 tokens
- **Total Cost**: ~$0.25-0.50

## 📝 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4GB | 8GB+ |
| Storage | 10GB | 50GB+ |
| Python | 3.10 | 3.11+ |
| FFmpeg | Latest | Latest |

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see LICENSE file

## ⚠️ Disclaimer

- Use only for **legal purposes** and **with permission**
- Do NOT use for copyright-protected content without authorization
- Creator is not responsible for misuse
- Check local laws regarding video processing

## 📞 Support & Issues

- **Bug Report**: Create GitHub issue
- **Feature Request**: Create GitHub discussion
- **Documentation**: See `CLAUDE.md`
- **Logs**: Check `output/YYYY-MM-DD/pipeline.log`

## 🙏 Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video downloader
- [Whisper](https://github.com/openai/whisper) - Speech recognition
- [Claude](https://www.anthropic.com/claude) - Translation API
- [edge-tts](https://github.com/rany2/edge-tts) - Text-to-speech
- [FFmpeg](https://ffmpeg.org/) - Audio/video processing

---

**Made with ❤️ by Caoboi1**

GitHub: https://github.com/Caoboi1
