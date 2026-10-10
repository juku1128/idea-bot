#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大學生報告主題發想_搜集機器人 (IdeaCatcher Bot) - v2.0 課後改善完成版
核心邏輯處理模組

改善版正式核心成果：
1. 【核心改善亮點】一鍵生成並匯出 Markdown 報告大綱草稿（「大綱：[編號]」或「匯出大綱：[編號]」）
2. 【智慧分類升級】關鍵字特徵庫智慧自動推測學科分類（未填分類時自動識別）
3. 【檢索與管理】支援領域篩選（「查看：[分類]」）與單筆靈感刪除（「刪除：[編號]」）
4. 【強健防呆機制】越界編號保護、空白輸入攔截與非數字型別檢查
"""

import re
import json
import os
from typing import List, Dict, Optional, Tuple

# 🔐 安全設定佔位符（避免外洩真實金鑰）
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_LINE_CHANNEL_SECRET_PLACEHOLDER")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_LINE_ACCESS_TOKEN_PLACEHOLDER")

# 智慧學科關鍵字特徵庫
KEYWORD_CATEGORY_MAP = {
    "資訊科技": ["ai", "人工智慧", "機器學習", "演算法", "區塊鏈", "程式", "資工", "大數據", "雲端", "深度學習", "物聯網", "app", "資安"],
    "社會心理": ["心理", "焦慮", "憂鬱", "情緒", "社群", "人際", "社會", "家庭", "青少年", "壓力", "行為"],
    "商管企管": ["行銷", "廣告", "商業", "管理", "esg", "永續", "財務", "創業", "經濟", "電商", "消費者"],
    "醫學健康": ["醫療", "健康", "疾病", "護理", "疫苗", "公衛", "診斷", "睡眠", "飲食", "體適能"],
    "人文教育": ["教育", "教學", "歷史", "文學", "哲學", "語言", "學習", "多元文化"]
}


class IdeaBot:
    """報告主題發想與搜集機器人核心類別 (v2.0 改善完成版)"""

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
        """根據關鍵字自動推測學科領域"""
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

        # 1. 記錄靈感
        record_patterns = [r"^靈感[:：]", r"^記[:：]"]
        for pattern in record_patterns:
            match = re.match(pattern, text)
            if match:
                content = text[match.end():].strip()
                return self._handle_record_idea(content)

        # 2. 【核心改善亮點】一鍵生成 / 匯出報告大綱草稿
        outline_patterns = [r"^(匯出大綱|大綱|生成大綱)[:：]\s*(.*)$"]
        for op in outline_patterns:
            omatch = re.match(op, text)
            if omatch:
                arg = omatch.group(2).strip()
                return self._handle_generate_outline(arg)

        # 3. 搜尋 / 領域篩選靈感
        search_patterns = [r"^(搜尋|查看|篩選)[:：]\s*(.+)$", r"^查[:：]\s*(.+)$"]
        for sp in search_patterns:
            smatch = re.match(sp, text)
            if smatch:
                keyword = smatch.group(2).strip()
                return self._handle_search_ideas(keyword)

        # 4. 查看全部靈感清單
        view_keywords = ["查看靈感", "查看清單", "清單", "列表", "調閱", "全部靈感"]
        if any(text == kw for kw in view_keywords):
            return self._handle_view_all_ideas()

        # 5. 刪除單筆靈感
        del_pattern = r"^刪除[:：]\s*(.*)$"
        del_match = re.match(del_pattern, text)
        if del_match:
            del_arg = del_match.group(1).strip()
            return self._handle_delete_idea(del_arg)

        # 6. 清空全部靈感
        clear_keywords = ["清空靈感", "清除靈感", "清空清單"]
        if any(text == kw for kw in clear_keywords):
            return self._handle_clear_ideas()

        # 7. 其他未知訊息
        return self._unknown_command_reply()

    def _handle_record_idea(self, content: str) -> str:
        """處理記錄靈感細部邏輯"""
        if not content:
            return (
                "⚠️ 請輸入要記錄的報告靈感主題喔！\n"
                "💡 正確格式範例：\n"
                "   • 智慧自動分類：「靈感：深度學習在無人機的應用」\n"
                "   • 自訂分類：「靈感：ESG 永續經營策略 分類：商管」"
            )

        cat_match = re.search(r"[\s,，]+(分類|類別)[:：]\s*(.+)$", content)
        is_auto_categorized = False

        if cat_match:
            category = cat_match.group(2).strip()
            topic = content[: cat_match.start()].strip()
        else:
            topic = content.strip()
            category = self._auto_detect_category(topic)
            is_auto_categorized = True

        if not topic:
            return "⚠️ 靈感主題不可為空白！請在「靈感：」後填寫報告主題內容。"

        idea_item = {"topic": topic, "category": category}
        self.ideas.append(idea_item)
        self._save_to_storage()

        auto_note = "（✨ 系統已智慧識別領域）" if is_auto_categorized else ""
        return (
            "✅ 已為您成功記錄報告靈感！\n"
            f"📌 主題：{topic}\n"
            f"🏷️ 分類：{category} {auto_note}\n"
            f"🔢 目前編號：第 {len(self.ideas)} 筆\n"
            f"💡 提示：輸入「大綱：{len(self.ideas)}」可一鍵生成此題目的三段式報告大綱草稿！"
        )

    def _handle_generate_outline(self, arg: str) -> str:
        """【改善亮點】根據指定編號主題一鍵生成 Markdown 報告大綱草稿並儲存實體檔案"""
        if not arg:
            return (
                "⚠️ 請輸入要生成大綱的靈感編號！\n"
                "💡 範例：「大綱：1」或「匯出大綱：1」（可先輸入「查看靈感」確認編號）。"
            )

        try:
            idx = int(arg)
        except ValueError:
            return f"⚠️ 輸入的編號「{arg}」不是有效數字！請輸入數字編號，例如：「大綱：1」。"

        if idx < 1 or idx > len(self.ideas):
            return (
                f"⚠️ 找不到編號 {idx} 的報告主題！\n"
                f"💡 目前有效編號範圍為 1 ~ {len(self.ideas)}（輸入「查看靈感」可確認最新編號）。"
            )

        target = self.ideas[idx - 1]
        topic = target["topic"]
        category = target["category"]

        # 針對不同學科領域生成客製化大綱結構
        outline_md = (
            f"# 【報告大綱草稿】{topic}\n\n"
            f"- **研究領域**：{category}\n"
            f"- **建立來源**：IdeaCatcher Bot v2.0 自動生成\n\n"
            f"## 一、研究背景與動機\n"
            f"探討現代社會與大專院校背景下，關於「{topic}」的現況觀察與問題意識。\n"
            f"闡述為何該主題值得深入研究，以及在 {category} 領域中的核心重要性。\n\n"
            f"## 二、主要探討核心面向\n"
            f"1. **文獻探討與理論架構**：整理國內外針對「{topic}」的相關文獻與現行模型。\n"
            f"2. **實務現況與案例分析**：蒐集實際案例或數據，分析影響關鍵因子。\n"
            f"3. **挑戰與瓶頸剖析**：探討推動或執行過程中所面臨的主要困境與限制。\n\n"
            f"## 三、預期研究結論與效益\n"
            f"1. 提出具體可行的解決對策或管理/實踐建議。\n"
            f"2. 歸納研究成果對大專學生、產學界或社會之貢獻與未來展望。\n"
        )

        # 實體匯出 Markdown 檔案
        clean_filename = re.sub(r'[\\/*?:"<>|]', "", topic)[:20]
        export_filename = f"報告大綱_{idx}_{clean_filename}.md"
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_dir, export_filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(outline_md)
            save_msg = f"\n💾 已同步在資料夾中匯出為：`{export_filename}`"
        except Exception:
            save_msg = ""

        reply = (
            f"📝 已為您成功生成【{topic}】的報告大綱草稿！\n"
            f"🏷️ 領域分類：{category}\n\n"
            "────────────── 大綱預覽 ──────────────\n"
            "一、研究背景與動機\n"
            f"    • 探討現代情境下「{topic}」之研究重要性。\n"
            "二、主要探討核心面向\n"
            "    1. 文獻理論與模型基礎\n"
            "    2. 實務案例與關鍵影響因子分析\n"
            "    3. 現行困境與實踐挑戰\n"
            "三、預期研究結論與效益\n"
            "    • 提出具體改善策略與未來展望方向\n"
            "────────────────────────────────────\n"
            f"{save_msg}\n"
            "💡 提示：點子已經結構化，可直接複製或開啟檔案拿來寫報告！"
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
        lines.append("\n💡 提示：輸入「大綱：[編號]」可一鍵生成該題目的完整報告大綱草稿！")
        return "\n".join(lines)

    def _handle_search_ideas(self, keyword: str) -> str:
        """處理依分類或關鍵字篩選調閱"""
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
                "💡 提示：輸入「查看靈感」可檢視現有所有點子清單。"
            )

        lines = [f"🔍 「{keyword}」相關報告點子篩選結果（共 {len(matched)} 則）："]
        for orig_idx, item in matched:
            lines.append(f"{orig_idx}. [{item['category']}] {item['topic']}")
        lines.append("\n💡 提示：輸入「大綱：[編號]」可直接產生該篇大綱！")
        return "\n".join(lines)

    def _handle_delete_idea(self, arg: str) -> str:
        """處理單筆刪除點子（附防呆與邊界檢查）"""
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
            "👋 您好！我是「大學生報告主題發想_搜集機器人」(v2.0 課後改善完成版)。\n"
            "我可以幫您隨手捕捉報告靈感，並能一鍵產生報告大綱草稿！\n\n"
            "🛠️ 目前支援指令列表：\n"
            "1. 記錄靈感：「靈感：[主題名稱]」（系統會智慧自動分類）\n"
            "   或自訂分類：「靈感：[主題] 分類：[學科]」\n"
            "2. 生成大綱：「大綱：[編號]」（🌟 改善亮點：一鍵生成三段式報告大綱）\n"
            "3. 搜尋/篩選：「查看：[分類]」或「搜尋：[關鍵字]」\n"
            "4. 查看全部：「查看靈感」或「清單」\n"
            "5. 刪除單筆：「刪除：[編號]」\n"
            "6. 清空資料：「清空靈感」"
        )


def main():
    """互動式終端機測試模式 (v2.0)"""
    bot = IdeaBot()
    print("=" * 65)
    print("🤖 大學生報告主題發想_搜集機器人 (v2.0 課後改善完成版)")
    print("🌟 核心改善亮點：一鍵匯出 Markdown 報告大綱草稿 (大綱：[編號])")
    print("輸入訊息開始對話，輸入 'exit' 或 'quit' 結束。")
    print("=" * 65)

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
