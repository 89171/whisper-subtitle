# Subtitle Maker

[中文](README_zh.md)

AI-powered subtitle and lyric generation for audio and video files using OpenAI Whisper.

## What it does

Drop in an audio or video file — get a perfectly timed **LRC** lyrics file for music, or **SRT** subtitle file for videos. Provide your own lyric text for best accuracy, or let Whisper transcribe everything from scratch.

## Features

| Feature | Detail |
|---------|--------|
| **Video → SRT subtitles** | MP4/MKV/MOV/WebM/AVI etc. — auto-extracts audio, outputs standard SRT |
| **Audio → LRC lyrics** | MP3 → Whisper ASR → timestamped LRC for music players |
| **Lyric alignment** | Supply a `.txt` lyrics file — DTW + pinyin similarity aligns text to audio precisely |
| **Vocal separation** | `--separate` runs demucs to isolate vocals before recognition |
| **Batch processing** | Process entire folders of mixed audio/video files at once |
| **Chinese optimized** | pinyin-based alignment, FunASR fallback, `--language zh` hint |
| **Auto-install** | Missing dependencies (demucs, funasr) install automatically on first use |
| **MCP integration** | Call via AI assistants with the built-in MCP server |
| **Playground** | `playground/index.html` — load video+SRT or audio+LRC, play, edit timestamps & text inline, add/delete lines, drag-and-drop, export |

## Quick Start

```bash
pip install openai-whisper torch mcp pypinyin
brew install ffmpeg      # macOS; or apt install ffmpeg on Linux
```

### Audio (LRC lyrics)

```bash
python subtitle_maker.py song.mp3                        # pure ASR
python subtitle_maker.py song.mp3 lyrics.txt              # with aligned lyrics
python subtitle_maker.py song.mp3 lyrics.txt --language zh  # Chinese
```

### Video (SRT subtitles)

```bash
python subtitle_maker.py video.mp4 -f srt                  # pure ASR subtitles
python subtitle_maker.py video.mp4 lyrics.txt -f srt       # aligned subtitles
python subtitle_maker.py video.mp4 -f srt --separate       # vocal isolation first
```

### Advanced

```bash
python subtitle_maker.py video.mp4 -f srt --separate --save-vocals  # keep vocal track
python subtitle_maker.py /path/to/files --batch -f srt              # batch SRT
python subtitle_maker.py /path/to/files --batch -f lrc              # batch LRC
```

## Supported Formats

| Type | Input | Output |
|------|-------|--------|
| Audio | `.mp3` | `.lrc` / `.srt` |
| Video | `.mp4` `.mkv` `.webm` `.mov` `.avi` `.flv` `.wmv` `.m4v` `.ts` | `.srt` / `.lrc` |

### Output examples

**LRC** — enhanced with end timestamps for karaoke-style display:
```
[ti:Moonlight]
[ar:Artist Name]
[00:12.50]<00:18.30>First line of lyrics
[00:18.30]<00:24.00>Second line of lyrics
```

**SRT** — for video players (VLC, IINA, mpv, etc.):
```
1
00:00:12,500 --> 00:00:18,300
First line of subtitles

2
00:00:18,300 --> 00:00:24,000
Second line of subtitles
```

## Playground

Open `playground/index.html` in a browser — no server needed. Features:

- **Drag & drop** or click to load media and subtitle files
- **Video mode**: video playback with subtitle overlay
- **Audio mode**: waveform animation + large lyric display (previous / current / next)
- **Editable table**: inline edit start time, end time, and text (double-click)
- **Toolbar**: add above/below, delete line, set current playback time as timestamp
- **Export** to LRC or SRT (auto-detected from loaded format)
- **Keyboard**: Space play/pause, ← → seek 5s, ↑ ↓ prev/next line, Enter edit, T set time, Delete remove

## CLI Options

```
python subtitle_maker.py <input> [lyrics] [output] [options]
```

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `<input>` | path | *required* | Media file or directory (with `--batch`) |
| `[lyrics]` | path | — | Lyric text file, one line per sentence |
| `[output]` | path | `<input>.lrc` or `.srt` | Output file path |
| `-f, --format` | `lrc` / `srt` | `lrc` | Output format |
| `-l, --language` | `auto` / `zh` / `en` | `auto` | Language hint for Whisper |
| `-s, --separate` | flag | — | Vocal separation with demucs |
| `--save-vocals` | flag | — | Save isolated vocals as `<file>.vocals.wav` |
| `-b, --batch` | flag | — | Process entire directory |
| `-o, --output-dir` | path | same as input | Batch output directory |
| `--whisper-model` | tiny~turbo | `large-v3` | Whisper model size |
| `-t, --title` | string | — | Song title (LRC metadata) |
| `-a, --artist` | string | — | Artist name (LRC metadata) |
| `-al, --album` | string | — | Album name (LRC metadata) |
| `-v, --verbose` | flag | — | Verbose logging |

## Pipeline

```
Media file ──→ [video?] extract audio via ffmpeg
            ──→ [--separate?] demucs vocal isolation
            ──→ 16kHz mono WAV → Whisper ASR
            ──→ [lyrics?] DTW + pinyin alignment
            ──→ write .lrc or .srt
```

## MCP Server

Add `mcp_config.json` to your AI client to enable the `generate_subtitle` tool.

| Parameter | Type | Description |
|-----------|------|-------------|
| `media_path` | string | Media file path (required) |
| `lyrics_path` | string | Optional lyric file path |
| `output_path` | string | Output file path |
| `model_size` | string | Whisper model: `tiny` ~ `turbo` |
| `format` | string | `lrc` or `srt` |
| `language` | string | `auto` / `zh` / `en` |
| `separate` | boolean | Vocal separation with demucs |
| `save_vocals` | boolean | Save vocal track |
| `title` / `artist` / `album` | string | LRC metadata |

## Project Structure

```
├── subtitle_maker.py       # Core engine
├── mcp_server.py           # MCP server
├── mcp_config.json         # MCP client config
├── playground/index.html   # Playground (video/audio + subtitle with editing)
└── requirements.txt
```

## License

MIT
