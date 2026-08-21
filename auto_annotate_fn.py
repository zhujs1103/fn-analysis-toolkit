#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动标注工具 - 用AI自动分类漏检原因，然后批量保存
支持timrReverse项目格式的CSV数据
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import argparse


# 漏检原因的标准分类与关键词
FN_REASON_KEYWORDS = {
    "遮挡": ["occlusion", "遮", "遮挡", "挡住", "blocked", "obstruct"],
    "目标尺寸过小": ["small", "tiny", "尺寸小", "太小", "size small", "小目标"],
    "光照/模糊问题": ["light", "illumination", "明亮", "暗", "光照", "brightness", "dark", "blur", "blurry", "模糊"],
    "背景干扰": ["background", "背景", "干扰", "混乱", "cluttered", "複雑"],
    "标注问题": ["annotation", "标注", "标记", "label", "error"],
    "其他异常": ["other", "未知", "不确定", "异常"],
}


def parse_original_data(data_str: str) -> Dict:
    """解析原始数据JSON"""
    try:
        if isinstance(data_str, str):
            return json.loads(data_str)
        return data_str
    except:
        return {}


def extract_text_features(row: pd.Series) -> str:
    """从行数据中提取所有文本特征，用于特征匹配"""
    text_parts = []
    
    # 从各列提取文本
    for col in row.index:
        if col in ['人工原因分类', '自动原因分类', '标注备注', '置信度']:
            continue
        
        val = str(row[col]).lower() if pd.notna(row[col]) else ""
        if val:
            text_parts.append(val)
    
    return " ".join(text_parts)


def smart_classify_reason(row: pd.Series) -> Tuple[str, float]:
    """
    智能分类漏检原因
    
    Args:
        row: CSV行数据
    
    Returns:
        (分类原因, 置信度)
    """
    
    # 提取所有文本特征
    text_features = extract_text_features(row)
    
    # 计算每个原因的匹配分数
    scores = defaultdict(int)
    
    for reason, keywords in FN_REASON_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_features:
                scores[reason] += 1
    
    # 获得分数最高的原因
    if scores:
        best_reason = max(scores.items(), key=lambda x: x[1])[0]
        max_score = scores[best_reason]
    else:
        best_reason = "其他异常"
        max_score = 0
    
    # 计算置信度（0-1之间）
    total_keywords = sum(len(keywords) for keywords in FN_REASON_KEYWORDS.values())
    confidence = min(1.0, max_score / max(1, len(FN_REASON_KEYWORDS.get(best_reason, []))))
    
    return best_reason, confidence


def auto_detect_label_issue(row: pd.Series) -> str:
    """
    自动检测是否存在标注问题
    
    Returns:
        "是" / "否"
    """
    text_features = extract_text_features(row)
    
    # 检测标注问题的关键词
    label_issue_keywords = ["标注错误", "标注问题", "annotation error", "label error", "错误标注", "标注不一致"]
    
    for keyword in label_issue_keywords:
        if keyword.lower() in text_features:
            return "是"
    
    return "否"


def batch_auto_annotate(csv_path: Path, output_path: Path = None, 
                        skip_annotated: bool = True,
                        confidence_threshold: float = 0.3) -> pd.DataFrame:
    """
    批量自动标注CSV文件
    
    Args:
        csv_path: 输入CSV文件路径
        output_path: 输出CSV文件路径（默认覆盖原文件）
        skip_annotated: 是否跳过已标注的行
        confidence_threshold: 置信度阈值，低于此值的标注会标记为待复核
    
    Returns:
        标注后的DataFrame
    """
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV文件不存在: {csv_path}")
    
    # 加载数据
    df = pd.read_csv(csv_path, encoding='utf-8')
    print(f"✓ 已加载 {len(df)} 条记录")
    
    # 初始化新列（如果不存在）
    if '自动原因分类' not in df.columns:
        df['自动原因分类'] = ""
    if '置信度' not in df.columns:
        df['置信度'] = 0.0
    if '是否标注问题' not in df.columns:
        df['是否标注问题'] = ""
    if '待复核' not in df.columns:
        df['待复核'] = False
    
    # 遍历每一行进行标注
    annotated_count = 0
    skipped_count = 0
    low_confidence_count = 0
    
    for idx, row in df.iterrows():
        # 检查是否跳过已标注
        if skip_annotated:
            human_reason = str(row.get('人工原因分类', '')).strip()
            if human_reason:
                skipped_count += 1
                continue
        
        # 自动分类
        reason, confidence = smart_classify_reason(row)
        
        # 自动检测标注问题
        label_issue = auto_detect_label_issue(row)
        
        # 更新DataFrame
        df.at[idx, '自动原因分类'] = reason
        df.at[idx, '置信度'] = round(confidence, 3)
        df.at[idx, '是否标注问题'] = label_issue
        
        # 标记低置信度为待复核
        if confidence < confidence_threshold:
            df.at[idx, '待复核'] = True
            low_confidence_count += 1
        else:
            df.at[idx, '待复核'] = False
        
        annotated_count += 1
        
        if (idx + 1) % 500 == 0:
            print(f"  已处理 {idx + 1}/{len(df)} 条记录...")
    
    # 保存结果
    if output_path is None:
        output_path = csv_path
    
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n✓ 已保存到: {output_path}")
    
    # 打印统计
    print(f"""
📊 自动标注统计：
  ├─ 新标注: {annotated_count} 条
  ├─ 已跳过（已有人工标注）: {skipped_count} 条
  ├─ 低置信度（<{confidence_threshold}）: {low_confidence_count} 条
  └─ 总计: {len(df)} 条

🔍 标注原因分布：
""")
    
    reason_counts = df['自动原因分类'].value_counts()
    for reason, count in reason_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {reason:15} : {count:5} 个 ({pct:6.2f}%)")
    
    return df


def review_low_confidence(df: pd.DataFrame, csv_path: Path) -> None:
    """
    显示低置信度的标注结果供人工审核
    """
    low_conf_df = df[df['待复核'] == True]
    
    if len(low_conf_df) == 0:
        print("✅ 所有标注都有较高置信度，无需复核")
        return
    
    print(f"\n⚠️  需要人工复核的低置信度标注 ({len(low_conf_df)} 条):\n")
    
    for idx, row in low_conf_df.head(10).iterrows():
        print(f"行号 {idx + 1}:")
        print(f"  自动分类: {row['自动原因分类']} (置信度: {row['置信度']:.2f})")
        print(f"  样本信息: ...")
        print()


def main():
    parser = argparse.ArgumentParser(description='自动标注FN样本的漏检原因')
    parser.add_argument('--input', '-i', type=str, required=True, 
                       help='输入CSV文件路径')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='输出CSV文件路径（默认覆盖原文件）')
    parser.add_argument('--skip-annotated', action='store_true', default=True,
                       help='跳过已有人工标注的行')
    parser.add_argument('--confidence-threshold', type=float, default=0.3,
                       help='置信度阈值（低于此值标记为待复核）')
    
    args = parser.parse_args()
    
    csv_path = Path(args.input)
    output_path = Path(args.output) if args.output else csv_path
    
    print("🚀 开始自动标注\n")
    
    try:
        df = batch_auto_annotate(
            csv_path,
            output_path,
            skip_annotated=args.skip_annotated,
            confidence_threshold=args.confidence_threshold
        )
        
        # 显示低置信度结果
        review_low_confidence(df, csv_path)
        
        print("\n✅ 自动标注完成！")
        print(f"📂 结果已保存到: {output_path}")
        
    except Exception as e:
        print(f"❌ 出错: {e}")
        raise


if __name__ == "__main__":
    main()
