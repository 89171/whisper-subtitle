#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import whisper


LYRIC_TAGS = [
    r'\[Intro\]', r'\[Verse\]', r'\[Verse\s*\d*\]', r'\[Chorus\]', r'\[Bridge\]',
    r'\[Pre-Chorus\]', r'\[Post-Chorus\]', r'\[Hook\]', r'\[Outro\]',
    r'\[Instrumental\]', r'\[Interlude\]', r'\[Solo\]', r'\[Break\]',
    r'\[Ending\]', r'\[Rap\]', r'\[Spoken\]', r'\[Ad-lib\]', r'\[Vocal\]',
    r'\[Pre-?Verse\]', r'\[Vocal\s*Break\]', r'\[Melodic\s*Break\]',
    r'\[Guitar\]', r'\[Synth\]', r'\[Drums\]', r'\[Bass\]',
    r'\[Bridge\s*#?\d*\]', r'\[Hook\s*#?\d*\]',
]


def is_lyric_tag(line: str) -> bool:
    line = line.strip()
    for tag in LYRIC_TAGS:
        if re.match(tag, line, re.IGNORECASE):
            return True
    return False


def filter_lyrics(lines: list[str]) -> list[str]:
    return [line for line in lines if line.strip() and not is_lyric_tag(line)]


def timestamp_to_lrc_format(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"[{minutes:02d}:{secs:05.2f}]"


def text_similarity(s1: str, s2: str) -> float:
    s1_clean = re.sub(r'[^\w\s]', '', s1.lower()).replace(' ', '')
    s2_clean = re.sub(r'[^\w\s]', '', s2.lower()).replace(' ', '')

    if not s1_clean or not s2_clean:
        return 0.0

    if s1_clean == s2_clean:
        return 1.0

    chars1 = list(s1_clean)
    chars2 = list(s2_clean)
    len1, len2 = len(chars1), len(chars2)

    matched = 0
    used = [False] * len2

    for c1 in chars1:
        best_ratio = 0
        best_idx = -1
        for i, c2 in enumerate(chars2):
            if used[i]:
                continue
            if c1 == c2:
                matched += 1
                used[i] = True
                break
            else:
                ratio = char_similarity(c1, c2)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = i
        if best_idx >= 0 and matched == 0 and best_ratio > 0.8:
            matched += 1
            used[best_idx] = True

    return matched / max(len1, len2)


def char_similarity(c1: str, c2: str) -> float:
    if c1 == c2:
        return 1.0
    if is_similar_char(c1, c2):
        return 0.9
    return 0.0


def is_similar_char(c1: str, c2: str) -> bool:
    similar_groups = [
        {'捎', '卷', '扫'},
        {'踏', '他', '它', '她'},
        {'月', '日', '目'},
        {'来', '未', '末'},
        {'的', '得', '地'},
        {'在', '再'},
        {'有', '又'},
        {'会', '惠'},
        {'爱', '艾'},
        {'心', '新', '辛'},
        {'风', '丰'},
        {'归', '轨'},
        {'期', '其', '奇'},
    ]
    for group in similar_groups:
        if c1 in group and c2 in group:
            return True
    return False


def align_lyrics_with_timestamps(lyrics: list[str], segments: list[dict]) -> list[tuple[str, float]]:
    if not lyrics or not segments:
        return []

    result = []
    seg_idx = 0
    lyric_times = [None] * len(lyrics)

    for i, lyric in enumerate(lyrics):
        best_score = 0
        best_seg_idx = -1

        for j in range(seg_idx, min(seg_idx + 10, len(segments))):
            score = text_similarity(segments[j]['text'].strip(), lyric)
            if score > best_score:
                best_score = score
                best_seg_idx = j

        if best_score >= 0.5 and best_seg_idx >= 0:
            lyric_times[i] = segments[best_seg_idx]['start']
            seg_idx = best_seg_idx + 1
        elif i > 0 and lyric_times[i - 1] is not None:
            lyric_times[i] = lyric_times[i - 1]
        elif seg_idx < len(segments):
            lyric_times[i] = segments[seg_idx]['start']
        else:
            lyric_times[i] = segments[-1]['end']

    for i, (lyric, timestamp) in enumerate(zip(lyrics, lyric_times)):
        if timestamp is None:
            timestamp = segments[-1]['end'] if segments else 0.0
        result.append((lyric, timestamp))

    return result


def convert_mp3_to_wav(mp3_path: str, output_path: str = None) -> str:
    if output_path is None:
        output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name

    cmd = [
        'ffmpeg', '-y', '-i', mp3_path,
        '-ar', '16000',
        '-ac', '1',
        '-c:a', 'pcm_s16le',
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def generate_lrc(mp3_path: str, lyrics_path: str = None, output_path: str = None, model_size: str = 'base') -> str:
    mp3_path = Path(mp3_path)
    if output_path is None:
        output_path = mp3_path.with_suffix('.lrc')
    else:
        output_path = Path(output_path)

    wav_path = convert_mp3_to_wav(str(mp3_path))

    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(wav_path, word_timestamps=True)

        lyrics = []
        if lyrics_path:
            with open(lyrics_path, 'r', encoding='utf-8') as f:
                content = f.read()
                content = content.replace('\\n', '\n')
                lyrics = [line.strip() for line in content.split('\n')]
            lyrics = filter_lyrics(lyrics)

        if lyrics:
            aligned = align_lyrics_with_timestamps(lyrics, result['segments'])
        else:
            aligned = [(seg['text'].strip(), seg['start']) for seg in result['segments'] if seg['text'].strip()]

        with open(output_path, 'w', encoding='utf-8') as f:
            for text, timestamp in aligned:
                lrc_line = timestamp_to_lrc_format(timestamp) + text
                f.write(lrc_line + '\n')

        return str(output_path)
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


def main():
    parser = argparse.ArgumentParser(description='使用 Whisper AI 将 MP3 音频转换为 LRC 歌词文件')
    parser.add_argument('mp3_file', help='输入的 MP3 音频文件')
    parser.add_argument('lyrics_file', nargs='?', default=None, help='歌词文本文件（每行一句）')
    parser.add_argument('output_file', nargs='?', default=None, help='生成的 LRC 文件路径')
    parser.add_argument('model_size', nargs='?', default='large', choices=['base', 'small', 'medium', 'large'], help='Whisper 模型大小')

    args = parser.parse_args()

    try:
        output_path = generate_lrc(
            args.mp3_file,
            args.lyrics_file,
            args.output_file,
            args.model_size
        )
        print(f"LRC 文件已生成: {output_path}")
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()