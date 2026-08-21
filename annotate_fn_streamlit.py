from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st


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
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 不存在: {csv_path}")
    return pd.read_csv(csv_path)


def safe_str(v) -> str:
    if pd.isna(v):
        return ""
    return str(v)


def save_row(df: pd.DataFrame, idx: int, csv_path: Path, reason: str, label_issue: str, note: str) -> None:
    df.at[idx, "人工原因分类"] = reason
    df.at[idx, "是否标注问题"] = label_issue
    df.at[idx, "标注备注"] = note
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")


def goto_next_index(df: pd.DataFrame, idx: int, only_unlabeled: bool) -> int:
    total = len(df)
    if not only_unlabeled:
        return min(total - 1, idx + 1)
    unlabeled_idx = df.index[df["人工原因分类"].isna() | (df["人工原因分类"].astype(str).str.strip() == "")]
    next_candidates = [x for x in unlabeled_idx if x > idx]
    return int(next_candidates[0]) if next_candidates else idx


def main() -> None:
    st.set_page_config(page_title="FN 标注工具", layout="wide")
    st.title("FN 人工标注工具（单窗口切图）")

    csv_input = st.text_input("CSV 路径", value=str(DEFAULT_CSV))
    csv_path = Path(csv_input)

    try:
        df = load_df(csv_path)
    except Exception as e:
        st.error(str(e))
        return

    if "row_idx" not in st.session_state:
        st.session_state.row_idx = 0

    total = len(df)
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        jump_row = st.number_input("跳转到数据行号(1开始)", min_value=1, max_value=max(1, total), value=st.session_state.row_idx + 1)
    with c2:
        only_unlabeled = st.checkbox("仅看未标注", value=False)
    with c3:
        st.write(f"总样本: {total}")

    if st.button("跳转"):
        st.session_state.row_idx = int(jump_row) - 1

    if only_unlabeled:
        unlabeled_idx = df.index[df["人工原因分类"].isna() | (df["人工原因分类"].astype(str).str.strip() == "")]
        if len(unlabeled_idx) == 0:
            st.success("全部已标注。")
            return
        # 把当前位置映射到未标注子集
        if st.session_state.row_idx not in unlabeled_idx:
            st.session_state.row_idx = int(unlabeled_idx[0])

    idx = max(0, min(st.session_state.row_idx, total - 1))
    row = df.iloc[idx]

    st.markdown(f"### 当前: 第 `{idx + 1}` / `{total}` 条")
    st.write(
        {
            "mode": safe_str(row.get("mode")),
            "target_person": safe_str(row.get("target_person")),
            "fn_file_path": safe_str(row.get("fn_file_path")),
            "score": safe_str(row.get("score")),
        }
    )
    current_human_reason = safe_str(row.get("人工原因分类")).strip()
    if current_human_reason:
        st.success(f"当前人工标注：`{current_human_reason}`")
    else:
        st.info("当前人工标注：`未标注`")

    st.info(f"AI 初判漏检原因（auto_reason）：`{safe_str(row.get('auto_reason')) or '未提供'}`")

    if safe_str(row.get("mode")).strip().lower() == "text":
        st.markdown("**文本检索内容（query_text）**")
        st.code(safe_str(row.get("query_text")) or "(空)")

    left, right = st.columns(2)
    with left:
        st.markdown("**标注图（漏检图）**")
        image_path = safe_str(row.get("image_path"))
        if image_path and Path(image_path).exists():
            st.image(image_path, width=320)
        else:
            st.warning("image_path 不存在")
        st.code(image_path or "(空)")

    with right:
        st.markdown("**Query 原图**")
        query_image_path = safe_str(row.get("query_image_path"))
        if query_image_path and Path(query_image_path).exists():
            st.image(query_image_path, width=320)
        else:
            st.info("query_image_path 为空或不存在（文本检索样本常见）")
        st.code(query_image_path or "(空)")

    st.markdown("---")
    st.subheader("在下方直接标注")

    current_reason = safe_str(row.get("人工原因分类"))
    if current_reason not in REASON_OPTIONS:
        REASON_OPTIONS.append(current_reason)
    reason = st.selectbox("人工原因分类", options=REASON_OPTIONS, index=REASON_OPTIONS.index(current_reason) if current_reason in REASON_OPTIONS else 0)

    current_issue = safe_str(row.get("是否标注问题"))
    issue_options = ["", "是", "否"]
    if current_issue not in issue_options:
        issue_options.append(current_issue)
    label_issue = st.radio(
        "是否标注问题",
        options=issue_options,
        horizontal=True,
        index=issue_options.index(current_issue) if current_issue in issue_options else 0,
    )

    note = st.text_area("标注备注", value=safe_str(row.get("标注备注")), height=100)

    st.markdown("#### 快捷键模式")
    hk_left, hk_right = st.columns([1, 2])
    with hk_left:
        st.markdown(
            "\n".join(
                [
                    "**数字映射**",
                    "- `1` 遮挡",
                    "- `2` 目标尺寸过小",
                    "- `3` 光照/模糊问题",
                    "- `4` 背景干扰",
                    "- `5` 标注问题",
                    "- `6` 其他异常",
                ]
            )
        )
    with hk_right:
        st.caption("输入 `1-6` 后直接回车：分类并自动保存到下一条；输入框留空直接回车：按当前选项保存到下一条。")
        with st.form("hotkey_form", clear_on_submit=True):
            hotkey = st.text_input("快捷键输入（直接回车提交）", value="", placeholder="例如：1")
            hotkey_submit = st.form_submit_button("提交")

    if hotkey_submit:
        hotkey_norm = hotkey.strip()
        ai_reason = safe_str(row.get("auto_reason")).strip()
        quick_reason = REASON_OPTIONS[0]
        if hotkey_norm in {"1", "2", "3", "4", "5", "6"}:
            quick_reason = REASON_OPTIONS[int(hotkey_norm)]
        elif hotkey_norm == "":
            # 直接回车：优先采用 AI 原因；若缺失则回退到当前手动选择
            quick_reason = ai_reason if ai_reason else reason
        else:
            quick_reason = reason
        save_row(df, idx, csv_path, quick_reason, label_issue, note)
        st.session_state.row_idx = goto_next_index(df, idx, only_unlabeled)
        st.rerun()

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("上一条"):
            st.session_state.row_idx = max(0, idx - 1)
            st.rerun()
    with b2:
        if st.button("保存"):
            save_row(df, idx, csv_path, reason, label_issue, note)
            st.success("已保存")
    with b3:
        if st.button("保存并下一条"):
            save_row(df, idx, csv_path, reason, label_issue, note)
            st.session_state.row_idx = goto_next_index(df, idx, only_unlabeled)
            st.rerun()
    with b4:
        if st.button("下一条(不保存)"):
            if only_unlabeled:
                unlabeled_idx = df.index[df["人工原因分类"].isna() | (df["人工原因分类"].astype(str).str.strip() == "")]
                next_candidates = [x for x in unlabeled_idx if x > idx]
                st.session_state.row_idx = int(next_candidates[0]) if next_candidates else idx
            else:
                st.session_state.row_idx = min(total - 1, idx + 1)
            st.rerun()


if __name__ == "__main__":
    main()

