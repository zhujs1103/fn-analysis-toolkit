#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的FN标注工具 - 同时支持自动标注审阅和手动标注
Streamlit应用，用于快速复核自动标注结果和手动标注
"""

from pathlib import Path
from typing import List, Optional
import pandas as pd
import streamlit as st
import subprocess
import sys


DEFAULT_CSV = Path("outputs/fn_analysis/manual_annotation_template_with_paths.csv")

REASON_OPTIONS: List[str] = [
    "",
    "遮挡",
    "目标尺寸过小",
    "光照/模糊问题",
    "背景干扰",
    "标注问题",
    "其他异常",
]


def load_df(csv_path: Path) -> pd.DataFrame:
    """加载CSV文件"""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 不存在: {csv_path}")
    return pd.read_csv(csv_path, encoding='utf-8')


def safe_str(v) -> str:
    """将值转换为字符串"""
    if pd.isna(v):
        return ""
    return str(v)


def save_row(df: pd.DataFrame, idx: int, csv_path: Path, 
             reason: str, label_issue: str, note: str) -> None:
    """保存单行标注结果"""
    df.at[idx, "人工原因分类"] = reason
    df.at[idx, "是否标注问题"] = label_issue
    df.at[idx, "标注备注"] = note
    df.to_csv(csv_path, index=False, encoding='utf-8')


def goto_next_index(df: pd.DataFrame, idx: int, 
                   filter_mode: str = "all") -> int:
    """
    跳转到下一条记录
    
    Args:
        filter_mode: "all" - 全部, "unlabeled" - 未手动标注, 
                   "low_confidence" - 低置信度需要复核
    """
    total = len(df)
    
    if filter_mode == "all":
        return min(total - 1, idx + 1)
    
    elif filter_mode == "unlabeled":
        # 未标注的行
        unlabeled_idx = df.index[df["人工原因分类"].isna() | 
                                (df["人工原因分类"].astype(str).str.strip() == "")]
        next_candidates = [x for x in unlabeled_idx if x > idx]
        return int(next_candidates[0]) if next_candidates else idx
    
    elif filter_mode == "low_confidence":
        # 需要复核的行（低置信度自动标注）
        low_conf_idx = df.index[(df.get('待复核', False) == True) | 
                               (df.get('待复核', False) == "True")]
        next_candidates = [x for x in low_conf_idx if x > idx]
        return int(next_candidates[0]) if next_candidates else idx
    
    return idx


def run_auto_annotation(csv_path: Path) -> bool:
    """在后台运行自动标注脚本"""
    try:
        result = subprocess.run(
            [sys.executable, "auto_annotate_fn.py", "--input", str(csv_path)],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            st.success("✅ 自动标注完成！")
            return True
        else:
            st.error(f"❌ 自动标注失败：{result.stderr}")
            return False
    except Exception as e:
        st.error(f"❌ 执行错误：{str(e)}")
        return False


def main() -> None:
    st.set_page_config(page_title="FN增强标注工具", layout="wide")
    st.title("🔧 FN 标注工具 - 增强版（自动+手动）")
    
    # ============ 侧边栏设置 ============
    with st.sidebar:
        st.header("⚙️ 工具设置")
        
        csv_input = st.text_input("CSV 路径", value=str(DEFAULT_CSV))
        csv_path = Path(csv_input)
        
        st.markdown("---")
        st.subheader("🤖 自动标注")
        
        if st.button("▶️ 运行自动标注脚本", use_container_width=True):
            with st.spinner("正在运行自动标注..."):
                if run_auto_annotation(csv_path):
                    st.rerun()
        
        st.caption("自动检测漏检原因，基于样本特征进行分类")
    
    # ============ 加载数据 ============
    try:
        df = load_df(csv_path)
    except Exception as e:
        st.error(str(e))
        return
    
    if "row_idx" not in st.session_state:
        st.session_state.row_idx = 0
    
    total = len(df)
    
    # ============ 顶部导航和过滤 ============
    col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.2, 1.6])
    
    with col1:
        jump_row = st.number_input(
            "跳转到行（1开始）", 
            min_value=1, 
            max_value=max(1, total), 
            value=st.session_state.row_idx + 1
        )
    
    with col2:
        filter_mode = st.selectbox(
            "过滤模式",
            options=["all", "unlabeled", "low_confidence"],
            format_func=lambda x: {
                "all": "📋 全部",
                "unlabeled": "⭕ 未标注",
                "low_confidence": "⚠️ 待复核"
            }[x]
        )
    
    with col3:
        # 统计信息
        manual_labeled = len(df[df["人工原因分类"].notna() & 
                               (df["人工原因分类"].astype(str).str.strip() != "")])
        st.metric("已手动标注", f"{manual_labeled}/{total}")
    
    with col4:
        # 自动标注统计
        if '自动原因分类' in df.columns:
            auto_labeled = len(df[df["自动原因分类"].notna() & 
                                  (df["自动原因分类"].astype(str).str.strip() != "")])
            st.metric("自动预标注", f"{auto_labeled}/{total}")
    
    # 跳转按钮
    if st.button("🔍 跳转", use_container_width=True):
        st.session_state.row_idx = int(jump_row) - 1
    
    # 应用过滤
    if filter_mode == "unlabeled":
        unlabeled_idx = df.index[df["人工原因分类"].isna() | 
                                (df["人工原因分类"].astype(str).str.strip() == "")]
        if len(unlabeled_idx) == 0:
            st.success("✅ 全部已手动标注！")
            return
        if st.session_state.row_idx not in unlabeled_idx:
            st.session_state.row_idx = int(unlabeled_idx[0])
    
    elif filter_mode == "low_confidence":
        if '待复核' in df.columns:
            low_conf_idx = df.index[df["待复核"] == True]
            if len(low_conf_idx) == 0:
                st.info("✅ 无需复核的低置信度标注")
                return
            if st.session_state.row_idx not in low_conf_idx:
                st.session_state.row_idx = int(low_conf_idx[0])
    
    idx = max(0, min(st.session_state.row_idx, total - 1))
    row = df.iloc[idx]
    
    # ============ 主内容区 ============
    st.markdown(f"### 📍 当前: 第 `{idx + 1}` / `{total}` 条")
    
    # 基础信息
    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        st.write("**基本信息**")
        st.code(f"""mode: {safe_str(row.get('mode'))}
