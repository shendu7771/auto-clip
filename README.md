# 永在湾 自动切片工具

🐟 鱼写的第一个产品。

## 功能

- 输入直播回放视频 → 自动切成短视频片段
- 基于音频检测找高光时刻
- 可选时长、数量、阈值

## 用法

```bash
# 基本用法
python3 auto_clip/clip.py 直播回放.mp4

# 自定义参数
python3 auto_clip/clip.py 直播回放.mp4 \
  --min-duration 15 \
  --max-duration 45 \
  --max-clips 10 \
  --output-dir ./我的切片

# 查看帮助
python3 auto_clip/clip.py --help
```

## 需要

- Python 3.8+
- ffmpeg（已装，imageio-ffmpeg）

## 下一步计划

- [ ] 音频高潮检测（用 loudness 找带货主播喊"上车"的时刻）
- [ ] 自动加字幕（whisper/openai-whisper-api）
- [ ] 自动加水印/logo
- [ ] 批量处理多个视频
- [ ] 定时任务——每天自动跑

---

CEO: 任礼益 | CTO: cc 🐟 | 永在湾
