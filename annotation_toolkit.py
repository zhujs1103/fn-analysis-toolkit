#!/usr/bin/env python3
"""
FN标注工具使用指南
========================

本工具提供两种标注方式的完整解决方案：
1. 自动标注 - AI快速分类（基于特征关键词匹配）
2. 手动复核 - Streamlit Web界面快速审阅和修改

"""

import subprocess
import sys
from pathlib import Path


class AnnotationToolkit:
    """FN标注工具包 - 编程接口"""
    
    @staticmethod
    def auto_annotate(csv_path: str, output_path: str = None,
                     skip_annotated: bool = True,
                     confidence_threshold: float = 0.3) -> None:
        """
        快速自动标注CSV文件
        
        使用示例：
        -----------
        from annotation_toolkit import AnnotationToolkit
        
        # 方式1：自动标注并覆盖原文件
        AnnotationToolkit.auto_annotate("path/to/data.csv")
        
        # 方式2：保存到新文件
        AnnotationToolkit.auto_annotate(
            "path/to/data.csv",
            output_path="path/to/output.csv"
        )
        
        # 方式3：跳过已标注的行，设置置信度阈值
        AnnotationToolkit.auto_annotate(
            "path/to/data.csv",
            skip_annotated=True,
            confidence_threshold=0.4
        )
        
        参数：
        -----
        csv_path : str
            输入CSV文件路径
        
        output_path : str, optional
            输出文件路径，默认覆盖原文件
        
        skip_annotated : bool, default=True
            是否跳过已有人工标注的行
        
        confidence_threshold : float, default=0.3
            置信度阈值，低于此值的标注会标记为待复核
        
        生成的列：
        --------
        - 自动原因分类: AI自动分类的原因
        - 置信度: 0-1之间的置信度分数
        - 是否标注问题: 自动检测是否存在标注错误
        - 待复核: 是否需要人工复核（置信度低）
        """
        result = subprocess.run(
            [sys.executable, "auto_annotate_fn.py",
             "--input", csv_path,
             "--confidence-threshold", str(confidence_threshold)],
            + (["--output", output_path] if output_path else [])
            + (["--skip-annotated"] if skip_annotated else []),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"自动标注失败：{result.stderr}")
        
        print(result.stdout)
    
    @staticmethod
    def launch_web_ui(csv_path: str = None) -> None:
        """
        启动Streamlit Web界面进行手动标注和复核
        
        使用示例：
        -----------
        from annotation_toolkit import AnnotationToolkit
        
        # 默认使用配置的CSV路径
        AnnotationToolkit.launch_web_ui()
        
        # 或指定CSV文件
        AnnotationToolkit.launch_web_ui("path/to/data.csv")
        
        界面功能：
        --------
        1. 查看自动标注结果和置信度
        2. 快速审阅和修改标注
        3. 数字快捷键 (1-6) 快速选择原因
        4. 按需筛选：全部、未标注、待复核
        5. 支持批量采用AI建议
        """
        cmd = [sys.executable, "-m", "streamlit", "run", "annotate_fn_enhanced.py"]
        
        if csv_path:
            # 通过环境变量传递CSV路径
            import os
            os.environ["FN_ANNOTATION_CSV"] = csv_path
        
        subprocess.run(cmd)
    
    @staticmethod
    def batch_process(csv_list: list, output_dir: str = None) -> None:
        """
        批量处理多个CSV文件
        
        使用示例：
        -----------
        from annotation_toolkit import AnnotationToolkit
        
        csv_files = [
            "data/batch1.csv",
            "data/batch2.csv",
            "data/batch3.csv"
        ]
        
        AnnotationToolkit.batch_process(
            csv_files,
            output_dir="outputs/annotated"
        )
        """
        output_dir = Path(output_dir) if output_dir else None
        
        for csv_path in csv_list:
            csv_path = Path(csv_path)
            if not csv_path.exists():
                print(f"⚠️ 跳过不存在的文件：{csv_path}")
                continue
            
            output_path = None
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / csv_path.name
            
            print(f"\n处理: {csv_path}")
            try:
                AnnotationToolkit.auto_annotate(
                    str(csv_path),
                    output_path=str(output_path) if output_path else None
                )
            except Exception as e:
                print(f"❌ 处理失败：{e}")


# ============================================
# 快速使用脚本
# ============================================