target_person: {safe_str(row.get('target_person'))}
score: {safe_str(row.get('score'))}""")
    
    with info_col2:
        st.write("**AI预判**")
        if '自动原因分类' in row and safe_str(row.get('自动原因分类')):
            confidence = row.get('置信度', 0)
            color = "🟢" if confidence > 0.5 else "🟡" if confidence > 0.3 else "🔴"
            st.code(f"""{color} 原因: {safe_str(row.get('自动原因分类'))}
置信度: {confidence:.2f}
待复核: {row.get('待复核', False)}""")
        else:
            st.info("未进行自动标注")
    
    with info_col3:
        st.write("**人工标注**")
        current_reason = safe_str(row.get("人工原因分类")).strip()
        if current_reason:
            st.success(f"✅ 已标注：`{current_reason}`")
        else:
            st.warning("❌ 未标注")
    
    st.markdown("---")
    
    # 文本内容（如果是文本检索）
    if safe_str(row.get("mode")).strip().lower() == "text":
        with st.expander("📄 文本检索内容（query_text）"):
            st.code(safe_str(row.get("query_text")) or "(空)")
    
    # 图像展示
    left, right = st.columns(2)
    
    with left:
        st.markdown("**标注图（漏检图）**")
        image_path = safe_str(row.get("image_path"))
        if image_path and Path(image_path).exists():
            st.image(image_path, width=350, use_column_width=True)
        else:
            st.warning("❌ 图像路径不存在")
        st.caption(f"路径: {image_path[:60]}..." if len(image_path) > 60 else f"路径: {image_path}")
    
    with right:
        st.markdown("**Query 原图**")
        query_image_path = safe_str(row.get("query_image_path"))
        if query_image_path and Path(query_image_path).exists():
            st.image(query_image_path, width=350, use_container_width=True)
        else:
            st.info("ℹ️ 无Query原图（文本检索样本常见）")
        st.caption(f"路径: {query_image_path[:60]}..." if len(query_image_path) > 60 else f"路径: {query_image_path}")
    
    st.markdown("---")
    st.subheader("📝 标注表单")
    
    # 标注表单
    current_reason = safe_str(row.get("人工原因分类"))
    if current_reason not in REASON_OPTIONS:
        REASON_OPTIONS.append(current_reason)
    
    reason = st.selectbox(
        "人工原因分类",
        options=REASON_OPTIONS,
        index=REASON_OPTIONS.index(current_reason) if current_reason in REASON_OPTIONS else 0,
        key=f"reason_{idx}"
    )
    
    # 建议标注（基于AI预判）
    if '自动原因分类' in row and safe_str(row.get('自动原因分类')):
        st.info(f"💡 AI建议: `{safe_str(row.get('自动原因分类'))}`")
    
    current_issue = safe_str(row.get("是否标注问题"))
    issue_options = ["", "是", "否"]
    if current_issue not in issue_options:
        issue_options.append(current_issue)
    
    label_issue = st.radio(
        "是否标注问题",
        options=issue_options,
        horizontal=True,
        index=issue_options.index(current_issue) if current_issue in issue_options else 0,
        key=f"issue_{idx}"
    )
    
    note = st.text_area(
        "标注备注",
        value=safe_str(row.get("标注备注")),
        height=80,
        key=f"note_{idx}"
    )
    
    # ============ 快捷键和按钮 ============
    st.markdown("---")
    st.subheader("⌨️ 快捷操作")
    
    hk_col1, hk_col2 = st.columns([1, 2])
    
    with hk_col1:
        st.markdown("""**数字快速选择**
