# 六阶段工作流

```
第一阶段：环境准备 ──── 检查 waoowaoo 服务 + 账号认证
         ↓
第二阶段：故事变分镜 ── 创建项目、写入故事、AI分析、生成片段、生成分镜
         ↓
第三阶段：分镜变画面和声音 ─ 生成漫画图 + 角色配音
         ↓
第四阶段：画面变完整视频 ─ 提交视频生成请求
         ↓
第五阶段：合并视频 ──── 下载所有视频片段并用 ffmpeg 合并
         ↓
第六阶段：下载至本地 ── 最终 MP4 输出到 output 目录
```


# 第一阶段：环境准备

## 1.1 部署 waoowaoo 到服务器
curl -fsSL https://cnb.cool/fuliai/waoowaoo/-/git/raw/main/install.sh | bash

## 1.2 API Key
 - 火山引擎 ARK（画图 + 做视频用的，seedream+seedance）
 - 火山引擎 ARK（分析故事用的，Doubao-Seed-2.0 ）
 - 火山引擎 ARK（配音用的,阿里云百炼,Qwen3 TTS、Qwen Voice Design、VideoRetalk Lip Sync）

## 1.3 在 waoowaoo 里配置 API Key
**把邮箱和密码换成你自己的**
、、、MY_EMAIL="你的邮箱"
MY_PASSWORD="你的密码"

rm -f /tmp/auth_cookies.txt
CSRF=$(curl -s -c /tmp/auth_cookies.txt http://localhost:13000/api/auth/csrf | python3 -c "import json,sys; print(json.load(sys.stdin)['csrfToken'])")
curl -s -c /tmp/auth_cookies.txt -b /tmp/auth_cookies.txt \
  -X POST http://localhost:13000/api/auth/callback/credentials \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "csrfToken=$CSRF&username=$MY_EMAIL&password=$MY_PASSWORD&callbackUrl=http%3A%2F%2Flocalhost%3A13000" > /dev/null
echo "✅ 登录完成"

**把两个 Key 换成你自己的**
、、、curl -s -b /tmp/auth_cookies.txt \
  -X PUT http://localhost:13000/api/user/api-config \
  -H "Content-Type: application/json" \
  -d '{
    "providers": [
      {"id": "ark", "name": "火山引擎 Ark", "apiKey": "你的ARK_API_KEY"},
      {"id": "bailian", "name": "阿里云百炼", "apiKey": "你的BAILIAN_API_KEY"},
    ]
  }'
echo "✅ API Key 配置完成"

## 1.4 环境检查

、、、MY_EMAIL="admin"
MY_PASSWORD="123456"