def print_usage():
    """打印使用指南"""
    guide = """
╔════════════════════════════════════════════════════════════════╗
║          FN 标注工具 - 完整使用指南                           ║
╚════════════════════════════════════════════════════════════════╝

📚 工具组成
===========
1️⃣  auto_annotate_fn.py
    ├─ 命令行工具，快速批量自动分类
    ├─ 基于特征关键词匹配
    └─ 生成置信度和待复核标记

2️⃣  annotate_fn_enhanced.py
    ├─ Streamlit Web界面
    ├─ 支持审阅AI结果和手动修改
    ├─ 智能过滤：全部/未标注/待复核
    └─ 快捷键操作，工作效率高

═══════════════════════════════════════════════════════════════

🚀 使用方式A - 命令行快速标注
===============================

# 基础使用（覆盖原文件）
python auto_annotate_fn.py --input data.csv

# 保存到新文件
python auto_annotate_fn.py --input data.csv --output output.csv

# 跳过已标注的行
python auto_annotate_fn.py --input data.csv --skip-annotated

# 自定义置信度阈值
python auto_annotate_fn.py --input data.csv --confidence-threshold 0.5

═══════════════════════════════════════════════════════════════

🎨 使用方式B - Web界面审阅
============================

# 启动Streamlit应用
streamlit run annotate_fn_enhanced.py

# 或在命令行中使用
python -m streamlit run annotate_fn_enhanced.py

浏览器会自动打开 http://localhost:8501

界面功能：
--------
✓ 左侧边栏
  - 输入CSV文件路径
  - 一键运行自动标注

✓ 顶部导航
  - 跳转到指定行号
  - 过滤模式（全部/未标注/待复核）
  - 统计信息（已标注数量）

✓ 主内容区
  - 左图：漏检样本
  - 右图：Query原图
  - AI预判结果和置信度

✓ 标注表单
  - 下拉框选择原因
  - 是否标注问题（是/否）
  - 输入备注说明

✓ 快捷键操作
  - 数字 1-6 快速选择原因
  - 数字 0 采用AI建议
  - 直接回车采用AI或当前选择

✓ 导航按钮
  - ⬅️ 上一条
  - 💾 保存
  - ✅ 采用AI建议
  - ➡️ 下一条
  - ⏭️ 跳过

═══════════════════════════════════════════════════════════════

🔧 使用方式C - Python编程接口
===============================

from annotation_toolkit import AnnotationToolkit

# 1. 自动标注（推荐先做这个）
AnnotationToolkit.auto_annotate("data.csv")

# 2. 启动Web界面进行复核和修改
AnnotationToolkit.launch_web_ui("data.csv")

# 3. 批量处理多个文件
csv_files = ["data1.csv", "data2.csv", "data3.csv"]
AnnotationToolkit.batch_process(csv_files, output_dir="outputs")

═══════════════════════════════════════════════════════════════

📊 工作流程建议
================

Step 1: 自动标注（5分钟）
  └─ python auto_annotate_fn.py --input data.csv
     生成：自动原因分类、置信度、待复核标记

Step 2: 审阅自动结果（视数据量而定）
  └─ streamlit run annotate_fn_enhanced.py
     选择过滤模式："待复核"，快速浏览低置信度结果
     使用快捷键快速确认或修改

Step 3: 手动标注未自动分类的（可选）
  └─ 在Web界面中过滤"未标注"
     逐个手动标注或采用AI建议

═══════════════════════════════════════════════════════════════

💡 建议用法
===========

场景1：快速验证数据
✓ auto_annotate_fn.py --input data.csv
✓ 几秒内完成4000+样本的分类
✓ 自动生成统计报告

场景2：人工复核+修改
✓ 先跑auto_annotate_fn.py
✓ 再用annotate_fn_enhanced.py
✓ 过滤"待复核"批量确认AI结果
✓ 快捷键0一次性采用正确的AI建议

场景3：多批次处理
✓ 创建文件列表
✓ 使用AnnotationToolkit.batch_process()
✓ 或写循环调用auto_annotate_fn.py

═══════════════════════════════════════════════════════════════

🎯 快捷键速查表
================

在Streamlit Web界面中：

数字快速选择：
  1  →  遮挡
  2  →  目标尺寸过小
  3  →  光照/模糊问题
  4  →  背景干扰
  5  →  标注问题
  6  →  其他异常
  
特殊操作：
  0  →  采用AI建议
  Enter (空)  →  采用AI或当前选择

═══════════════════════════════════════════════════════════════

❓ 常见问题
===========

Q: 自动标注的准确度如何？
A: 基于特征关键词匹配，不同数据质量下准确度有差异。
   建议先审阅低置信度结果（待复核列）。

Q: 能否同时修改多条记录？
A: 目前是单条编辑。如需批量修改，请用pandas脚本。

Q: CSV列名有要求吗？
A: 支持自定义列名，脚本会自动识别。
   建议保留：image_path, query_image_path, mode等。

Q: 数据量很大（100k+），如何处理？
A: 1. 先自动标注（1-2分钟）
   2. 在Web界面过滤"待复核"进行针对性复核
   3. 必要时分批处理

═══════════════════════════════════════════════════════════════

✨ 输出结果说明
================

运行auto_annotate_fn.py后，CSV会新增以下列：

自动原因分类 (auto_reason):
  - 遮挡
  - 目标尺寸过小
  - 光照/模糊问题
  - 背景干扰
  - 标注问题
  - 其他异常

置信度 (confidence):
  - 0-1之间的值
  - >0.5 表示高置信度 🟢
  - 0.3-0.5 表示中置信度 🟡
  - <0.3 表示低置信度 🔴

是否标注问题 (label_issue):
  - "是" / "否"
  - 自动检测样本是否有标注错误

待复核 (need_review):
  - True / False
  - 置信度低于阈值时自动标记

═══════════════════════════════════════════════════════════════
"""
    print(guide)


if __name__ == "__main__":
    print_usage()
    
    print("\n\n快速开始：")
    print("=" * 60)
    print("1️⃣  自动标注你的CSV文件：")
    print("   python auto_annotate_fn.py --input your_data.csv")
    print("\n2️⃣  启动Web界面复核结果：")
    print("   streamlit run annotate_fn_enhanced.py")
    print("\n3️⃣  或使用编程接口：")
    print("   from annotation_toolkit import AnnotationToolkit")
    print("   AnnotationToolkit.auto_annotate('your_data.csv')")
    print("=" * 60)