- `1` 遮挡
- `2` 目标尺寸过小
- `3` 光照/模糊问题
- `4` 背景干扰
- `5` 标注问题
- `6` 其他异常
- `0` 采用AI建议""")
    
    with hk_col2:
        st.caption("输入数字后回车")
        with st.form("hotkey_form", clear_on_submit=True):
            hotkey = st.text_input(
                "快捷键（输入0-6或直接回车）",
                value="",
                placeholder="例如: 1"
            )
            hotkey_submit = st.form_submit_button("▶️ 提交并下一条", use_container_width=True)
    
    # 处理快捷键
    if hotkey_submit:
        hotkey_norm = hotkey.strip()
        ai_reason = safe_str(row.get("自动原因分类")).strip()
        
        quick_reason = reason  # 默认使用当前选择
        
        if hotkey_norm == "0" and ai_reason:
            # 采用AI建议
            quick_reason = ai_reason
        elif hotkey_norm in {"1", "2", "3", "4", "5", "6"}:
            # 按数字选择
            quick_reason = REASON_OPTIONS[int(hotkey_norm)]
        elif hotkey_norm == "":
            # 空输入：采用AI建议，否则采用当前选择
            quick_reason = ai_reason if ai_reason else reason
        
        save_row(df, idx, csv_path, quick_reason, label_issue, note)
        st.session_state.row_idx = goto_next_index(df, idx, filter_mode)
        st.rerun()
    
    # ============ 导航按钮 ============
    b1, b2, b3, b4, b5 = st.columns(5)
    
    with b1:
        if st.button("⬅️ 上一条", use_container_width=True):
            st.session_state.row_idx = max(0, idx - 1)
            st.rerun()
    
    with b2:
        if st.button("💾 保存", use_container_width=True):
            save_row(df, idx, csv_path, reason, label_issue, note)
            st.success("✅ 已保存")
    
    with b3:
        if st.button("✅ 采用AI建议", use_container_width=True, type="secondary"):
            if '自动原因分类' in row and safe_str(row.get('自动原因分类')):
                ai_reason = safe_str(row.get('自动原因分类'))
                save_row(df, idx, csv_path, ai_reason, label_issue, note)
                st.session_state.row_idx = goto_next_index(df, idx, filter_mode)
                st.rerun()
    
    with b4:
        if st.button("➡️ 下一条", use_container_width=True):
            save_row(df, idx, csv_path, reason, label_issue, note)
            st.session_state.row_idx = goto_next_index(df, idx, filter_mode)
            st.rerun()
    
    with b5:
        if st.button("⏭️ 跳过", use_container_width=True, type="secondary"):
            st.session_state.row_idx = goto_next_index(df, idx, filter_mode)
            st.rerun()


if __name__ == "__main__":
    main()