rm -f /tmp/auth_cookies.txt
CSRF=$(curl -s -c /tmp/auth_cookies.txt http://localhost:13000/api/auth/csrf | python3 -c "import json,sys; print(json.load(sys.stdin)['csrfToken'])")
curl -s -c /tmp/auth_cookies.txt -b /tmp/auth_cookies.txt \
  -X POST http://localhost:13000/api/auth/callback/credentials \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "csrfToken=$CSRF&username=$MY_EMAIL&password=$MY_PASSWORD&callbackUrl=http%3A%2F%2Flocalhost%3A13000" > /dev/null
echo "✅ 登录完成"

# 第二阶段：故事变分镜
## 2.1 命令行登录
、、、MY_EMAIL="你的邮箱"
MY_PASSWORD="你的密码"

rm -f /tmp/auth_cookies.txt
CSRF=$(curl -s -c /tmp/auth_cookies.txt http://localhost:13000/api/auth/csrf | python3 -c "import json,sys; print(json.load(sys.stdin)['csrfToken'])")
curl -s -c /tmp/auth_cookies.txt -b /tmp/auth_cookies.txt \
  -X POST http://localhost:13000/api/auth/callback/credentials \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "csrfToken=$CSRF&username=$MY_EMAIL&password=$MY_PASSWORD&callbackUrl=http%3A%2F%2Flocalhost%3A13000" > /dev/null
echo "✅ 登录完成"

## 2.2 创建项目
、、、PROJECT=$(curl -s -b /tmp/auth_cookies.txt \
  -X POST http://localhost:13000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "AI漫剧_时间戳", "description": "漫剧创建"}')
PROJECT_ID=$(echo $PROJECT | python3 -c "import json,sys; print(json.load(sys.stdin)['project']['projectId'])")
echo "✅ 项目创建成功，ID = $PROJECT_ID"

**把 ID 保存到文件，防止终端断开后丢失**
echo "PROJECT_ID=$PROJECT_ID" > /tmp/waoowaoo_session.env

## 2.3 创建剧集并写入故事
、、、EP=$(curl -s -b /tmp/auth_cookies.txt \
  -X POST "http://localhost:13000/api/novel-promotion/$PROJECT_ID/episodes" \
  -H "Content-Type: application/json" \
  -d '{"name": "第一集"}')
EPISODE_ID=$(echo $EP | python3 -c "import json,sys; print(json.load(sys.stdin)['episode']['id'])")
echo "✅ 剧集创建成功，ID = $EPISODE_ID"

**保存 ID**
、、、echo "EPISODE_ID=$EPISODE_ID" >> /tmp/waoowaoo_session.env

echo input/chapter-001.txt

STORY_TEXT=$(cat input/chapter-001.txt)
curl -s -b /tmp/auth_cookies.txt \
  -X PATCH "http://localhost:13000/api/novel-promotion/$PROJECT_ID/episodes/$EPISODE_ID" \
  -H "Content-Type: application/json" \
  -d "{\"novelText\": $(python3 -c "import json; print(json.dumps(open('input/chapter-001.txt').read()))")}" > /dev/null
echo "✅ 故事写入成功"


## 2.4 让 AI 分析故事
、、、echo "⏳ AI 正在分析你的故事..."
TASK=$(curl -s -b /tmp/auth_cookies.txt \
  -X POST "http://localhost:13000/api/novel-promotion/$PROJECT_ID/analyze-global" \
  -H "Content-Type: application/json" \
  -d "{\"episodeId\": \"$EPISODE_ID\", \"locale\": \"zh\"}")
TASK_ID=$(echo $TASK | python3 -c "import json,sys; print(json.load(sys.stdin).get('taskId','?'))")

**自动等待完成（最多等 3 分钟）**
、、、for i in $(seq 1 36); do
  sleep 5
  STATUS=$(curl -s -b /tmp/auth_cookies.txt "http://localhost:13000/api/tasks/$TASK_ID" | python3 -c "import json,sys; print(json.load(sys.stdin).get('task',{}).get('status',''))")
  if [ "$STATUS" = "completed" ]; then echo "✅ 故事分析完成！"; break; fi
  if [ "$STATUS" = "failed" ]; then echo "❌ 分析失败，请检查 Google API Key 是否配置正确，以及服务器是否能访问 Google"; break; fi
  echo "  等待中... ($i/36) 状态: $STATUS"
done

## 2.5 生成片段
、、、echo "⏳ 正在切分故事片段..."
CLIP_RESULT=$(curl -s -b /tmp/auth_cookies.txt \
  -X POST "http://localhost:13000/api/novel-promotion/$PROJECT_ID/clips" \
  -H "Content-Type: application/json" \
  -d "{\"episodeId\": \"$EPISODE_ID\", \"locale\": \"zh\"}")

**等待并确认片段生成完成**
、、、for i in $(seq 1 12); do
  sleep 5
  CLIP_COUNT=$(curl -s -b /tmp/auth_cookies.txt \
    "http://localhost:13000/api/novel-promotion/$PROJECT_ID/episodes/$EPISODE_ID" | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('episode',{}).get('clips',[])))" 2>/dev/null)
  if [ "$CLIP_COUNT" != "0" ] && [ -n "$CLIP_COUNT" ]; then
    echo "✅ 片段生成完成，共 $CLIP_COUNT 个片段"
    break
  fi
  echo "  等待中... ($i/12)"
done

## 2.6 生成分镜
、、、echo "⏳ 正在生成分镜（约 2 分钟）..."
TASK=$(curl -s -b /tmp/auth_cookies.txt \
  -X POST "http://localhost:13000/api/novel-promotion/$PROJECT_ID/script-to-storyboard-stream" \
  -H "Content-Type: application/json" \
  -d "{\"episodeId\": \"$EPISODE_ID\", \"locale\": \"zh\"}")
TASK_ID=$(echo $TASK | python3 -c "import json,sys; print(json.load(sys.stdin).get('taskId','?'))")

for i in $(seq 1 36); do
  sleep 5
  STATUS=$(curl -s -b /tmp/auth_cookies.txt "http://localhost:13000/api/tasks/$TASK_ID" | python3 -c "import json,sys; print(json.load(sys.stdin).get('task',{}).get('status',''))")
  if [ "$STATUS" = "completed" ]; then echo "✅ 分镜生成完成！"; break; fi
  if [ "$STATUS" = "failed" ]; then echo "❌ 分镜生成失败，请重新运行本步骤"; break; fi
  echo "  等待中... ($i/36) 状态: $STATUS"
done

# 第三阶段：分镜变画面和声音
## 3.1 生成所有图片
、、、echo "⏳ 正在生成图片..."

cat > /tmp/submit_panels.py << 'PYEOF'
import json, subprocess, sys, time

PROJECT_ID = sys.argv[1]
EPISODE_ID = sys.argv[2]

d = json.loads(subprocess.check_output([
    "curl", "-s", "-b", "/tmp/auth_cookies.txt",
    f"http://localhost:13000/api/novel-promotion/{PROJECT_ID}/episodes/{EPISODE_ID}"
]).decode())

panels = []
for sb in d.get("episode", {}).get("storyboards", []):
    for p in sb.get("panels", []):
        if not p.get("imageUrl"):
            panels.append(p["id"])

if not panels:
    print("所有图片已生成，无需重复操作")
    sys.exit(0)

print(f"共 {len(panels)} 张图片需要生成")
for i, pid in enumerate(panels):
    r = json.loads(subprocess.check_output([
        "curl", "-s", "-b", "/tmp/auth_cookies.txt",
        "-X", "POST", f"http://localhost:13000/api/novel-promotion/{PROJECT_ID}/regenerate-panel-image",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"panelId": pid, "locale": "zh", "count": 1})
    ]).decode())
    print(f"  [{i+1}/{len(panels)}] 已提交")
    time.sleep(0.3)

