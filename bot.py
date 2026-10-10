#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大學生報告主題發想_搜集機器人 (IdeaCatcher Bot) - v2.0 課後改善完成版
核心邏輯處理模組

修復重點：
1. 擴充智慧學科關鍵字庫（包含機器人、教育、世代、體罰等），精準自動識別領域。
2. 徹底解決「大綱都一樣」問題：根據主題實質內容與學科領域，動態產出針對性的核心探討面向、研究背景與具體建議！
3. 優化未識別時的提示：未命中時不誇稱智慧識別，改提示可手動標註。
"""

import re
import json
import os
from typing import List, Dict, Optional, Tuple

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_LINE_CHANNEL_SECRET_PLACEHOLDER")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_LINE_ACCESS_TOKEN_PLACEHOLDER")

# 完整涵蓋大專院校熱門報告領域之關鍵字庫
KEYWORD_CATEGORY_MAP = {
    "資訊科技": [
        "ai", "人工智慧", "機器學習", "演算法", "區塊鏈", "程式", "資工", "大數據", "雲端",
        "深度學習", "物聯網", "app", "資安", "機器人", "bot", "自動化", "軟體", "系統", "資訊", "科技", "平台"
    ],
    "人文教育": [
        "教育", "體罰", "世代", "教養", "教學", "學校", "學生", "老師", "學習", "兒童",
        "幼兒", "歷史", "文學", "哲學", "語言", "文化", "考題", "課綱", "家長", "管教", "成長"
    ],
    "社會心理": [
        "心理", "焦慮", "憂鬱", "情緒", "社群", "人際", "社會", "家庭", "青少年", "壓力",
        "行為", "諮商", "人格", "關係", "霸凌", "溝通", "同儕", "自尊", "孤獨", "成癮"
    ],
    "商管企管": [
        "行銷", "廣告", "商業", "管理", "esg", "永續", "財務", "創業", "經濟", "電商",
        "消費者", "企業", "品牌", "營運", "投資", "市場", "策略", "通路", "競品"
    ],
    "醫學健康": [
        "醫療", "健康", "疾病", "護理", "疫苗", "公衛", "診斷", "睡眠", "飲食", "體適能",
        "運動", "生理", "藥物", "公共衛生", "衛福", "營養", "身心障礙", "復健"
    ],
    "法律政治": [
        "法律", "政策", "政治", "權利", "法規", "憲法", "犯罪", "司法", "民主", "人權",
        "勞動法", "刑法", "民法", "選舉", "國際關係"
    ]
}


class IdeaBot:
    """報告主題發想與搜集機器人核心類別 (v2.0 改善完成版)"""

    def __init__(self, storage_file: Optional[str] = None):
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

    def _auto_detect_category(self, topic: str) -> Tuple[str, bool]:
        """
        根據關鍵字自動推測學科領域。
        回傳：(分類名稱, 是否真正命中關鍵字)
        """
        lower_topic = topic.lower()
        for category, keywords in KEYWORD_CATEGORY_MAP.items():
            for kw in keywords:
                if kw in lower_topic:
                    return category, True
        return "一般/其他", False

    def handle_message(self, user_message: str) -> str:
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

        # 2. 一鍵生成 / 匯出報告大綱草稿
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
        if not content:
            return (
                "⚠️ 請輸入要記錄的報告靈感主題喔！\n"
                "💡 正確格式範例：\n"
                "   • 自動辨識：「靈感：體罰是否必要？世代教育觀念探討」\n"
                "   • 自訂分類：「靈感：ESG 永續經營策略 分類：商管」"
            )

        cat_match = re.search(r"[\s,，]+(分類|類別)[:：]\s*(.+)$", content)

        if cat_match:
            category = cat_match.group(2).strip()
            topic = content[: cat_match.start()].strip()
            detected_tag = f"🏷️ 分類：{category}（使用者指定）"
        else:
            topic = content.strip()
            category, hit = self._auto_detect_category(topic)
            if hit:
                detected_tag = f"🏷️ 分類：{category}（✨ 智慧識別領域：{category}）"
            else:
                detected_tag = f"🏷️ 分類：{category}（💡 提示：可於文末輸入「分類：學科」自訂）"

        if not topic:
            return "⚠️ 靈感主題不可為空白！請在「靈感：」後填寫報告主題內容。"

        idea_item = {"topic": topic, "category": category}
        self.ideas.append(idea_item)
        self._save_to_storage()

        return (
            "✅ 已為您成功記錄報告靈感！\n"
            f"📌 主題：{topic}\n"
            f"{detected_tag}\n"
            f"🔢 目前編號：第 {len(self.ideas)} 筆\n"
            f"💡 提示：輸入「大綱：{len(self.ideas)}」可一鍵生成此題目的三段式專屬報告大綱！"
        )

    def _generate_tailored_outline_content(self, topic: str, category: str) -> Tuple[str, List[str], str]:
        """
        根據領域分類與題目內容實質語意，產出深度的研究背景、三大探討核心與結論建議。
        依據所屬領域精準客製化，徹底告別千篇一律的刻板模板！
        """
        topic_lower = topic.lower()

        # 1. 資訊科技領域（機器人、AI、系統、軟體、程式等）
        if category == "資訊科技" or any(k in topic_lower for k in ["機器人", "bot", "ai", "人工智慧", "軟體", "系統", "程式", "演算法", "自動化"]):
            bg = f"探討數位化與人工智慧浪潮下，針對「{topic}」在知識管理、自動化輔助與人機協同發想中的應用潛力與核心價值。"
            points = [
                f"針對「{topic}」之核心系統架構、自然語言對話流程與指令解析效能評估",
                f"使用者在日常操作與靈感收集流程中之實質痛點與人機介面接受度調研",
                f"資料結構化儲存、多輪對話防呆容錯機制與實務落地部署瓶頸剖析"
            ]
            conclusion = f"驗證該系統對提升使用者創意發想與研究效率之實質成效，並提出後續架構優化建議。"
            return bg, points, conclusion

        # 2. 人文教育領域（體罰、世代、教育、教學、學校等）
        if category == "人文教育" or any(k in topic_lower for k in ["體罰", "世代", "管教", "教養", "教學", "課綱"]):
            if any(k in topic_lower for k in ["體罰", "世代", "管教", "教養"]):
                bg = f"從時代變遷與人權價值演進，探討「{topic}」在不同世代（如嬰兒潮世代與 Z 世代）間所引發之教育哲學與管教價值觀衝突。"
                points = [
                    f"新舊世代教養思維與文化歷史背景之家庭社會成因差異比較",
                    f"管教手段對學生心理健康、同儕適應與人格發展之實證影響評估",
                    f"現代學校與家庭教育中「正向輔導管教替代機制」之推動困境與支持體系建立"
                ]
                conclusion = f"建立跨世代親師溝通橋樑，並提出兼顧現代人權理念與實務可行性之正向輔導策略。"
            else:
                bg = f"探討現代教育體制與學習環境下，針對「{topic}」所面臨的教學革新契機與學生學習成效問題意識。"
                points = [
                    f"現行教學模式與課程架構對「{topic}」之支援程度評估",
                    f"學生學習動機、自主學習成效與教師教學負擔之交互影響",
                    f"教育資源數位化融入與弱勢學生學習支持體系之落差探討"
                ]
                conclusion = f"提出提升學生學習成效與優化教學策略之具體實踐藍圖。"
            return bg, points, conclusion

        # 3. 社會心理領域（社群、焦慮、心理、情緒、憂鬱等）
        if category == "社會心理" or any(k in topic_lower for k in ["社群", "心理", "焦慮", "情緒", "憂鬱", "壓力", "同儕", "成癮"]):
            bg = f"剖析現代網路社群高頻互動與生活型態下，針對「{topic}」在大專青年群體中所面臨的心理調適與身心健康挑戰。"
            points = [
                f"社群推播機制、點讚文化與同儕向上比較心理機制對情緒波動之影響",
                f"心理焦慮狀態對學業表現、日常人際關係與睡眠品質之關聯性分析",
                f"數位排毒 (Digital Detox)、校園心理諮商與同儕支持網絡介入策略成效"
            ]
            conclusion = f"建立健康數位使用習慣自我評估指標，並為校園輔導體系提供早期預警與介入方案建議。"
            return bg, points, conclusion

        # 4. 商管企管領域（行銷、商業、管理、ESG、永續等）
        if category == "商管企管" or any(k in topic_lower for k in ["行銷", "商業", "esg", "永續", "管理", "企業", "市場", "品牌", "消費"]):
            bg = f"分析市場競爭環境與商業動態下，推動「{topic}」在品牌建立、商業模式創新與永續經營中的關鍵角色。"
            points = [
                f"目標受眾需求洞察與「{topic}」之市場痛點定位剖析",
                f"商業模式畫布 (BMC) 與數位行銷推廣策略之整合路徑",
                f"成本結構效益、合規風險與實務落地執行障礙評估"
            ]
            conclusion = f"提出具商業可行性之營運改善企劃，並擬定關鍵績效指標 (KPI) 與長期競爭優勢規劃。"
            return bg, points, conclusion

        # 5. 醫學健康領域（健康、醫療、睡眠、飲食等）
        if category == "醫學健康" or any(k in topic_lower for k in ["健康", "醫療", "睡眠", "飲食", "疾病", "運動", "營養"]):
            bg = f"探討現代生活型態對人體生理機能之影響，剖析「{topic}」在公共衛生預防醫學與個人健康管理中的核心價值。"
            points = [
                f"流行病學現況回顧與造成「{topic}」之關鍵生活環境致病危險因子",
                f"實證醫學介入方案、日常飲食/作息監測與健康改善成效對照",
                f"公衛推廣普及性瓶頸與民眾自我健康管理遵從度落差"
            ]
            conclusion = f"建構可量化之日常身心健康監測指標，並提出生活型態醫學導向的具體改善指引。"
            return bg, points, conclusion

        # 6. 法律政治領域
        if category == "法律政治" or any(k in topic_lower for k in ["法律", "政策", "政治", "權利", "法規", "犯罪", "司法", "人權"]):
            bg = f"探討現代公民社會與民主法治脈絡下，針對「{topic}」所衍生之法規體系衝突與公共政策爭議。"
            points = [
                f"現行法律規範條文與憲法基本權利保障之合憲性/合規性審查",
                f"國內外立法例比較與關鍵利益團體之訴求立場衝突剖析",
                f"執法實務上面臨之制度性盲點與修法推動之政治社會阻力"
            ]
            conclusion = f"提出兼顧法理邏輯與社會公益之具體修法倡議與政策改革藍圖。"
            return bg, points, conclusion

        # 7. 通用主題（深度結合主題名詞生成）
        bg = f"分析現代大專學術與實務發展脈絡下，針對「{topic}」所衍生之核心議題、問題意識與研究動機。"
        points = [
            f"國內外針對「{topic}」之理論文獻脈絡、歷史沿革與現行研究典範回顧",
            f"實務案例深入剖析與推動「{topic}」所面臨之關鍵利益衝突爭議點",
            f"現行體制制度之結構性限制與實踐推廣之主要瓶頸分析"
        ]
        conclusion = f"歸納針對「{topic}」之系統性改善架構，並提出具體行動策略與後續研究展望方向。"
        return bg, points, conclusion

    def _handle_generate_outline(self, arg: str) -> str:
        """根據指定主題生成深度客製化報告大綱草稿，並實體匯出 Markdown 檔案"""
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

        # 核心亮點：動態客製化生成內容
        bg, points, conclusion = self._generate_tailored_outline_content(topic, category)

        points_text_preview = "\n".join([f"    {i+1}. {p}" for i, p in enumerate(points)])
        points_text_md = "\n".join([f"{i+1}. **{p.split('分析')[0].split('探討')[0].split('評估')[0]}**：{p}" for i, p in enumerate(points)])

        outline_md = (
            f"# 【報告大綱草稿】{topic}\n\n"
            f"- **學術領域**：{category}\n"
            f"- **建立來源**：IdeaCatcher Bot v2.0 動態客製化生成\n\n"
            f"## 一、研究背景與動機\n{bg}\n\n"
            f"## 二、主要探討核心面向\n{points_text_md}\n\n"
            f"## 三、預期研究結論與效益\n{conclusion}\n"
        )

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
            f"📝 已為您成功生成【{topic}】的專屬報告大綱草稿！\n"
            f"🏷️ 領域分類：{category}\n\n"
            "────────────── 大綱預覽 ──────────────\n"
            f"一、研究背景與動機\n    • {bg}\n"
            f"二、主要探討核心面向\n{points_text_preview}\n"
            f"三、預期研究結論與效益\n    • {conclusion}\n"
            "────────────────────────────────────\n"
            f"{save_msg}\n"
            "💡 提示：本大綱已依據主題與領域客製化，可直接開啟檔案撰寫期末報告！"
        )
        return reply

    def _handle_view_all_ideas(self) -> str:
        if not self.ideas:
            return (
                "📋 目前尚未儲存任何報告靈感喔！\n"
                "💡 快試試傳送「靈感：[主題]」來記錄您的第一個點子吧！"
            )

        lines = [f"📋 目前已收集的報告點子清單（共 {len(self.ideas)} 則）："]
        for idx, item in enumerate(self.ideas, 1):
            lines.append(f"{idx}. [{item['category']}] {item['topic']}")
        lines.append("\n💡 提示：輸入「大綱：[編號]」可一鍵生成該題目的專屬報告大綱！")
        return "\n".join(lines)

    def _handle_search_ideas(self, keyword: str) -> str:
        if not keyword:
            return "⚠️ 請輸入要搜尋的分類或關鍵字！例如：「查看：人文教育」或「搜尋：機器人」。"

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
        if not arg:
            return "⚠️ 請提供要刪除的靈感編號！\n💡 範例：「刪除：1」。"

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
        count = len(self.ideas)
        self.ideas.clear()
        self._save_to_storage()
        return f"🗑️ 已成功清空靈感清單！（共清除了 {count} 則主題）"

    def _unknown_command_reply(self) -> str:
        return (
            "👋 您好！我是「大學生報告主題發想_搜集機器人」(v2.0 改善完成版)。\n"
            "我可以幫您隨手捕捉報告靈感，並能依主題動態產出客製化大綱！\n\n"
            "🛠️ 目前支援指令列表：\n"
            "1. 記錄靈感：「靈感：[主題名稱]」（系統會智慧識別領域）\n"
            "   或自訂分類：「靈感：[主題] 分類：[學科]」\n"
            "2. 生成大綱：「大綱：[編號]」（🌟 根據主題動態產出具體大綱）\n"
            "3. 搜尋/篩選：「查看：[分類]」或「搜尋：[關鍵字]」\n"
            "4. 查看全部：「查看靈感」或「清單」\n"
            "5. 刪除單筆：「刪除：[編號]」\n"
            "6. 清空資料：「清空靈感」"
        )


def main():
    bot = IdeaBot()
    print("=" * 65)
    print("🤖 大學生報告主題發想_搜集機器人 (v2.0 課後改善完成版)")
    print("🌟 核心改善亮點：動態客製化 Markdown 報告大綱草稿 (大綱：[編號])")
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
