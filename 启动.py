#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ 简单启动脚本 - 直接启动标注Web界面
"""

import subprocess
import sys
import os
from pathlib import Path

print("\n" + "="*70)
print("🚀 启动FN标注Web界面")
print("="*70 + "\n")

# 确保在正确的目录
os.chdir(Path(__file__).parent)
print(f"工作目录: {Path.cwd()}\n")

# 检查CSV文件
csv_file = Path("outputs/fn_analysis/manual_annotation_template_with_paths.csv")
if csv_file.exists():
    print(f"✓ 找到标注文件: {csv_file}")
    print(f"  文件大小: {csv_file.stat().st_size / 1024:.1f} KB\n")
else:
    print(f"⚠️ 警告：找不到标注文件: {csv_file}")
    print("  但Web界面可能有默认配置，继续启动...\n")

# 启动Streamlit
print("启动Web服务...")
print("浏览器会自动打开 http://localhost:8501\n")
print("-" * 70)
print()

try:
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "annotate_fn_enhanced.py"],
        check=False
    )
except KeyboardInterrupt:
    print("\n\n✅ Web服务已关闭")
    print("📌 提示：所有标注数据已自动保存到CSV文件")
except Exception as e:
    print(f"\n❌ 错误: {e}")
    sys.exit(1)
