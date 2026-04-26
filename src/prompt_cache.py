#!/usr/bin/env python3
"""
Prompt 缓存工具 - 用于长篇小说分段处理
避免 token 溢出，将长文本拆分为可处理的 chunks
"""

from typing import List, Iterator


class PromptCache:
    """长文本分段缓存"""

    def __init__(self, max_chars: int = 4000, overlap: int = 200):
        self.max_chars = max_chars
        self.overlap = overlap

    def split(self, text: str) -> List[str]:
        """将长文本拆分为多个 chunk"""
        if len(text) <= self.max_chars:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.max_chars

            if end >= len(text):
                chunks.append(text[start:])
                break

            # 在句号或换行处分割，保持语义完整
            split_pos = self._find_split_point(text, start, end)
            if split_pos <= start:
                split_pos = end

            chunks.append(text[start:split_pos])
            start = split_pos - self.overlap

        return chunks

    def _find_split_point(self, text: str, start: int, end: int) -> int:
        """找到最佳分割点（句号、换行、逗号）"""
        candidates = []

        for char in ['\n', '。', '！', '？', '，', '.', '!', '?']:
            pos = text.rfind(char, start, end)
            if pos > start:
                candidates.append(pos)

        if candidates:
            return max(candidates) + 1
        return end

    def merge_results(self, results: List[dict]) -> dict:
        """合并分段处理的结果"""
        merged = {"scenes": [], "characters": {}}

        for result in results:
            if "scenes" in result:
                merged["scenes"].extend(result["scenes"])
            if "characters" in result:
                merged["characters"].update(result["characters"])

        return merged


if __name__ == "__main__":
    cache = PromptCache(max_chars=4000)

    sample_text = """
    这是一个测试文本。今天天气很好，阳光明媚。

    他走进了一家咖啡馆，点了一杯拿铁。咖啡馆里播放着轻快的音乐。
    他坐下来，打开笔记本电脑，开始工作。

    窗外的人们匆匆走过，没有人注意到他。
    """

    chunks = cache.split(sample_text)
    print(f"文本长度: {len(sample_text)}")
    print(f"分段数量: {len(chunks)}")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n--- Chunk {i} ---")
        print(chunk)