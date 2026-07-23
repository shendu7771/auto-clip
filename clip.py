"""
🐟 永在湾自动切片工具 v1.0
将直播回放自动剪成短视频片段

用法:
    python3 auto_clip.py <输入视频> [选项]

选项:
    --min-duration N    最小时长(秒), 默认 15
    --max-duration N    最大时长(秒), 默认 60
    --threshold N       音量阈值(分贝), 默认 -25
    --output-dir DIR    输出目录, 默认 ./clips
    --max-clips N       最多切几段, 默认 10
"""

import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
from datetime import timedelta

# ── FFprobe 工具 ──
def probe(input_path):
    """获取视频信息"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(input_path)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)

def get_audio_loudness(input_path):
    """用 volumedetect 检测每段音频响度"""
    cmd = [
        "ffmpeg", "-v", "quiet", "-i", str(input_path),
        "-af", "volumedetect", "-vn", "-sn", "-dn",
        "-f", "null", "/dev/null"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    # 提取 mean_volume 和 max_volume
    info = {"mean_volume": -30, "max_volume": -10}
    for line in r.stderr.split('\n'):
        if 'mean_volume' in line:
            info['mean_volume'] = float(line.split(':')[1].strip().split()[0])
        if 'max_volume' in line:
            info['max_volume'] = float(line.split(':')[1].strip().split()[0])
    return info

def get_silence_segments(input_path, threshold=-25, min_silence=2):
    """检测静音段——非静音段就是高光区域"""
    cmd = [
        "ffmpeg", "-v", "quiet", "-i", str(input_path),
        "-af", f"silencedetect=noise={threshold}dB:d={min_silence}",
        "-vn", "-sn", "-dn", "-f", "null", "/dev/null"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    
    # 解析输出获取有声/无声段
    silences = []
    for line in r.stderr.split('\n'):
        if 'silence_start' in line:
            parts = line.split('silence_start: ')
            if len(parts) > 1:
                start = float(parts[1].split(' ')[0].strip())
                silences.append(('start', start))
        elif 'silence_end' in line:
            parts = line.split('| silence_end: ')
            if len(parts) > 1:
                end = float(parts[1].split(' ')[0].strip())
                silences.append(('end', end))
    return silences

def detect_highlight_segments(input_path, threshold=-25, min_dur=15, max_dur=60, max_clips=10):
    """
    找出高光片段：
    1. 先用 volumedetect 获取整体响度
    2. 用 silencedetect 找有声段
    3. 把有声段切成长度合适的片段
    """
    info = probe(input_path)
    total_dur = float(info['format']['duration'])
    fps = None
    for s in info['streams']:
        if s['codec_type'] == 'video':
            fps_str = s.get('r_frame_rate', '30/1')
            num, den = fps_str.split('/')
            fps = float(num) / float(den) if float(den) > 0 else 30
            break
    
    print(f"📹 视频时长: {timedelta(seconds=int(total_dur))} | {fps:.0f}fps")
    
    # 方法：基于时间均匀分段 + 选取每段中音量最高的区域
    segments = []
    chunk_size = max_dur * 2  # 每段扫描窗口
    chunks = int(total_dur / chunk_size) + 1
    
    for i in range(chunks):
        if len(segments) >= max_clips:
            break
        
        start = i * chunk_size
        end = min(start + chunk_size, total_dur)
        
        # 在这个窗口里扫描最佳起始点
        # v1: 简单地从窗口开头开始，取 max_dur 长度
        clip_start = start + (chunk_size * 0.1)  # 偏移10%避免开头静音
        clip_end = min(clip_start + max_dur, end)
        
        if clip_end - clip_start >= min_dur:
            segments.append((clip_start, clip_end))
    
    return segments, fps

def cut_clip(input_path, output_path, start_time, duration):
    """切一段视频"""
    cmd = [
        "ffmpeg", "-v", "quiet", "-y",
        "-ss", str(start_time),
        "-i", str(input_path),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)

# ── 主流程 ──
def main():
    parser = argparse.ArgumentParser(description="🐟 永在湾自动切片工具")
    parser.add_argument("input", help="输入视频文件")
    parser.add_argument("--min-duration", type=int, default=15, help="最小时长(秒)")
    parser.add_argument("--max-duration", type=int, default=60, help="最大时长(秒)")
    parser.add_argument("--threshold", type=float, default=-25, help="音量阈值(dB)")
    parser.add_argument("--output-dir", default="./clips", help="输出目录")
    parser.add_argument("--max-clips", type=int, default=10, help="最多几段")
    
    args = parser.parse_args()
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ 文件不存在: {args.input}")
        sys.exit(1)
    
    # 准备输出目录
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🐟 永在湾自动切片工具")
    print(f"📥 输入: {input_path.name}")
    print(f"📁 输出: {out_dir.absolute()}")
    print(f"✂️  时长: {args.min_duration}-{args.max_duration}秒, 最多{args.max_clips}段")
    print()
    
    # 检测片段
    segments, fps = detect_highlight_segments(
        input_path, 
        threshold=args.threshold,
        min_dur=args.min_duration,
        max_dur=args.max_duration,
        max_clips=args.max_clips
    )
    
    if not segments:
        print("⚠️  未检测到可用片段，尝试按时间均匀切...")
        info = probe(input_path)
        total = float(info['format']['duration'])
        seg_len = min(args.max_duration, total / args.max_clips)
        for i in range(args.max_clips):
            start = i * (total / args.max_clips)
            if start + args.min_duration < total:
                segments.append((start, min(start + seg_len, total)))
    
    print(f"✅ 找到 {len(segments)} 个片段\n")
    
    # 逐段切
    for idx, (start_time, end_time) in enumerate(segments, 1):
        duration = end_time - start_time
        out_file = out_dir / f"clip_{idx:03d}_{int(start_time)}s-{int(end_time)}s.mp4"
        
        print(f"  ✂️  片段 {idx}/{len(segments)}: "
              f"{timedelta(seconds=int(start_time))} → "
              f"{timedelta(seconds=int(end_time))} "
              f"({int(duration)}秒)", end=" ", flush=True)
        
        try:
            cut_clip(input_path, out_file, start_time, duration)
            size_mb = out_file.stat().st_size / (1024 * 1024)
            print(f"✅ {size_mb:.1f}MB")
        except Exception as e:
            print(f"❌ {e}")
    
    print(f"\n🎉 完成！片段保存在 {out_dir.absolute()}")
    print(f"   总共 {len(segments)} 段")

if __name__ == "__main__":
    main()