print("全部提交完毕，等待 AI 画图中...")
PYEOF

python3 /tmp/submit_panels.py $PROJECT_ID $EPISODE_ID

**生成进度检查**
、、、
echo "⏳ 等待图片生成（每 15 秒检查一次）..."
for i in $(seq 1 20); do
  sleep 15
  RESULT=$(curl -s -b /tmp/auth_cookies.txt \
    "http://localhost:13000/api/novel-promotion/$PROJECT_ID/episodes/$EPISODE_ID" | \
    python3 -c "
import json,sys
d = json.load(sys.stdin)
panels = [p for sb in d['episode']['storyboards'] for p in sb['panels']]
done = sum(1 for p in panels if p.get('imageUrl'))
print(f'{done}/{len(panels)}')
if done == len(panels): sys.exit(0)
else: sys.exit(1)
")
  echo "  图片进度: $RESULT ($i/20)"
  if [ $? -eq 0 ]; then echo "✅ 所有图片生成完成！"; break; fi
done

## 3.2配置角色配音
、、、
### 第一步：准备参考音频**
pip install edge-tts -q 2>/dev/null

**生成一个少年男声（给男性角色用）**
edge-tts --voice zh-CN-YunxiNeural --text "你好，我是这个故事里的角色，我的声音听起来是这样的" \
  --write-media /tmp/voice_male.mp3

**生成一个活泼女声（给女性角色用）**
edge-tts --voice zh-CN-XiaoxiaoNeural --text "你好，我是这个故事里的角色，我的声音听起来是这样的" \
  --write-media /tmp/voice_female.mp3

echo "✅ 参考音频生成完成"

**上传到 MinIO 存储（waoowaoo 的文件服务）**
docker cp /tmp/voice_male.mp3 waoowaoo-minio:/data/uploads/voice_male.mp3 2>/dev/null || \
  cp /tmp/voice_male.mp3 /opt/waoowaoo/data/uploads/voice_male.mp3

docker cp /tmp/voice_female.mp3 waoowaoo-minio:/data/uploads/voice_female.mp3 2>/dev/null || \
  cp /tmp/voice_female.mp3 /opt/waoowaoo/data/uploads/voice_female.mp3

echo "✅ 音频已上传"

### 第二步：看看你的故事里有哪些角色**
、、、echo "=== 你的故事里有这些角色 ==="
curl -s -b /tmp/auth_cookies.txt \
  "http://localhost:13000/api/novel-promotion/$PROJECT_ID/episodes/$EPISODE_ID" | \
  python3 -c "
import json,sys
d = json.load(sys.stdin)
vl = d.get('episode',{}).get('voiceLines',[])
speakers = sorted(set(v.get('speaker','') for v in vl))
for s in speakers:
    count = sum(1 for v in vl if v.get('speaker')==s)
    print(f'  {s}（{count}句台词）')
"

### 第三步：设置每个角色用哪个声音
、、、cat > /tmp/setup_voices.py << 'PYEOF'
import json, subprocess, sys

PROJECT_ID = sys.argv[1]
EPISODE_ID = sys.argv[2]


**在这里修改角色和声音的对应关系 "角色名": "voice_male.mp3" 或 "voice_female.mp3"**
VOICE_MAP = {
    "阿金": "voice_male.mp3",
    "小松鼠": "voice_female.mp3",
    "旁白": "voice_male.mp3",
}

speaker_voices = {}
for name, audio_file in VOICE_MAP.items():
    speaker_voices[name] = {
        "voiceType": "uploaded",
        "audioUrl": f"http://localhost:13000/api/files/{audio_file}"
    }

**通过 API 更新**
data = json.dumps({"speakerVoices": speaker_voices})
result = subprocess.check_output([
    "curl", "-s", "-b", "/tmp/auth_cookies.txt",
    "-X", "PATCH",
    f"http://localhost:13000/api/novel-promotion/{PROJECT_ID}/episodes/{EPISODE_ID}",
    "-H", "Content-Type: application/json",
    "-d", data
]).decode()

print("✅ 角色声音设置完成")
for name, audio in VOICE_MAP.items():
    print(f"  {name} → {audio}")
PYEOF

python3 /tmp/setup_voices.py $PROJECT_ID $EPISODE_ID

### 第四步：分析配音
、、、echo "⏳ 正在分析配音..."
curl -s -b /tmp/auth_cookies.txt \
  -X POST "http://localhost:13000/api/novel-promotion/$PROJECT_ID/voice-analyze" \
  -H "Content-Type: application/json" \
  -d "{\"episodeId\": \"$EPISODE_ID\", \"locale\": \"zh\"}" > /dev/null

for i in $(seq 1 12); do
  sleep 5
  echo "  等待中... ($i/12)"
done
echo "✅ 配音分析完成"


### 第五步：生成所有配音**
echo "⏳ 开始生成配音..."
RESULT=$(curl -s -b /tmp/auth_cookies.txt \
  -X POST "http://localhost:13000/api/novel-promotion/$PROJECT_ID/voice-generate" \
  -H "Content-Type: application/json" \
  -d "{\"episodeId\": \"$EPISODE_ID\", \"locale\": \"zh\", \"all\": true, \"audioModel\": \"fal::fal-ai/index-tts-2/text-to-speech\"}")
TOTAL=$(echo $RESULT | python3 -c "import json,sys; print(json.load(sys.stdin).get('total',0))")
echo "已提交 $TOTAL 条台词，等待生成..."

**按台词数量动态计算等待时间（每条约 15 秒）**
WAIT=$((TOTAL * 15 + 60))
echo "预计需要 $((WAIT / 60)) 分钟"
for i in $(seq 1 $((WAIT / 10))); do
  sleep 10
  echo "  等待中... ($((i * 10))/${WAIT}秒)"
done
echo "✅ 配音应该已完成"

# 第四阶段：画面变完整视频
## 4.1 生成视频片段
、、、echo "⏳ 正在提交视频生成请求..."
RESULT=$(curl -s -b /tmp/auth_cookies.txt \
  -X POST "http://localhost:13000/api/novel-promotion/$PROJECT_ID/generate-video" \
  -H "Content-Type: application/json" \
  -d "{
    \"episodeId\": \"$EPISODE_ID\",
    \"locale\": \"zh\",
    \"all\": true,
    \"videoModel\": \"ark::doubao-seedance-1-5-pro-251215\",
    \"generationOptions\": {
      \"generateAudio\": false,
      \"duration\": 4,
      \"resolution\": \"720p\"
    }
  }")
