# AI Novel to Video

将小说/故事通过 waoowaoo 自动转换为带角色配音的漫画视频 MP4 文件。

## 六阶段工作流

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

## 项目结构

```
ai-novel-video/
├── CLAUDE.md            # 项目说明
├── README.md            # 使用文档
├── .env.example         # 配置示例文件
├── src/
│   ├── novel_to_video.py    # 主入口，六阶段流程封装
│   ├── prompt_cache.py      # 长文本分段工具
│   └── test/
│       └── mock_server.py   # Mock 服务
├── output/              # 产出目录（视频输出）
├── docker-compose.yml   # waoowaoo 服务配置
└── skills.json         # Skill 注册配置
```

## 技术栈

- **waoowaoo** - 开源全流程AI影视制作平台 (localhost:13000)
  - 镜像: `docker.cnb.cool/fuliai/waoowaoo/app:latest`
  - 依赖: MySQL 8.0, Redis 7, MinIO (RELEASE.2025-02-28)
- **Python 3.10+** + requests
- **ffmpeg** - 视频合并
- **edge-tts** - 角色配音参考音频生成
- **输出格式** - 9:16 竖版 MP4，时间戳命名

## API Key 配置

waoowaoo 需要配置以下 API Key：
- **火山引擎 ARK** - 画图 + 视频生成（seedream + seedance）
- **火山引擎 ARK** - 分析故事（Doubao-Seed-2.0）
- **阿里云百炼** - 配音（Qwen3 TTS、Qwen Voice Design、VideoRetalk Lip Sync）

## 快速开始

```bash
# 配置文件
cp .env.example .env
# 编辑 .env 填入 WAOOWAOO_EMAIL、WAOOWAOO_PASSWORD
# 以及 ARK_API_KEY、BAILIAN_API_KEY

# 运行
python src/novel_to_video.py "一段小说文本..."

# 本地测试（无需 waoowaoo 服务）
python src/novel_to_video.py --mock "一段小说文本..."
```

## API 模式

| 模式 | 说明 |
|------|------|
| `mock_mode=False` | 连接真实 waoowaoo 服务（需要 Docker + 认证） |
| `mock_mode=True` | 使用模拟 API，适合开发测试 |

## 认证方式

1. `.env` 配置文件（推荐）
2. 命令行 `--login EMAIL PASSWORD`
3. 环境变量 `WAOOWAOO_EMAIL` / `WAOOWAOO_PASSWORD`

认证信息保存至 `/tmp/waoowaoo_auth.txt`
会话ID保存至 `/tmp/waoowaoo_session.env`

## 输出

- 输出目录: `output/`
- 文件命名: `{YYYYMMDD_HHMMSS}.mp4`

## 程序调用

```python
from src.novel_to_video import run_novel_to_video

# 真实服务模式
result = run_novel_to_video("小说文本...")

# 测试模式
result = run_novel_to_video("小说文本...", mock_mode=True)
```
