#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键启动标注流程
1. 自动标注
2. 启动Web界面进行人工审阅
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("\n" + "="*70)
    print("📋 FN标注流程 - 一键启动")
    print("="*70 + "\n")
    
    # 确定CSV文件路径
    csv_path = Path("outputs/fn_analysis/manual_annotation_template_with_paths.csv")
    
    if not csv_path.exists():
        print(f"❌ 错误：找不到CSV文件: {csv_path}")
        return
    
    print(f"✓ 找到标注文件: {csv_path}")
    
    # Step 1: 自动标注
    print("\n" + "-"*70)
    print("Step 1️⃣ : 运行自动标注...")
    print("-"*70)
    
    result = subprocess.run(
        [sys.executable, "auto_annotate_fn.py", "--input", str(csv_path)],
        capture_output=False,
        text=True
    )
    
    if result.returncode != 0:
        print("❌ 自动标注失败")
        return
    
    # Step 2: 启动Web界面
    print("\n" + "-"*70)
    print("Step 2️⃣ : 启动Web界面进行人工审阅...")
    print("-"*70)
    print("""
✓ Web界面即将启动
✓ 打开浏览器访问: http://localhost:8501

📝 如何操作：
  1. 选择过滤模式"待复核"快速找到需要复核的样本
  2. 使用快捷键快速操作：
     - 按数字 1-6 快速选择原因
     - 按 0 采用AI建议
     - 按 Enter 直接提交
  3. 也可以手动选择，然后点击按钮保存

按 Ctrl+C 可以退出Web界面（数据已自动保存到CSV）
    """)
    
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "annotate_fn_enhanced.py",
         "--", "--csv", str(csv_path)]
    )

if __name__ == "__main__":
    main()
