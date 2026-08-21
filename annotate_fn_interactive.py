import argparse
import os
from pathlib import Path
from typing import Dict

import pandas as pd


DEFAULT_CSV = Path("outputs/fn_analysis/manual_annotation_template_with_paths.csv")

REASON_MAP: Dict[str, str] = {
    "1": "遮挡",
    "2": "目标尺寸过小",
    "3": "光照/模糊问题",
    "4": "背景干扰",
    "5": "标注问题",
    "6": "其他异常",
}


def open_if_exists(path_str: str) -> None:
    if not path_str:
        return
    s = str(path_str).strip()
    if not s or s.lower() in {"nan", "none"}:
        return
    p = Path(s)
    if p.exists():
        os.startfile(str(p))  # Windows


def print_menu() -> None:
    print("\n可选分类：")
    for k, v in REASON_MAP.items():
        print(f"  {k}. {v}")
    print("  s. 跳过本条")
    print("  q. 退出并保存")


def normalize_reason(user_input: str) -> str:
    text = user_input.strip()
    if text in REASON_MAP:
        return REASON_MAP[text]
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="自动弹图 + 交互标注 + 下一条")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="标注CSV路径")
    parser.add_argument("--start-line", type=int, help="从CSV真实行号开始（含表头）")
    parser.add_argument("--start-row", type=int, help="从数据行号开始（不含表头，从1开始）")
    parser.add_argument("--limit", type=int, default=0, help="最多处理多少条，0表示不限制")
    args = parser.parse_args()

    if args.start_line is None and args.start_row is None:
        # 默认从第一条数据行开始
        start_idx = 0
    elif args.start_line is not None:
        start_idx = args.start_line - 2
    else:
        start_idx = args.start_row - 1

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 不存在: {csv_path}")

    df = pd.read_csv(csv_path)
    if start_idx < 0 or start_idx >= len(df):
        raise IndexError(f"起始位置无效，允许范围: 0 ~ {len(df)-1}")

    processed = 0
    for i in range(start_idx, len(df)):
        if args.limit > 0 and processed >= args.limit:
            break

        row = df.iloc[i]
        line_no = i + 2
        print("\n" + "=" * 70)
        print(f"CSV行号: {line_no} | 数据行号: {i+1}/{len(df)}")
        print(f"mode: {row.get('mode', '')} | target_person: {row.get('target_person', '')}")
        print(f"fn_file_path: {row.get('fn_file_path', '')} | score: {row.get('score', '')}")
        print(f"当前人工原因分类: {row.get('人工原因分类', '')}")
        print("=" * 70)

        # 每条固定弹出两张图：当前待标注图 + query原图
        open_if_exists(str(row.get("image_path", "")))
        open_if_exists(str(row.get("query_image_path", "")))

        print_menu()
        reason_input = input("输入分类(1-6/直接中文/s/q): ").strip()
        if reason_input.lower() == "q":
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"\n已保存并退出：{csv_path}")
            print(f"下次可从 --start-line {line_no} 继续。")
            return
        if reason_input.lower() == "s":
            processed += 1
            continue

        reason = normalize_reason(reason_input)
        if reason:
            df.at[i, "人工原因分类"] = reason

        mark_issue = input("是否标注问题(y/n, 回车跳过): ").strip().lower()
        if mark_issue == "y":
            df.at[i, "是否标注问题"] = "是"
        elif mark_issue == "n":
            df.at[i, "是否标注问题"] = "否"

        note = input("标注备注(回车跳过): ").strip()
        if note:
            df.at[i, "标注备注"] = note

        # 每条都落盘，防止中断丢失
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"[已保存] 行 {line_no}")
        processed += 1

    print(f"\n已处理完成，结果已保存：{csv_path}")


if __name__ == "__main__":
    main()

