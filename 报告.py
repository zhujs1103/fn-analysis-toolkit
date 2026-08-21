#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成当前标注项目的总结报告
"""

import pandas as pd
from pathlib import Path

def generate_report():
    """生成标注进度报告"""
    
    csv_path = Path("outputs/fn_analysis/manual_annotation_template_with_paths.csv")
    df = pd.read_csv(csv_path)
    
    print("\n" + "="*70)
    print("📊 FN标注项目 - 现状报告")
    print("="*70 + "\n")
    
    # 基础统计
    total = len(df)
    print(f"📈 样本总数")
    print(f"   └─ 总计: {total:,} 条\n")
    
    # 人工标注统计
    labeled = df[df['人工原因分类'].notna() & (df['人工原因分类'].astype(str).str.strip() != '')]
    unlabeled = df[df['人工原因分类'].isna() | (df['人工原因分类'].astype(str).str.strip() == '')]
    
    print(f"👤 人工标注进度")
    print(f"   ├─ 已标注: {len(labeled):,} 条 ({len(labeled)/total*100:.1f}%)")
    print(f"   └─ 未标注: {len(unlabeled):,} 条 ({len(unlabeled)/total*100:.1f}%)\n")
    
    # 人工标注分布
    if len(labeled) > 0:
        print(f"🏷️ 已标注样本原因分布")
        reason_dist = labeled['人工原因分类'].value_counts()
        for reason, count in reason_dist.items():
            pct = count / len(labeled) * 100
            print(f"   ├─ {reason:15} : {count:5} 条 ({pct:6.2f}%)")
        print()
    
    # 自动标注统计
    auto_labeled = df[df['自动原因分类'].notna() & (df['自动原因分类'].astype(str).str.strip() != '')]
    auto_unlabeled = df[df['自动原因分类'].isna() | (df['自动原因分类'].astype(str).str.strip() == '')]
    
    print(f"🤖 自动标注统计")
    print(f"   ├─ 已自动标注: {len(auto_labeled):,} 条 ({len(auto_labeled)/total*100:.1f}%)")
    print(f"   └─ 未自动标注: {len(auto_unlabeled):,} 条 ({len(auto_unlabeled)/total*100:.1f}%)\n")
    
    # 待复核统计
    need_review = df[df['待复核'] == True].shape[0]
    print(f"⚠️ 需要复核的项目")
    print(f"   └─ 待复核: {need_review:,} 条 ({need_review/total*100:.1f}%)\n")
    
    # 模式分布
    print(f"📷 样本类型分布")
    mode_dist = df['mode'].value_counts()
    for mode, count in mode_dist.items():
        print(f"   ├─ {mode:10} : {count:5} 条 ({count/total*100:6.2f}%)")
    print()
    
    # 下一步建议
    print(f"✅ 下一步建议")
    print(f"""
   1️⃣  启动Web标注界面
       python 启动标注界面.py
       或
       streamlit run annotate_fn_enhanced.py
   
   2️⃣  选择过滤模式
       ├─ 建议先看"未标注" - 优先标注没有标注的样本
       └─ 其次看"全部" - 完整检查所有样本
   
   3️⃣  快速标注技巧
       ├─ 使用快捷键 1-6 快速选择原因
       ├─ 按 0 采用AI建议（如有）
       ├─ 按 Enter 直接提交并跳到下一条
       └─ "跳过"按钮用于暂时跳过某个样本
   
   4️⃣  标注完成后
       ├─ CSV自动保存
       ├─ 按 Ctrl+C 退出Web界面
       └─ 数据已安全保存到CSV
    """)
    
    print("="*70)
    
    # 样本模式详细信息
    print(f"\n🔍 样本模式详情\n")
    
    for mode in df['mode'].unique():
        mode_df = df[df['mode'] == mode]
        mode_labeled = mode_df[mode_df['人工原因分类'].notna() & 
                               (mode_df['人工原因分类'].astype(str).str.strip() != '')]
        
        print(f"  📱 {mode.upper()}")
        print(f"     ├─ 总数: {len(mode_df):,}")
        print(f"     ├─ 已标注: {len(mode_labeled):,} ({len(mode_labeled)/len(mode_df)*100:.1f}%)")
        print(f"     └─ 待标注: {len(mode_df) - len(mode_labeled):,}")
        
        if len(mode_labeled) > 0:
            reason_dist = mode_labeled['人工原因分类'].value_counts()
            for reason, count in reason_dist.items():
                print(f"        ├─ {reason}: {count}")
        print()
    
    return df

if __name__ == "__main__":
    generate_report()
