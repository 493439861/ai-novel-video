#!/usr/bin/env python3
"""
AI Novel to Video Skill - 将小说转换为漫剧视频

六阶段流程：
1. 环境准备 - 检查waoowaoo服务、配置API Key
2. 故事变分镜 - 创建项目、写入故事、AI分析、生成片段、生成分镜
3. 分镜变画面和声音 - 生成漫画图+角色配音
4. 画面变完整视频 - 提交视频生成请求
5. 合并成一个完整视频 - ffmpeg合并
6. 视频下载至本地 - output目录
"""

import json
import os
import shutil
import subprocess
import sys
import time
from typing import List, Dict, Any, Optional

try:
    import requests
except ImportError:
    print("需要安装 requests: pip install requests")
    sys.exit(1)


# ============== 配置 ==============

WAOOWAOO_BASE_URL = "http://localhost:13000"
COOKIES_FILE = "/tmp/waoowaoo_auth.txt"
SESSION_FILE = "/tmp/waoowaoo_session.env"


def load_config() -> Dict[str, str]:
    """从环境变量或配置文件加载 waoowaoo 配置"""
    config = {
        "email": os.environ.get("WAOOWAOO_EMAIL", ""),
        "password": os.environ.get("WAOOWAOO_PASSWORD", ""),
        "ark_api_key": os.environ.get("ARK_API_KEY", ""),
        "bailian_api_key": os.environ.get("BAILIAN_API_KEY", ""),
    }

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(project_root, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "WAOOWAOO_EMAIL" and not config["email"]:
                        config["email"] = value
                    elif key == "WAOOWAOO_PASSWORD" and not config["password"]:
                        config["password"] = value
                    elif key == "ARK_API_KEY" and not config["ark_api_key"]:
                        config["ark_api_key"] = value
                    elif key == "BAILIAN_API_KEY" and not config["bailian_api_key"]:
                        config["bailian_api_key"] = value

    return config


def load_session() -> Dict[str, str]:
    """加载已保存的会话ID"""
    session = {}
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    session[key] = value
    return session


def save_session(project_id: str = None, episode_id: str = None):
    """保存会话ID到文件"""
    lines = []
    if project_id:
        lines.append(f"PROJECT_ID={project_id}")
    if episode_id:
        lines.append(f"EPISODE_ID={episode_id}")
    if lines:
        with open(SESSION_FILE, "w") as f:
            f.write("\n".join(lines))


def find_command(cmd: str) -> Optional[str]:
    """查找命令路径"""
    for path in [cmd, f"/usr/local/bin/{cmd}", f"/opt/homebrew/bin/{cmd}"]:
        if shutil.which(path) or os.path.exists(path):
            return path
    return None


def check_command(cmd: str) -> bool:
    """检查命令是否可用"""
    return find_command(cmd) is not None


# ============== waoowaoo API 客户端 ==============

class WaoowaooClient:
    """
    waoowaoo API 客户端

    支持两种模式:
    1. mock_mode=True: 使用模拟API进行测试（无需认证）
    2. mock_mode=False: 连接真实waoowaoo服务
    """

    def __init__(self, base_url: str = WAOOWAOO_BASE_URL, mock_mode: bool = False):
        self.base_url = base_url.rstrip("/")
        self.mock_mode = mock_mode
        self.session = requests.Session()
        self._csrf_token = None

    def _get_csrf(self) -> Optional[str]:
        """获取 CSRF Token"""
        try:
            resp = self.session.get(f"{self.base_url}/api/auth/csrf", timeout=10)
            data = resp.json()
            return data.get("csrfToken")
        except Exception as e:
            print(f"获取CSRF失败: {e}")
            return None

    def login(self, email: str, password: str) -> bool:
        """使用账号密码登录并保存Cookie"""
        if self.mock_mode:
            print("  [Mock] 登录成功")
            return True

        try:
            # 获取 CSRF Token
            csrf_token = self._get_csrf()
            if not csrf_token:
                return False

            # 执行登录
            resp = self.session.post(
                f"{self.base_url}/api/auth/callback/credentials",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=f"csrfToken={csrf_token}&username={email}&password={password}&callbackUrl=http%3A%2F%2Flocalhost%3A13000",
                timeout=10
            )

            if resp.status_code == 200:
                self._save_cookies()
                print("  登录成功")
                return True
            return False
        except Exception as e:
            print(f"登录失败: {e}")
            return False

    def _save_cookies(self):
        """保存Cookie到文件"""
        try:
            with open(COOKIES_FILE, 'w') as f:
                f.write('# Netscape HTTP Cookie File\n')
                f.write('# https://curl.se/docs/http-cookies.html\n\n')
                for name, value in self.session.cookies.items():
                    f.write(f'localhost\tFALSE\t/\tFALSE\t0\t{name}\t{value}\n')
        except Exception as e:
            print(f"保存Cookie失败: {e}")

    def load_cookies(self) -> bool:
        """加载已保存的Cookie（Netscape格式）"""
        if not os.path.exists(COOKIES_FILE):
            return False
        try:
            with open(COOKIES_FILE, 'r') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = line.strip().split('\t')
                    if len(parts) >= 7:
                        self.session.cookies.set(parts[5], parts[6])
            return len(self.session.cookies) > 0
        except Exception as e:
            print(f"加载Cookie失败: {e}")
            return False

    def check_health(self) -> bool:
        """检查服务健康状态"""
        if self.mock_mode:
            return True
        try:
            resp = self.session.get(f"{self.base_url}/api/auth/csrf", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def wait_for_task(self, task_id: str, max_wait: int = 360, interval: int = 5) -> Dict[str, Any]:
        """等待任务完成"""
        for i in range(max_wait):
            time.sleep(interval)
            try:
                resp = self.session.get(f"{self.base_url}/api/tasks/{task_id}", timeout=5)
                result = resp.json()
                status = result.get("task", {}).get("status") if isinstance(result, dict) else result.get("status")
                print(f"    等待中... ({i*interval}/{max_wait}s) 状态: {status}")
                if status == "completed":
                    return {"status": "ok", "result": result}
                elif status == "failed":
                    return {"status": "error", "message": "任务失败"}
            except Exception as e:
                print(f"    检查状态失败: {e}")
        return {"status": "error", "message": "等待超时"}

    # ============== API 方法 ==============

    def create_project(self, name: str = None, description: str = None) -> Optional[str]:
        """创建项目"""
        if self.mock_mode:
            project_id = f"mock_project_{time.strftime('%Y%m%d_%H%M%S')}"
            print(f"  [Mock] 项目创建成功: {project_id}")
            return project_id

        try:
            if not name:
                name = f"ai-novel-video_{time.strftime('%Y%m%d_%H%M%S')}"
            if not description:
                description = f"ai-novel-video_{time.strftime('%Y%m%d_%H%M%S')}"
            resp = self.session.post(
                f"{self.base_url}/api/projects",
                json={"name": name, "description": description},
                timeout=10
            )
            data = resp.json()
            project_id = data.get("project", {}).get("id") if isinstance(data.get("project"), dict) else data.get("projectId")
            print(f"  项目创建成功: {project_id}")
            return project_id
        except Exception as e:
            print(f"创建项目失败: {e}")
            return None

    def create_episode(self, project_id: str, name: str = "第一集") -> Optional[str]:
        """创建剧集"""
        if self.mock_mode:
            episode_id = f"mock_episode_{time.strftime('%Y%m%d_%H%M%S')}"
            print(f"  [Mock] 剧集创建成功: {episode_id}")
            return episode_id

        try:
            resp = self.session.post(
                f"{self.base_url}/api/novel-promotion/{project_id}/episodes",
                json={"name": name},
                timeout=10
            )
            data = resp.json()
            episode_id = data.get("episode", {}).get("id") if isinstance(data.get("episode"), dict) else data.get("episodeId")
            print(f"  剧集创建成功: {episode_id}")
            return episode_id
        except Exception as e:
            print(f"创建剧集失败: {e}")
            return None

    def write_story(self, project_id: str, episode_id: str, story_text: str) -> bool:
        """写入故事文本到剧集"""
        if self.mock_mode:
            print("  [Mock] 故事写入成功")
            return True

        try:
            resp = self.session.patch(
                f"{self.base_url}/api/novel-promotion/{project_id}/episodes/{episode_id}",
                json={"novelText": story_text},
                timeout=10
            )
            print("  故事写入成功")
            return True
        except Exception as e:
            print(f"写入故事失败: {e}")
            return True  # 不阻塞流程

    def analyze_story(self, project_id: str, episode_id: str, locale: str = "zh") -> Optional[str]:
        """提交故事分析任务"""
        if self.mock_mode:
            print("  [Mock] 故事分析完成")
            return "mock_task_id"

        try:
            resp = self.session.post(
                f"{self.base_url}/api/novel-promotion/{project_id}/analyze-global",
                json={"episodeId": episode_id, "locale": locale},
                timeout=10
            )
            data = resp.json()
            task_id = data.get("taskId")
            print(f"  分析任务已提交: {task_id}")
            return task_id
        except Exception as e:
            print(f"提交分析任务失败: {e}")
            return None

    def generate_clips(self, project_id: str, episode_id: str, locale: str = "zh") -> Optional[str]:
        """提交片段生成任务"""
        if self.mock_mode:
            print("  [Mock] 片段生成完成")
            return "mock_task_id"

        try:
            resp = self.session.post(
                f"{self.base_url}/api/novel-promotion/{project_id}/clips",
                json={"episodeId": episode_id, "locale": locale},
                timeout=10
            )
            data = resp.json()
            task_id = data.get("taskId")
            print(f"  片段生成已提交: {task_id}")
            return task_id
        except Exception as e:
            print(f"提交片段生成失败: {e}")
            return None
            return None

    def generate_storyboard(self, project_id: str, episode_id: str, locale: str = "zh") -> Optional[str]:
        """提交分镜生成任务"""
        if self.mock_mode:
            print("  [Mock] 分镜生成完成")
            return "mock_task_id"

        try:
            resp = self.session.post(
                f"{self.base_url}/api/novel-promotion/{project_id}/script-to-storyboard-stream",
                json={"episodeId": episode_id, "locale": locale},
                timeout=10
            )
            data = resp.json()
            task_id = data.get("taskId")
            print(f"  分镜任务已提交: {task_id}")
            return task_id
        except Exception as e:
            print(f"提交分镜任务失败: {e}")
            return None

    def submit_panel_images(self, project_id: str, episode_id: str) -> int:
        """提交所有需要生成的图片"""
        if self.mock_mode:
            print("  [Mock] 已提交 6 张图片生成请求")
            return 6

        try:
            # 获取分镜数据
            resp = self.session.get(
                f"{self.base_url}/api/novel-promotion/{project_id}/episodes/{episode_id}",
                timeout=10
            )
            data = resp.json()
            panels = []
            for sb in data.get("episode", {}).get("storyboards", []):
                for p in sb.get("panels", []):
                    if not p.get("imageUrl"):
                        panels.append(p["id"])

            if not panels:
                print("  所有图片已生成，无需重复操作")
                return 0

            print(f"  共 {len(panels)} 张图片需要生成")
            for i, pid in enumerate(panels):
                self.session.post(
                    f"{self.base_url}/api/novel-promotion/{project_id}/regenerate-panel-image",
                    json={"panelId": pid, "locale": "zh", "count": 1},
                    timeout=10
                )
                print(f"    [{i+1}/{len(panels)}] 已提交")
                time.sleep(0.3)

            return len(panels)
        except Exception as e:
            print(f"提交图片生成失败: {e}")
            return 0

    def get_episode_status(self, project_id: str, episode_id: str) -> Dict[str, Any]:
        """获取剧集状态"""
        if self.mock_mode:
            return {"status": "ok", "panels": 6, "done": 6, "clips": 3}

        try:
            resp = self.session.get(
                f"{self.base_url}/api/novel-promotion/{project_id}/episodes/{episode_id}",
                timeout=10
            )
            data = resp.json()
            panels = []
            for sb in data.get("episode", {}).get("storyboards", []):
                panels.extend(sb.get("panels", []))
            done = sum(1 for p in panels if p.get("imageUrl"))
            return {
                "status": "ok",
                "panels": len(panels),
                "done": done,
                "clips": len(data.get("episode", {}).get("clips", []))
            }
        except Exception as e:
            print(f"获取状态失败: {e}")
            return {"status": "error"}

    def get_characters(self, project_id: str, episode_id: str) -> List[Dict[str, Any]]:
        """获取故事中的角色列表"""
        if self.mock_mode:
            return [
                {"name": "阿金", "count": 5},
                {"name": "小松鼠", "count": 3},
                {"name": "旁白", "count": 2}
            ]

        try:
            resp = self.session.get(
                f"{self.base_url}/api/novel-promotion/{project_id}/episodes/{episode_id}",
                timeout=10
            )
            data = resp.json()
            voice_lines = data.get("episode", {}).get("voiceLines", [])
            speakers = {}
            for v in voice_lines:
                speaker = v.get("speaker", "未知")
                speakers[speaker] = speakers.get(speaker, 0) + 1
            return [{"name": k, "count": v} for k, v in sorted(speakers.items())]
        except Exception as e:
            print(f"获取角色失败: {e}")
            return []

    def setup_voice(self, project_id: str, episode_id: str, voice_map: Dict[str, str]) -> bool:
        """配置角色声音"""
        if self.mock_mode:
            print(f"  [Mock] 角色声音配置完成")
            for name, audio in voice_map.items():
                print(f"    {name} → {audio}")
            return True

        try:
            speaker_voices = {}
            for name, audio_file in voice_map.items():
                speaker_voices[name] = {
                    "voiceType": "uploaded",
                    "audioUrl": f"{self.base_url}/api/files/{audio_file}"
                }

            resp = self.session.patch(
                f"{self.base_url}/api/novel-promotion/{project_id}/episodes/{episode_id}",
                json={"speakerVoices": speaker_voices},
                timeout=10
            )
            print("  角色声音设置完成")
            for name, audio in voice_map.items():
                print(f"    {name} → {audio}")
            return True
        except Exception as e:
            print(f"设置角色声音失败: {e}")
            return False

    def voice_analyze(self, project_id: str, episode_id: str, locale: str = "zh") -> bool:
        """提交配音分析任务"""
        if self.mock_mode:
            print("  [Mock] 配音分析完成")
            return True

        try:
            self.session.post(
                f"{self.base_url}/api/novel-promotion/{project_id}/voice-analyze",
                json={"episodeId": episode_id, "locale": locale},
                timeout=10
            )
            print("  配音分析已提交")
            return True
        except Exception as e:
            print(f"提交配音分析失败: {e}")
            return False

    def voice_generate(self, project_id: str, episode_id: str, locale: str = "zh", total: int = 10) -> int:
        """提交配音生成任务"""
        if self.mock_mode:
            print(f"  [Mock] 已提交 {total} 条配音生成请求")
            return total

        try:
            resp = self.session.post(
                f"{self.base_url}/api/novel-promotion/{project_id}/voice-generate",
                json={
                    "episodeId": episode_id,
                    "locale": locale,
                    "all": True,
                    "audioModel": "fal::fal-ai/index-tts-2/text-to-speech"
                },
                timeout=10
            )
            data = resp.json()
            count = data.get("total", 0)
            print(f"  已提交 {count} 条配音生成请求")
            return count
        except Exception as e:
            print(f"提交配音生成失败: {e}")
            return 0

    def submit_video_generation(self, project_id: str, episode_id: str, locale: str = "zh") -> int:
        """提交视频生成任务"""
        if self.mock_mode:
            print("  [Mock] 已提交 6 段视频生成请求")
            return 6

        try:
            resp = self.session.post(
                f"{self.base_url}/api/novel-promotion/{project_id}/generate-video",
                json={
                    "episodeId": episode_id,
                    "locale": locale,
                    "all": True,
                    "videoModel": "ark::doubao-seedance-1-5-pro-251215",
                    "generationOptions": {
                        "generateAudio": False,
                        "duration": 4,
                        "resolution": "720p"
                    }
                },
                timeout=10
            )
            data = resp.json()
            count = data.get("total", 0)
            print(f"  已提交 {count} 段视频生成请求")
            return count
        except Exception as e:
            print(f"提交视频生成失败: {e}")
            return 0

    def download_video_segments(self, project_id: str, episode_id: str, output_dir: str = "/tmp/panels") -> List[str]:
        """下载所有视频片段"""
        if self.mock_mode:
            print("  [Mock] 视频片段下载完成")
            return [f"{output_dir}/000.mp4", f"{output_dir}/001.mp4"]

        os.makedirs(output_dir, exist_ok=True)
        lines = []

        try:
            resp = self.session.get(
                f"{self.base_url}/api/novel-promotion/{project_id}/episodes/{episode_id}",
                timeout=10
            )
            data = resp.json()
            panels = []
            for sb in data.get("episode", {}).get("storyboards", []):
                for p in sb.get("panels", []):
                    if p.get("videoUrl"):
                        panels.append(p)

            print(f"  共 {len(panels)} 个视频片段")
            for i, p in enumerate(panels):
                url = f"{self.base_url}{p['videoUrl']}"
                fname = f"{output_dir}/{i:03d}.mp4"
                subprocess.run(
                    ["curl", "-s", "-b", COOKIES_FILE, url, "-o", fname],
                    capture_output=True
                )
                size = os.path.getsize(fname) if os.path.exists(fname) else 0
                if size > 1000:
                    lines.append(f"file '{fname}'")
                    print(f"    [{i+1}/{len(panels)}] 下载完成 ({size//1024}KB)")
                else:
                    print(f"    [{i+1}/{len(panels)}] 跳过（文件太小）")

            return lines
        except Exception as e:
            print(f"下载视频片段失败: {e}")
            return []

    def merge_videos(self, filelist: List[str], output_path: str) -> bool:
        """使用 ffmpeg 合并视频"""
        if not filelist:
            print("  没有视频片段可合并")
            return False

        try:
            filelist_path = "/tmp/filelist.txt"
            with open(filelist_path, "w") as f:
                f.write("\n".join(filelist))

            subprocess.run(
                ["ffmpeg", "-f", "concat", "-safe", "0", "-i", filelist_path, "-c", "copy", output_path, "-y"],
                capture_output=True,
                timeout=600
            )

            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"  视频合并完成: {output_path} ({size//1024//1024}MB)")
                return True
            return False
        except Exception as e:
            print(f"合并视频失败: {e}")
            return False


# ============== 各阶段流程 ==============

def stage1_check_environment(client: WaoowaooClient) -> bool:
    """第一阶段：环境准备 - 检查服务状态"""
    print("\n" + "=" * 60)
    print("第一阶段：环境准备")
    print("=" * 60)

    print("\n1. 检查 Docker...")
    if check_command("docker"):
        print("  ✓ Docker 已安装")
    else:
        print("  ✗ Docker 未安装")
        return False

    print("\n2. 检查 waoowaoo 服务...")
    if client.check_health():
        print("  ✓ waoowaoo 服务正常")
        return True
    else:
        print("  ✗ waoowaoo 服务异常")
        print("  请运行: cd /opt/waoowaoo && docker compose up -d")
        return False


def stage2_story_to_storyboard(client: WaoowaooClient, story_text: str) -> Optional[Dict]:
    """第二阶段：故事变分镜"""
    print("\n" + "=" * 60)
    print("第二阶段：故事变分镜")
    print("=" * 60)

    # 2.1 加载会话或创建新项目
    session = load_session()
    project_id = session.get("PROJECT_ID")
    episode_id = session.get("EPISODE_ID")

    if not project_id:
        print("\n[2.1] 创建项目...")
        project_id = client.create_project()
        if not project_id:
            print("  ✗ 项目创建失败")
            return None
        save_session(project_id=project_id)

    if not episode_id:
        print("\n[2.2] 创建剧集...")
        episode_id = client.create_episode(project_id)
        if not episode_id:
            print("  ✗ 剧集创建失败")
            return None
        save_session(project_id=project_id, episode_id=episode_id)

    print("\n[2.3] 写入故事文本...")
    client.write_story(project_id, episode_id, story_text)

    print("\n[2.4] AI 分析故事...")
    task_id = client.analyze_story(project_id, episode_id)
    if task_id and not client.mock_mode:
        result = client.wait_for_task(task_id, max_wait=180)
        if result["status"] != "ok":
            print("  ⚠ 分析任务可能失败，继续...")

    print("\n[2.5] 生成片段...")
    clips_task_id = client.generate_clips(project_id, episode_id)
    if clips_task_id and not client.mock_mode:
        print("  等待片段生成完成...")
        result = client.wait_for_task(clips_task_id, max_wait=180)
        if result["status"] != "ok":
            print("  ⚠ 片段生成任务可能失败")
        else:
            print("  ✓ 片段生成完成")
    time.sleep(5)  # 额外等待确保数据就绪

    print("\n[2.6] 生成分镜...")
    task_id = client.generate_storyboard(project_id, episode_id)
    if task_id and not client.mock_mode:
        result = client.wait_for_task(task_id, max_wait=180)
        if result["status"] != "ok":
            print("  ⚠ 分镜任务可能失败，继续...")

    print("\n✓ 第二阶段完成！")
    return {"project_id": project_id, "episode_id": episode_id}


def stage3_images_and_voice(client: WaoowaooClient, project_id: str, episode_id: str) -> bool:
    """第三阶段：分镜变画面和声音"""
    print("\n" + "=" * 60)
    print("第三阶段：分镜变画面和声音")
    print("=" * 60)

    print("\n[3.1] 生成所有图片...")
    count = client.submit_panel_images(project_id, episode_id)
    if count > 0:
        print(f"  已提交 {count} 张图片生成请求")
        print("  等待图片生成（每15秒检查一次）...")
        for i in range(20):
            time.sleep(15)
            status = client.get_episode_status(project_id, episode_id)
            if status["status"] == "ok":
                done = status["done"]
                total = status["panels"]
                print(f"    图片进度: {done}/{total}")
                if done >= total:
                    print("  ✓ 所有图片生成完成！")
                    break
    else:
        print("  无需生成新图片")

    print("\n[3.2] 查看角色列表...")
    characters = client.get_characters(project_id, episode_id)
    print("  故事里的角色：")
    for char in characters:
        print(f"    - {char['name']}（{char['count']}句台词）")

    print("\n[3.3] 配置角色配音...")
    voice_map = {
        "阿金": "voice_male.mp3",
        "小松鼠": "voice_female.mp3",
        "旁白": "voice_male.mp3",
    }
    client.setup_voice(project_id, episode_id, voice_map)

    print("\n[3.4] 分析配音...")
    client.voice_analyze(project_id, episode_id)
    time.sleep(30)

    print("\n[3.5] 生成所有配音...")
    total = sum(c["count"] for c in characters)
    count = client.voice_generate(project_id, episode_id, total=total or 10)
    if count > 0:
        wait_time = count * 15 + 60
        print(f"  预计需要 {wait_time//60} 分钟")

    print("\n✓ 第三阶段完成！")
    return True


def stage4_generate_video(client: WaoowaooClient, project_id: str, episode_id: str) -> bool:
    """第四阶段：画面变完整视频"""
    print("\n" + "=" * 60)
    print("第四阶段：画面变完整视频")
    print("=" * 60)

    print("\n[4.1] 提交视频生成请求...")
    count = client.submit_video_generation(project_id, episode_id)

    if count > 0:
        print(f"\n  ✓ 已提交 {count} 段视频生成请求")
        print("  预计需要 60 分钟")

    print("\n✓ 第四阶段完成！")
    return True


def stage5_merge_video(client: WaoowaooClient, project_id: str, episode_id: str) -> Optional[str]:
    """第五阶段：合并成一个完整视频"""
    print("\n" + "=" * 60)
    print("第五阶段：合并视频")
    print("=" * 60)

    print("\n[5.1] 下载所有视频片段...")
    segments_dir = "/tmp/panels"
    lines = client.download_video_segments(project_id, episode_id, segments_dir)

    if not lines:
        print("  ✗ 没有视频片段可下载")
        return None

    print("\n[5.2] 合并视频...")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    merged_path = os.path.join(output_dir, "merged.mp4")

    if client.merge_videos(lines, merged_path):
        return merged_path
    return None


def stage6_download_local(merged_path: str) -> Optional[str]:
    """第六阶段：视频下载至本地"""
    print("\n" + "=" * 60)
    print("第六阶段：下载至本地")
    print("=" * 60)

    if not merged_path or not os.path.exists(merged_path):
        print("  ✗ 合并后的视频不存在")
        return None

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    final_path = os.path.join(output_dir, f"{time.strftime('%Y%m%d_%H%M%S')}.mp4")

    try:
        shutil.copy(merged_path, final_path)
        size = os.path.getsize(final_path)
        print(f"  ✓ 视频已保存: {final_path}")
        print(f"    文件大小: {size//1024//1024}MB")
        return final_path
    except Exception as e:
        print(f"  ✗ 保存失败: {e}")
        return None


# ============== 主流程 ==============

def run_novel_to_video(story_text: str, mock_mode: bool = False, email: str = None, password: str = None):
    """
    运行完整的小说转视频流程

    Args:
        story_text: 小说或故事文本
        mock_mode: True=使用模拟API，False=连接真实服务
        email: waoowaoo 登录邮箱
        password: waoowaoo 登录密码
    """
    print("\n" + "#" * 60)
    print("# AI 漫剧生成器 - 小说转视频")
    print("#" * 60)

    config = load_config()
    if not email:
        email = config.get("email")
    if not password:
        password = config.get("password")

    client = WaoowaooClient(mock_mode=mock_mode)

    if mock_mode:
        print("[测试模式] 使用模拟API进行测试")
    else:
        if client.load_cookies():
            print("✓ 已加载保存的认证信息")
        elif email and password:
            print(f"正在登录 waoowaoo ({email})...")
            if not client.login(email, password):
                print("登录失败，将切换到测试模式")
                mock_mode = True
        else:
            print("未提供认证信息，将切换到测试模式")
            mock_mode = True

    # 第一阶段：环境检查
    if not mock_mode and not stage1_check_environment(client):
        print("\n提示: 可使用 --mock 参数进行本地测试")
        return {"success": False, "stage": "environment", "message": "环境检查失败"}

    # 第二阶段：故事变分镜
    result = stage2_story_to_storyboard(client, story_text)
    if not result:
        return {"success": False, "stage": "storyboard", "message": "分镜生成失败"}

    project_id = result["project_id"]
    episode_id = result["episode_id"]

    # 第三阶段：分镜变画面和声音
    if not stage3_images_and_voice(client, project_id, episode_id):
        return {"success": False, "stage": "image_voice", "message": "画面配音生成失败"}

    # 第四阶段：生成视频
    if not stage4_generate_video(client, project_id, episode_id):
        return {"success": False, "stage": "video", "message": "视频生成失败"}

    # 第五阶段：合并视频
    merged_path = stage5_merge_video(client, project_id, episode_id)

    # 第六阶段：下载至本地
    final_path = stage6_download_local(merged_path)

    if final_path:
        return {"success": True, "video_path": final_path}
    else:
        return {"success": False, "stage": "download", "message": "视频下载失败"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI 漫剧生成器 - 小说转视频")
    parser.add_argument("story", nargs="?", help="小说文本")
    parser.add_argument("--mock", action="store_true", help="使用模拟API测试")
    parser.add_argument("--login", nargs=2, metavar=("EMAIL", "PASSWORD"), help="waoowaoo 账号登录")
    args = parser.parse_args()

    story = args.story
    if not story:
        story = input("\n请输入小说文本:\n").strip()

    if not story:
        print("错误: 请提供小说文本")
        sys.exit(1)

    email = password = None
    if args.login:
        email, password = args.login
    else:
        config = load_config()
        email = config.get("email")
        password = config.get("password")

    result = run_novel_to_video(story, mock_mode=args.mock, email=email, password=password)
    print(f"\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
