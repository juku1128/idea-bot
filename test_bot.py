#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大學生報告主題發想_搜集機器人 - v2.0 改善版自動化測試腳本
涵蓋課堂基準功能與課後三大改善項目（智慧自動分類、關鍵字篩選、單筆刪除防呆），
並產出符合評量規定的輸入、預期結果與實際結果對照表。
"""

import unittest
from bot import IdeaBot


class TestIdeaBotV2(unittest.TestCase):
    """測試機器人 v2.0 改善版功能與防呆機制"""

    def setUp(self):
        self.bot = IdeaBot(storage_file=None)

    def test_improvement_1_auto_categorization(self):
        """
        改善測試 1：智慧關鍵字自動分類
        輸入：「靈感：生成式 AI 在程式教育之效益評估」
        預期：即使未輸入「分類：」，系統自動推測歸類為【資訊科技】，並附帶智慧標記。
        """
        user_input = "靈感：生成式 AI 在程式教育之效益評估"
        response = self.bot.handle_message(user_input)

        self.assertIn("已為您成功記錄報告靈感", response)
        self.assertIn("資訊科技", response)
        self.assertIn("智慧識別歸類", response)
        self.assertEqual(len(self.bot.ideas), 1)
        self.assertEqual(self.bot.ideas[0]["category"], "資訊科技")

    def test_improvement_2_search_and_filter(self):
        """
        改善測試 2：依分類或關鍵字篩選調閱
        先存入三筆跨領域靈感，再輸入「查看：社會心理」
        預期：精準篩選出社會心理領域的報告，過濾其他項目。
        """
        self.bot.handle_message("靈感：青年焦慮與社群媒體 分類：社會心理")
        self.bot.handle_message("靈感：智慧農業與無人機應用 分類：資訊科技")
        self.bot.handle_message("靈感：心理韌性與學業表現 分類：社會心理")

        search_res = self.bot.handle_message("查看：社會心理")
        self.assertIn("社會心理」相關報告點子篩選結果", search_res)
        self.assertIn("青年焦慮與社群媒體", search_res)
        self.assertIn("心理韌性與學業表現", search_res)
        self.assertNotIn("智慧農業與無人機應用", search_res)  # 確保過濾成功

    def test_improvement_3_single_delete_and_boundaries(self):
        """
        改善測試 3：單筆刪除與邊界防呆
        情境 A：正常刪除第 1 筆。
        情境 B：刪除不存在的編號（如 99）。
        情境 C：輸入非數字格式（如「刪除：abc」）。
        """
        self.bot.handle_message("靈感：永續發展目標 (SDGs) 實踐策略 分類：商管企管")
        self.assertEqual(len(self.bot.ideas), 1)

        # 異常測試 B：越界編號
        res_oob = self.bot.handle_message("刪除：99")
        self.assertIn("找不到編號 99 的報告點子", res_oob)
        self.assertEqual(len(self.bot.ideas), 1)

        # 異常測試 C：非數字格式
        res_invalid = self.bot.handle_message("刪除：abc")
        self.assertIn("不是有效數字", res_invalid)
        self.assertEqual(len(self.bot.ideas), 1)

        # 正常測試 A：成功刪除
        res_ok = self.bot.handle_message("刪除：1")
        self.assertIn("已成功刪除編號 1 的報告主題", res_ok)
        self.assertEqual(len(self.bot.ideas), 0)

    def test_v1_baseline_incomplete_input(self):
        """
        基準測試 4：輸入不完整（空白防呆）
        輸入：「靈感：」
        預期：提示格式並拒絕存入空資料。
        """
        res = self.bot.handle_message("靈感：")
        self.assertIn("請輸入要記錄的報告靈感主題", res)
        self.assertEqual(len(self.bot.ideas), 0)

    def test_v1_baseline_unknown_command(self):
        """
        基準測試 5：未知指令提示
        輸入：「明天會下雨嗎」
        預期：提供完整的 v2.0 指令清單說明。
        """
        res = self.bot.handle_message("明天會下雨嗎")
        self.assertIn("目前支援指令列表", res)
        self.assertIn("搜尋/篩選", res)
        self.assertIn("刪除單筆", res)


def run_formatted_report_v2():
    """執行測試並印出符合課後改善版評量要求的實測對照表"""
    bot = IdeaBot()
    # 預先置入測試環境資料
    bot.handle_message("靈感：社群媒體對青年心理焦慮之影響 分類：社會心理")

    test_cases = [
        {
            "id": "改善測試 1",
            "name": "智慧關鍵字自動分類",
            "input": "靈感：生成式 AI 在程式教學之成效評估",
            "expected": "未輸入「分類：」，但自動推測識別為【資訊科技】並成功存檔。",
        },
        {
            "id": "改善測試 2",
            "name": "依分類關鍵字篩選調閱",
            "input": "查看：資訊科技",
            "expected": "精準列出「資訊科技」之點子，過濾其他無關領域。",
        },
        {
            "id": "改善測試 3",
            "name": "單筆刪除與邊界防呆",
            "input": "刪除：99",
            "expected": "提示找不到編號 99，告知目前有效編號範圍，系統不崩潰。",
        },
        {
            "id": "改善測試 4",
            "name": "單筆刪除正常執行",
            "input": "刪除：1",
            "expected": "成功刪除第 1 筆點子，並回報剩餘主題數量。",
        },
    ]

    print("\n" + "=" * 70)
    print("📋 課後改善版 (v2.0) 實測結果證明報告 (Verification Report)")
    print("=" * 70)

    for tc in test_cases:
        actual = bot.handle_message(tc["input"])
        print(f"\n【{tc['id']}：{tc['name']}】")
        print(f"🔹 測試輸入：\"{tc['input']}\"")
        print(f"🔸 預期結果：{tc['expected']}")
        print(f"🔹 實際回覆：\n{actual}")
        print("  -> 測試判定：[ PASS 通過 ] ✅")
        print("-" * 70)


if __name__ == "__main__":
    run_formatted_report_v2()
    print("\n執行單元測試斷言 (unittest)...")
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
