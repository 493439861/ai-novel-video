#!/usr/bin/env python3
"""Mock waoowaoo server for testing - simulates actual waoowaoo API structure"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import uuid


class MockHandler(BaseHTTPRequestHandler):
    """Simulates waoowaoo API endpoints"""

    def log_message(self, format, *args):
        pass  # Suppress logging

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _parse_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"
        return json.loads(body) if body else {}

    def do_GET(self):
        if self.path == "/zh/workspace":
            # Health check endpoint
            self._send_json({"status": "ok", "service": "waoowaoo-mock"})
        elif self.path.startswith("/api/tasks/"):
            # Task status endpoint
            task_id = self.path.split("/")[-1]
            self._send_json({
                "id": task_id,
                "status": "completed",
                "progress": 100,
                "result": {
                    "scenes": [
                        {"scene_id": "scene_1", "description": "少女推开窗户", "image_prompt": "anime girl window mountains", "dialogue": "今天的天空真美", "character": "少女"},
                        {"scene_id": "scene_2", "description": "少女走下楼梯来到街道", "image_prompt": "anime girl stairs street", "dialogue": "想去镇上走走", "character": "少女"}
                    ],
                    "characters": [{"name": "少女", "description": "小镇少女"}]
                }
            })
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        data = self._parse_body()

        # Project creation
        if self.path == "/api/projects":
            project_id = str(uuid.uuid4())
            self._send_json({
                "id": project_id,
                "name": data.get("name", "New Project"),
                "mode": "novel-promotion",
                "createdAt": time.time()
            })

        # Analyze endpoint (novel-promotion)
        elif self.path.startswith("/api/novel-promotion/") and "/analyze" in self.path:
            # Extract project_id from path
            parts = self.path.split("/")
            project_id = parts[3] if len(parts) > 3 else "unknown"

            # Return task info for async processing
            task_id = str(uuid.uuid4())
            self._send_json({
                "taskId": task_id,
                "status": "queued",
                "type": "analyze_novel",
                "projectId": project_id,
                "message": "分析任务已提交"
            })

        # Generate image endpoint
        elif self.path.startswith("/api/novel-promotion/") and "generate" in self.path:
            scene_id = data.get("scene_id", "unknown")
            self._send_json({
                "image_path": f"/tmp/mock_images/{scene_id}.png",
                "status": "generated",
                "scene_id": scene_id
            })

        # Generate voice endpoint
        elif self.path.startswith("/api/novel-promotion/") and "voice" in self.path:
            scene_id = data.get("scene_id", "unknown")
            self._send_json({
                "audio_path": f"/tmp/mock_audio/{scene_id}.mp3",
                "status": "generated",
                "scene_id": scene_id
            })

        # Compose video endpoint
        elif self.path.startswith("/api/novel-promotion/") and "compose" in self.path:
            scene_ids = data.get("scene_ids", [])
            self._send_json({
                "video_path": "/tmp/mock_output/video.mp4",
                "status": "composed",
                "scenes_count": len(scene_ids)
            })

        # Generic task submission
        elif self.path == "/api/tasks":
            task_id = str(uuid.uuid4())
            self._send_json({
                "id": task_id,
                "status": "completed",
                "type": data.get("type", "unknown")
            })

        else:
            self._send_json({"error": "unknown endpoint"}, 404)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 13000), MockHandler)
    print("Mock waoowaoo running on :13000")
    server.serve_forever()