TOTAL=$(echo $RESULT | python3 -c "import json,sys; print(json.load(sys.stdin).get('total',0))")
echo "✅ 已提交 $TOTAL 段视频生成请求"
echo ""
echo "⏰ 预计需要 60 分钟，你可以："
echo "   - 去喝杯咖啡"
echo "   - 想想下一个要做什么故事"
echo "   - 或者就放着，等会儿回来查看"


**查看进度**
curl -s -b /tmp/auth_cookies.txt \
  "http://localhost:13000/api/novel-promotion/$PROJECT_ID/episodes/$EPISODE_ID" | \
  python3 -c "
import json,sys
d = json.load(sys.stdin)
panels = [p for sb in d['episode']['storyboards'] for p in sb['panels']]
done = sum(1 for p in panels if p.get('videoUrl'))
total = len(panels)
pct = int(done/total*100) if total else 0
print(f'视频进度: {done}/{total} ({pct}%)')
if done >= total * 0.9:
    print('✅ 已完成 90% 以上，可以进行下一步了')
elif done == total:
    print('✅ 全部完成！')
else:
    print(f'还需要等待，预计还剩 {(total-done)*2} 分钟')
"

## 4.2 下载并合并成最终视频
、、、
echo "⏳ 正在下载所有视频片段..."

