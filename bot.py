#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大學生報告主題發想_搜集機器人 (IdeaCatcher Bot)
核心邏輯處理模組
"""

import re
import json
import os
from typing import List, Dict, Optional


class IdeaBot:
    """報告主題發想與搜集機器人核心類別"""

    def __init__(self, storage_file: Optional[str] = None):
        """
        初始化機器人。
        :param storage_file: 選填，儲存點子的 JSON 檔案路徑。若無則使用記憶體暫存。
        """
        self.storage_file = storage_file
        self.ideas: List[Dict[str, str]] = []
        if self.storage_file and os.path.exists(self.storage_file):
            self._load_from_storage()

    def _load_from_storage(self):
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                self.ideas = json.load(f)
        except Exception:
            self.ideas = []

    def _save_to_storage(self):
        if self.storage_file:
            try:
                with open(self.storage_file, "w", encoding="utf-8") as f:
                    json.dump(self.ideas, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def handle_message(self, user_message: str) -> str:
        """
        處理使用者輸入訊息並回傳 Bot 回覆內容。
        """
        if not user_message:
            return self._unknown_command_reply()

        text = user_message.strip()

        # 1. 判斷是否為「記錄靈感」指令 (支援全形或半形冒號)
        record_patterns = [r"^靈感[:：]", r"^記[:：]"]
        is_record_command = False
        prefix_len = 0

        for pattern in record_patterns:
            match = re.match(pattern, text)
            if match:
                is_record_command = True
                prefix_len = match.end()
                break

        if is_record_command:
            content = text[prefix_len:].strip()
            return self._handle_record_idea(content)

        # 2. 判斷是否為「調閱靈感」指令
        view_keywords = ["查看靈感", "查看清單", "清單", "列表", "調閱", "靈感清單"]
        if any(text == kw for kw in view_keywords):
            return self._handle_view_ideas()

        # 3. 判斷是否為「清空靈感」指令
        clear_keywords = ["清空靈感", "清除靈感", "清空清單"]
        if any(text == kw for kw in clear_keywords):
            return self._handle_clear_ideas()

        # 4. 其他未知訊息：提供使用指南
        return self._unknown_command_reply()

    def _handle_record_idea(self, content: str) -> str:
        """處理記錄靈感細部邏輯（包含主題、分類解析與防呆）"""
        if not content:
            return (
                "⚠️ 請輸入要記錄的報告靈感主題喔！\n"
                "💡 正確格式範例：\n"
                "   • 「靈感：智慧農業應用 分類：資工」\n"
                "   • 或直接輸入「靈感：ESG 永續經營策略」"
            )

        # 支援解析「分類：...」或「類別：...」
        cat_match = re.search(r"[\s,，]+(分類|類別)[:：]\s*(.+)$", content)
        if cat_match:
            category = cat_match.group(2).strip()
            topic = content[: cat_match.start()].strip()
        else:
            category = "一般/未分類"
            topic = content.strip()

        if not topic:
            return (
                "⚠️ 靈感主題不可為空白！請在「靈感：」後填寫報告主題內容。\n"
                "💡 範例：「靈感：心理學在廣告中的應用 分類：商管」"
            )

        # 儲存點子
        idea_item = {"topic": topic, "category": category}
        self.ideas.append(idea_item)
        self._save_to_storage()

        reply = (
            "✅ 已為您成功記錄報告靈感！\n"
            f"📌 主題：{topic}\n"
            f"🏷️ 分類：{category}\n"
            "💡 提示：隨時輸入「查看靈感」即可調閱所有已儲存的主題。"
        )
        return reply

    def _handle_view_ideas(self) -> str:
        """處理查看靈感清單"""
        if not self.ideas:
            return (
                "📋 目前尚未儲存任何報告靈感喔！\n"
                "💡 快試試傳送「靈感：[主題] 分類：[學科]」來記錄您的第一個點子吧！"
            )

        lines = [f"📋 目前已收集的報告點子清單（共 {len(self.ideas)} 則）："]
        for idx, item in enumerate(self.ideas, 1):
            lines.append(f"{idx}. [{item['category']}] {item['topic']}")
        lines.append("\n💡 繼續傳送「靈感：[主題]」來添加新點子！")
        return "\n".join(lines)

    def _handle_clear_ideas(self) -> str:
        """清空靈感清單"""
        count = len(self.ideas)
        self.ideas.clear()
        self._save_to_storage()
        return f"🗑️ 已成功清空靈感清單！（共清除了 {count} 則主題）"

    def _unknown_command_reply(self) -> str:
        """非支援指令時的使用指南說明"""
        return (
            "👋 您好！我是「大學生報告主題發想_搜集機器人」。\n"
            "我可以幫您隨手捕捉稍縱即逝的報告靈感！\n\n"
            "🛠️ 目前支援指令：\n"
            "1. 記錄靈感：「靈感：[主題名稱] 分類：[學科領域]」\n"
            "   （若不填分類，預設為一般）\n"
            "2. 調閱靈感：「查看靈感」或「清單」\n"
            "3. 清空資料：「清空靈感」"
        )


def main():
    """互動式終端機測試模式"""
    bot = IdeaBot()
    print("=" * 55)
    print("🤖 大學生報告主題發想_搜集機器人 (互動終端模式)")
    print("輸入訊息開始對話，輸入 'exit' 或 'quit' 結束。")
    print("=" * 55)

    while True:
        try:
            user_input = input("\n[使用者] > ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("👋 掰掰！祝報告順利拿到高分！")
                break
            if not user_input:
                continue
            response = bot.handle_message(user_input)
            print(f"\n[Bot 回覆]\n{response}")
        except (KeyboardInterrupt, EOFError):
            print("\n👋 程式結束")
            break


if __name__ == "__main__":
    main()
