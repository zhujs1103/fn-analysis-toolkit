import argparse
import os
from pathlib import Path

import pandas as pd


DEFAULT_CSV = Path("outputs/fn_analysis/manual_annotation_template_with_paths.csv")


def open_path(path_str: str, print_only: bool = False) -> None:
    if not path_str:
        return
    if str(path_str).strip().lower() in {"nan", "none"}:
        return
    p = Path(path_str)
    if not p.exists():
        print(f"[WARN] 路径不存在: {p}")
        return
    print(f"[OPEN] {p}")
    if not print_only:
        os.startfile(str(p))  # Windows


def get_row_by_line(df: pd.DataFrame, line_number: int) -> pd.Series:
    # CSV 文件中：第1行为表头；第2行对应 df 的第0行
    idx = line_number - 2
    if idx < 0 or idx >= len(df):
        raise IndexError(f"line_number 超出范围: {line_number}，有效范围是 2 ~ {len(df) + 1}")
    return df.iloc[idx]


def get_row_by_index(df: pd.DataFrame, row_index: int) -> pd.Series:
    # 1-based row index (excluding header)
    idx = row_index - 1
    if idx < 0 or idx >= len(df):
        raise IndexError(f"row_index 超出范围: {row_index}，有效范围是 1 ~ {len(df)}")
    return df.iloc[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="按行号打开标注样本相关路径（图片/文本）。")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="标注CSV路径")
    parser.add_argument("--line", type=int, help="CSV真实行号（含表头）")
    parser.add_argument("--row", type=int, help="数据行号（不含表头，从1开始）")
    parser.add_argument("--print-only", action="store_true", help="只打印路径，不实际打开")
    args = parser.parse_args()

    if args.line is None and args.row is None:
        raise ValueError("请至少提供 --line 或 --row 其中一个参数。")

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 不存在: {csv_path}")

    df = pd.read_csv(csv_path)

    row = get_row_by_line(df, args.line) if args.line is not None else get_row_by_index(df, args.row)

    print("\n===== 当前样本 =====")
    print(f"mode: {row.get('mode', '')}")
    print(f"target_person: {row.get('target_person', '')}")
    print(f"fn_file_path: {row.get('fn_file_path', '')}")
    print(f"score: {row.get('score', '')}")
    print(f"auto_reason: {row.get('auto_reason', '')}")
    print("===================\n")

    image_path = str(row.get("image_path", "") or "")
    query_image_path = str(row.get("query_image_path", "") or "")
    query_text_path = str(row.get("query_text_path", "") or "")

    open_path(image_path, print_only=args.print_only)
    open_path(query_image_path, print_only=args.print_only)
    open_path(query_text_path, print_only=args.print_only)


if __name__ == "__main__":
    main()