cat > /tmp/download_and_merge.py << 'PYEOF'
import json, subprocess, os, sys

PROJECT_ID = sys.argv[1]
EPISODE_ID = sys.argv[2]

**1.取所有分镜数据**
d = json.loads(subprocess.check_output([
    "curl", "-s", "-b", "/tmp/auth_cookies.txt",
    f"http://localhost:13000/api/novel-promotion/{PROJECT_ID}/episodes/{EPISODE_ID}"
]).decode())

**2.收集有视频的 panel**
panels = []
for sb in d.get("episode", {}).get("storyboards", []):
    for p in sb.get("panels", []):
        if p.get("videoUrl"):
            panels.append(p)

os.makedirs("/tmp/panels", exist_ok=True)
lines = []
skipped = 0

for i, p in enumerate(panels):
    url = "http://localhost:13000" + p["videoUrl"]
    fname = f"/tmp/panels/{i:03d}.mp4"
    subprocess.run(["curl", "-s", "-b", "/tmp/auth_cookies.txt", url, "-o", fname],
                   capture_output=True)
    size = os.path.getsize(fname) if os.path.exists(fname) else 0
    if size > 1000:
        lines.append(f"file '{fname}'")
        print(f"  [{i+1}/{len(panels)}] ✅ 下载完成 ({size//1024}KB)")
    else:
        skipped += 1
        print(f"  [{i+1}/{len(panels)}] ⚠️ 跳过（文件太小，可能还没生成完）")

**3.写入 ffmpeg 合并列表**
with open("/tmp/filelist.txt", "w") as f:
    f.write("\n".join(lines))

print(f"\n共下载 {len(lines)} 段视频" + (f"，跳过 {skipped} 段" if skipped else ""))
PYEOF

python3 /tmp/download_and_merge.py $PROJECT_ID $EPISODE_ID


# 第五阶段：合并成一个完整视频
、、、echo "⏳ 正在合并视频..."
ffmpeg -f concat -safe 0 -i /tmp/filelist.txt -c copy /tmp/final_video.mp4 -y 2>/dev/null

FILE_SIZE=$(du -h /tmp/final_video.mp4 | cut -f1)
echo "✅ 视频合并完成！文件大小: $FILE_SIZE"

# 第六阶段：视频下载至本地
、、、
cp /tmp/final_video.mp4 /opt/waoowaoo/data/uploads/ 2>/dev/null || \
  docker cp /tmp/final_video.mp4 waoowaoo-minio:/data/uploads/final_video.mp4

echo "✅ 用浏览器打开以下链接下载视频："
echo "http://你的服务器IP:13000/api/files/final_video.mp4"