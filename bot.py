#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大學生報告主題發想_搜集機器人 (IdeaCatcher Bot) - v2.0 課後改善版
核心邏輯處理模組

改善重點：
1. 智慧關鍵字自動分類推測（即使未輸入「分類：」也能依主題自動標籤）
2. 支援依學科分類篩選與關鍵字搜尋（例如「查看：科技」或「搜尋：AI」）
3. 支援單筆靈感刪除（「刪除：[編號]」）與邊界防呆
4. LINE Bot 雲端金鑰安全佔位設定範本（避免敏感資訊外洩）
"""

import re
import json
import os
from typing import List, Dict, Optional, Tuple

# ==========================================================
# 🔐 LINE Bot 安全設定（以佔位文字說明，避免外洩真實金鑰）
# ==========================================================
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_LINE_CHANNEL_SECRET_PLACEHOLDER")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_LINE_ACCESS_TOKEN_PLACEHOLDER")

# 智慧學科關鍵字特徵庫（改善功能 1）
KEYWORD_CATEGORY_MAP = {
    "資訊科技": ["ai", "人工智慧", "機器學習", "演算法", "區塊鏈", "程式", "資工", "大數據", "雲端", "深度學習", "物聯網", "app", "資安"],
    "社會心理": ["心理", "焦慮", "憂鬱", "情緒", "社群", "人際", "社會", "家庭", "青少年", "壓力", "行為"],
    "商管企管": ["行銷", "廣告", "商業", "管理", "esg", "永續", "財務", "創業", "經濟", "電商", "消費者"],
    "醫學健康": ["醫療", "健康", "疾病", "護理", "疫苗", "公衛", "診斷", "睡眠", "飲食", "體適能"],
    "人文教育": ["教育", "教學", "歷史", "文學", "哲學", "語言", "學習", "多元文化"]
}


class IdeaBot:
    """報告主題發想與搜集機器人核心類別 (v2.0 改善版)"""

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

    def _auto_detect_category(self, topic: str) -> str:
        """根據關鍵字自動推測學科領域（v2.0 改善功能）"""
        lower_topic = topic.lower()
        for category, keywords in KEYWORD_CATEGORY_MAP.items():
            for kw in keywords:
                if kw in lower_topic:
                    return category
        return "一般/其他"

    def handle_message(self, user_message: str) -> str:
        """
        處理使用者輸入訊息並回傳 Bot 回覆內容。
        """
        if not user_message:
            return self._unknown_command_reply()

        text = user_message.strip()

        # 1. 判斷是否為「記錄靈感」指令 (支援全形或半形冒號)
        record_patterns = [r"^靈感[:：]", r"^記[:：]"]
        for pattern in record_patterns:
            match = re.match(pattern, text)
            if match:
                content = text[match.end():].strip()
                return self._handle_record_idea(content)

        # 2. 判斷是否為「搜尋/分類篩選靈感」指令（v2.0 改善功能）
        search_patterns = [r"^(搜尋|查看|篩選)[:：]\s*(.+)$", r"^查[:：]\s*(.+)$"]
        for sp in search_patterns:
            smatch = re.match(sp, text)
            if smatch:
                keyword = smatch.group(2).strip()
                return self._handle_search_ideas(keyword)

        # 3. 判斷是否為「查看全部靈感」指令
        view_keywords = ["查看靈感", "查看清單", "清單", "列表", "調閱", "靈感清單", "全部靈感"]
        if any(text == kw for kw in view_keywords):
            return self._handle_view_all_ideas()

        # 4. 判斷是否為「刪除單筆靈感」指令（v2.0 改善功能）
        del_pattern = r"^刪除[:：]\s*(.*)$"
        del_match = re.match(del_pattern, text)
        if del_match:
            del_arg = del_match.group(1).strip()
            return self._handle_delete_idea(del_arg)

        # 5. 判斷是否為「清空全部靈感」指令
        clear_keywords = ["清空靈感", "清除靈感", "清空清單"]
        if any(text == kw for kw in clear_keywords):
            return self._handle_clear_ideas()

        # 6. 其他未知訊息：提供完整使用指南
        return self._unknown_command_reply()

    def _handle_record_idea(self, content: str) -> str:
        """處理記錄靈感細部邏輯（包含主題、分類解析、智慧推測與防呆）"""
        if not content:
            return (
                "⚠️ 請輸入要記錄的報告靈感主題喔！\n"
                "💡 正確格式範例：\n"
                "   • 自訂分類：「靈感：智慧農業應用 分類：資工」\n"
                "   • 智慧自動分類：「靈感：生成式 AI 在醫療的倫理議題」（系統會自動標記為資訊科技/醫學健康）"
            )

        # 檢查是否有指定分類
        cat_match = re.search(r"[\s,，]+(分類|類別)[:：]\s*(.+)$", content)
        is_auto_categorized = False

        if cat_match:
            category = cat_match.group(2).strip()
            topic = content[: cat_match.start()].strip()
        else:
            topic = content.strip()
            # 使用智慧關鍵字推測分類（v2.0 改善）
            category = self._auto_detect_category(topic)
            is_auto_categorized = True

        if not topic:
            return (
                "⚠️ 靈感主題不可為空白！請在「靈感：」後填寫報告主題內容。\n"
                "💡 範例：「靈感：社群成癮與青年焦慮」"
            )

        # 儲存點子
        idea_item = {"topic": topic, "category": category}
        self.ideas.append(idea_item)
        self._save_to_storage()

        auto_note = "（✨ 系統已為您智慧識別歸類）" if is_auto_categorized else ""
        reply = (
            "✅ 已為您成功記錄報告靈感！\n"
            f"📌 主題：{topic}\n"
            f"🏷️ 分類：{category} {auto_note}\n"
            f"🔢 目前編號：第 {len(self.ideas)} 筆\n"
            "💡 提示：輸入「查看靈感」或「搜尋：[關鍵字]」隨時調閱。"
        )
        return reply

    def _handle_view_all_ideas(self) -> str:
        """處理查看全部靈感清單"""
        if not self.ideas:
            return (
                "📋 目前尚未儲存任何報告靈感喔！\n"
                "💡 快試試傳送「靈感：[主題]」來記錄您的第一個點子吧！"
            )

        lines = [f"📋 目前已收集的報告點子清單（共 {len(self.ideas)} 則）："]
        for idx, item in enumerate(self.ideas, 1):
            lines.append(f"{idx}. [{item['category']}] {item['topic']}")
        lines.append("\n💡 提示：輸入「搜尋：[關鍵字]」可篩選特定主題；輸入「刪除：[編號]」可移除指定點子。")
        return "\n".join(lines)

    def _handle_search_ideas(self, keyword: str) -> str:
        """處理依分類或關鍵字篩選調閱（v2.0 改善功能）"""
        if not keyword:
            return "⚠️ 請輸入要搜尋的分類或關鍵字！例如：「查看：資訊科技」或「搜尋：AI」。"

        if not self.ideas:
            return "📋 目前資料庫內沒有任何點子可供搜尋。"

        matched = []
        kw_lower = keyword.lower()
        for idx, item in enumerate(self.ideas, 1):
            if kw_lower in item["category"].lower() or kw_lower in item["topic"].lower():
                matched.append((idx, item))

        if not matched:
            return (
                f"🔍 找不到與「{keyword}」相符的報告主題。\n"
                "💡 提示：輸入「查看靈感」可檢視現有所有點子與分類清單。"
            )

        lines = [f"🔍 「{keyword}」相關報告點子篩選結果（共 {len(matched)} 則）："]
        for orig_idx, item in matched:
            lines.append(f"{orig_idx}. [{item['category']}] {item['topic']}")
        return "\n".join(lines)

    def _handle_delete_idea(self, arg: str) -> str:
        """處理單筆刪除點子（v2.0 改善功能，附防呆與邊界檢查）"""
        if not arg:
            return "⚠️ 請提供要刪除的靈感編號！\n💡 範例：「刪除：1」（若不確定編號，可先輸入「查看靈感」查詢）。"

        try:
            target_idx = int(arg)
        except ValueError:
            return f"⚠️ 輸入的編號「{arg}」不是有效數字！請輸入正確整數編號，例如：「刪除：2」。"

        if target_idx < 1 or target_idx > len(self.ideas):
            return (
                f"⚠️ 找不到編號 {target_idx} 的報告點子！\n"
                f"💡 目前有效編號範圍為 1 ~ {len(self.ideas)}（輸入「查看靈感」可確認最新編號）。"
            )

        # 移除該項目
        removed_item = self.ideas.pop(target_idx - 1)
        self._save_to_storage()

        return (
            f"🗑️ 已成功刪除編號 {target_idx} 的報告主題！\n"
            f"📌 移除內容：[{removed_item['category']}] {removed_item['topic']}\n"
            f"📊 剩餘儲存點子數量：{len(self.ideas)} 則"
        )

    def _handle_clear_ideas(self) -> str:
        """清空靈感清單"""
        count = len(self.ideas)
        self.ideas.clear()
        self._save_to_storage()
        return f"🗑️ 已成功清空靈感清單！（共清除了 {count} 則主題）"

    def _unknown_command_reply(self) -> str:
        """非支援指令時的使用指南說明 (v2.0 完整手冊)"""
        return (
            "👋 您好！我是「大學生報告主題發想_搜集機器人」(v2.0 改善版)。\n"
            "我可以幫您隨手捕捉稍縱即逝的報告靈感並智慧分類！\n\n"
            "🛠️ 目前支援指令列表：\n"
            "1. 記錄靈感：「靈感：[主題名稱]」（系統會自動智慧分類）\n"
            "   或自訂分類：「靈感：[主題] 分類：[學科]」\n"
            "2. 搜尋/篩選：「查看：[分類]」或「搜尋：[關鍵字]」\n"
            "3. 查看全部：「查看靈感」或「清單」\n"
            "4. 刪除單筆：「刪除：[編號]」（例如：刪除：1）\n"
            "5. 清空資料：「清空靈感」"
        )


def main():
    """互動式終端機測試模式 (v2.0)"""
    bot = IdeaBot()
    print("=" * 60)
    print("🤖 大學生報告主題發想_搜集機器人 (v2.0 課後改善版 - 互動終端模式)")
    print("支援新功能：智慧自動分類、搜尋/篩選、單筆刪除")
    print("輸入訊息開始對話，輸入 'exit' 或 'quit' 結束。")
    print("=" * 60)

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
