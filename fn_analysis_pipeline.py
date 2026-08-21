import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
IMG_FN_CSV = ROOT / "FN_Analysis_Image_FrameLevel" / "FN_Analysis_Image_FrameLevel" / "fn_scores.csv"
TXT_FN_CSV = ROOT / "FN_Analysis_Text_FrameLevel" / "FN_Analysis_Text_FrameLevel" / "fn_scores_text.csv"
LABEL_JSON = ROOT / "generated_beiyou_labeled.json"
OUT_DIR = ROOT / "outputs" / "fn_analysis"
IMG_FN_ROOT = ROOT / "FN_Analysis_Image_FrameLevel" / "FN_Analysis_Image_FrameLevel"
TXT_FN_ROOT = ROOT / "FN_Analysis_Text_FrameLevel" / "FN_Analysis_Text_FrameLevel"


REASON_CATEGORIES = [
    "遮挡",
    "目标尺寸过小",
    "光照/模糊问题",
    "背景干扰",
    "标注问题",
    "其他异常",
]

REASON_EN_MAP = {
    "遮挡": "occlusion",
    "目标尺寸过小": "small_target",
    "光照/模糊问题": "lighting_or_blur",
    "背景干扰": "background_clutter",
    "标注问题": "annotation_issue",
    "其他异常": "other",
}


def parse_file_path(file_path: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """Parse names like 1_326_6_0.jpg into numeric parts."""
    stem = Path(str(file_path)).stem
    parts = stem.split("_")
    if len(parts) < 4:
        return None, None, None, None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    except ValueError:
        return None, None, None, None


def load_caption_map(label_json: Path) -> Dict[str, str]:
    if not label_json.exists():
        return {}
    with label_json.open("r", encoding="utf-8") as f:
        items = json.load(f)

    caption_map: Dict[str, str] = {}
    for item in items:
        file_path = item.get("file_path")
        captions = item.get("captions", [])
        if not file_path:
            continue
        if isinstance(captions, list) and captions:
            caption_map[file_path] = " ".join([str(x) for x in captions if x])
    return caption_map


def build_file_index(base_dirs: List[Path], pattern: str) -> Dict[str, List[str]]:
    """
    Build index by basename. Key: file name, Value: absolute paths.
    """
    idx: Dict[str, List[str]] = {}
    for base in base_dirs:
        if not base.exists():
            continue
        for p in base.rglob(pattern):
            idx.setdefault(p.name, []).append(str(p.resolve()))
    return idx


def pick_best_path(candidates: List[str], preferred_keyword: Optional[str] = None) -> str:
    if not candidates:
        return ""
    if preferred_keyword:
        for c in candidates:
            if preferred_keyword.lower() in c.lower():
                return c
    return candidates[0]


def infer_reason_by_text(caption: str) -> str:
    # Kept for compatibility; real classification now uses make_auto_reason().
    if not caption:
        return "其他异常"
    s = caption.lower()
    if any(k in s for k in ["occlud", "partially occluded", "blocked"]):
        return "遮挡"
    if any(k in s for k in ["blur", "blurry", "out of focus", "dark", "low light", "shadow"]):
        return "光照/模糊问题"
    if any(k in s for k in ["crowd", "clutter", "busy background", "complex background"]):
        return "背景干扰"
    if any(k in s for k in ["small", "tiny", "distant", "far away", "long shot"]):
        return "目标尺寸过小"
    return "其他异常"


def _keyword_score(s: str, keywords: List[str]) -> int:
    return sum(1 for k in keywords if k in s)


def _tokenize_alpha(s: str) -> List[str]:
    out: List[str] = []
    for t in s.lower().replace(",", " ").replace(".", " ").replace("/", " ").split():
        t = t.strip()
        if len(t) < 3:
            continue
        if t in {"the", "and", "with", "from", "while", "wearing", "person", "individual"}:
            continue
        out.append(t)
    return out


def make_auto_reason(mode: str, score: float, threshold: float, caption: str, query_text: str) -> str:
    s = (caption or "").lower()
    margin = float(threshold) - float(score) if pd.notna(score) else 0.0

    # Category keyword sets.
    occ_kw = [
        "behind", "rear", "back view", "viewed from behind", "from the rear", "occlud", "partially",
        "silhouette", "side-rear", "seen from the back",
    ]
    small_kw = ["small", "tiny", "distant", "far away", "long shot", "low resolution", "hard to see details"]
    light_kw = ["blur", "blurry", "out of focus", "dark", "dim", "low light", "shadow", "overexposed", "underexposed"]
    bg_kw = ["crowd", "clutter", "busy background", "complex background", "multiple people", "railings", "metal structure"]

    scores = {
        "遮挡": _keyword_score(s, occ_kw),
        "目标尺寸过小": _keyword_score(s, small_kw),
        "光照/模糊问题": _keyword_score(s, light_kw),
        "背景干扰": _keyword_score(s, bg_kw),
        "标注问题": 0,
        "其他异常": 0,
    }

    # Strong decision-boundary + high semantic overlap -> probable annotation issue in text retrieval.
    if str(mode) == "text" and query_text:
        q_toks = set(_tokenize_alpha(query_text))
        c_toks = set(_tokenize_alpha(caption))
        overlap = len(q_toks.intersection(c_toks))
        if margin <= 0.02 and overlap >= 3:
            scores["标注问题"] += 3

    # Very close to threshold in image retrieval is often noisy boundary.
    if str(mode) == "image" and margin <= 0.006:
        scores["标注问题"] += 2

    # If margin is very large and there is no explicit clue, prefer "其他异常".
    if ((str(mode) == "text" and margin >= 0.12) or (str(mode) == "image" and margin >= 0.08)):
        scores["其他异常"] += 1

    best_reason = max(scores.items(), key=lambda x: x[1])[0]
    if scores[best_reason] <= 0:
        # Backoff: no strong evidence.
        return "其他异常"
    return best_reason


def prepare_image_fn(caption_map: Dict[str, str]) -> pd.DataFrame:
    df = pd.read_csv(IMG_FN_CSV)
    df = df.rename(
        columns={
            "目标人物": "target_person",
            "Query原图": "query_source",
            "漏检图(file_path)": "fn_file_path",
            "实际相似度得分(阈值0.71)": "score",
        }
    )
    df["mode"] = "image"
    df["threshold"] = 0.71
    df["query_text"] = pd.NA
    df["caption"] = df["fn_file_path"].map(caption_map).fillna("")
    return df


def prepare_text_fn(caption_map: Dict[str, str]) -> pd.DataFrame:
    df = pd.read_csv(TXT_FN_CSV)
    df = df.rename(
        columns={
            "目标人物": "target_person",
            "测试文本(Query)": "query_text",
            "漏检图(file_path)": "fn_file_path",
            "实际相似度得分(阈值0.30)": "score",
        }
    )
    df["mode"] = "text"
    df["threshold"] = 0.30
    df["query_source"] = pd.NA
    df["caption"] = df["fn_file_path"].map(caption_map).fillna("")
    return df


def build_text_query_map(txt_root: Path) -> Dict[str, str]:
    """
    Map query text content -> query_text.txt absolute path.
    """
    out: Dict[str, str] = {}
    if not txt_root.exists():
        return out
    for p in txt_root.rglob("query_text.txt"):
        try:
            content = p.read_text(encoding="utf-8").strip()
            if content and content not in out:
                out[content] = str(p.resolve())
        except Exception:
            continue
    return out


def build_outputs(
    df: pd.DataFrame,
    jpg_index: Dict[str, List[str]],
    query_image_index: Dict[str, List[str]],
    text_query_map: Dict[str, str],
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    parsed = df["fn_file_path"].apply(parse_file_path)
    df["camera_id"] = parsed.apply(lambda x: x[0])
    df["frame_id"] = parsed.apply(lambda x: x[1])
    df["track_id"] = parsed.apply(lambda x: x[2])
    df["instance_id"] = parsed.apply(lambda x: x[3])

    df["score_margin_to_threshold"] = df["threshold"] - df["score"]
    df["auto_reason"] = [
        make_auto_reason(md, sc, th, cap, qt)
        for md, sc, th, cap, qt in zip(df["mode"], df["score"], df["threshold"], df["caption"], df["query_text"])
    ]

    merged_cols = [
        "mode",
        "target_person",
        "query_source",
        "query_text",
        "fn_file_path",
        "score",
        "threshold",
        "score_margin_to_threshold",
        "camera_id",
        "frame_id",
        "track_id",
        "instance_id",
        "caption",
        "auto_reason",
    ]
    merged = df[merged_cols].copy()

    # Add direct-open paths to speed up manual annotation.
    merged["image_path"] = merged.apply(
        lambda r: pick_best_path(
            jpg_index.get(str(r["fn_file_path"]), []),
            preferred_keyword=("Image_FrameLevel" if r["mode"] == "image" else "Text_FrameLevel"),
        ),
        axis=1,
    )
    merged["query_image_path"] = merged.apply(
        lambda r: (
            pick_best_path(query_image_index.get(str(r["query_source"]), []), preferred_keyword="Image_FrameLevel")
            if r["mode"] == "image" and pd.notna(r["query_source"])
            else ""
        ),
        axis=1,
    )
    merged["query_text_path"] = merged.apply(
        lambda r: (
            text_query_map.get(str(r["query_text"]), "")
            if r["mode"] == "text"
            else ""
        ),
        axis=1,
    )

    merged.to_csv(OUT_DIR / "merged_fn_samples.csv", index=False, encoding="utf-8-sig")

    # Manual annotation template (preserve existing manual labels when regenerating).
    manual = merged.copy()
    manual["人工原因分类"] = ""
    manual["是否标注问题"] = ""
    manual["标注备注"] = ""
    manual["最终结论"] = ""

    existing_path = OUT_DIR / "manual_annotation_template_with_paths.csv"
    if existing_path.exists():
        old = pd.read_csv(existing_path)
        key_cols = ["mode", "target_person", "query_source", "query_text", "fn_file_path"]
        keep_cols = ["人工原因分类", "是否标注问题", "标注备注", "最终结论"]
        old_sub = old[key_cols + keep_cols].drop_duplicates(subset=key_cols, keep="last")
        manual = manual.merge(old_sub, on=key_cols, how="left", suffixes=("", "_old"))
        for c in keep_cols:
            manual[c] = manual[f"{c}_old"].combine_first(manual[c])
            manual = manual.drop(columns=[f"{c}_old"])
    manual.to_csv(OUT_DIR / "manual_annotation_template.csv", index=False, encoding="utf-8-sig")
    manual.to_csv(OUT_DIR / "manual_annotation_template_with_paths.csv", index=False, encoding="utf-8-sig")

    reason_stats = (
        merged.groupby(["mode", "auto_reason"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["mode", "count"], ascending=[True, False])
    )
    reason_stats["ratio"] = reason_stats.groupby("mode")["count"].transform(lambda x: x / x.sum())
    reason_stats.to_csv(OUT_DIR / "reason_distribution_auto.csv", index=False, encoding="utf-8-sig")

    person_stats = (
        merged.groupby(["mode", "target_person"], dropna=False)
        .agg(
            fn_count=("fn_file_path", "count"),
            avg_score=("score", "mean"),
            min_score=("score", "min"),
            max_score=("score", "max"),
        )
        .reset_index()
        .sort_values(["mode", "fn_count"], ascending=[True, False])
    )
    person_stats.to_csv(OUT_DIR / "person_stats.csv", index=False, encoding="utf-8-sig")

    camera_stats = (
        merged.groupby(["mode", "camera_id"], dropna=False)
        .agg(fn_count=("fn_file_path", "count"), avg_score=("score", "mean"))
        .reset_index()
        .sort_values(["mode", "fn_count"], ascending=[True, False])
    )
    camera_stats.to_csv(OUT_DIR / "camera_stats.csv", index=False, encoding="utf-8-sig")

    # Charts
    for mode in ["image", "text"]:
        sub = reason_stats[reason_stats["mode"] == mode]
        if sub.empty:
            continue
        sub_plot = sub.copy()
        sub_plot["reason_plot"] = sub_plot["auto_reason"].map(REASON_EN_MAP).fillna(sub_plot["auto_reason"])
        plt.figure(figsize=(8, 4))
        plt.bar(sub_plot["reason_plot"], sub_plot["count"])
        plt.title(f"FN Auto Reason Distribution ({mode})")
        plt.xticks(rotation=20)
        plt.tight_layout()
        plt.savefig(OUT_DIR / f"reason_distribution_{mode}.png", dpi=160)
        plt.close()

        cam_sub = camera_stats[camera_stats["mode"] == mode]
        if not cam_sub.empty:
            plt.figure(figsize=(8, 4))
            plt.bar(cam_sub["camera_id"].astype(str), cam_sub["fn_count"])
            plt.title(f"FN by Camera ({mode})")
            plt.xlabel("camera_id")
            plt.ylabel("fn_count")
            plt.tight_layout()
            plt.savefig(OUT_DIR / f"camera_distribution_{mode}.png", dpi=160)
            plt.close()

    # Report
    total = len(merged)
    image_n = int((merged["mode"] == "image").sum())
    text_n = int((merged["mode"] == "text").sum())
    top_person = person_stats.groupby("mode").head(1)

    lines: List[str] = []
    lines.append("# 漏检样本分析报告（自动生成）")
    lines.append("")
    lines.append("## 1. 数据概览")
    lines.append(f"- 总 FN 样本数: {total}")
    lines.append(f"- 图像检索 FN: {image_n}")
    lines.append(f"- 文本检索 FN: {text_n}")
    lines.append("")
    lines.append("## 2. 初步发现")
    for _, row in top_person.iterrows():
        lines.append(
            f"- `{row['mode']}` 模式下，FN 最多的目标是 `{row['target_person']}`，数量 `{int(row['fn_count'])}`。"
        )
    lines.append("- 已输出自动原因分布，但这只是弱规则初判，最终需人工复核。")
    lines.append("")
    lines.append("## 3. 建议的人工复核流程")
    lines.append("- 使用 `manual_annotation_template.csv` 逐条补充 `人工原因分类`。")
    lines.append("- 原因分类建议使用: " + "、".join(REASON_CATEGORIES) + "。")
    lines.append("- 复核完成后可按 `人工原因分类` 再生成正式占比图和典型 case。")
    lines.append("")
    lines.append("## 4. 输出文件")
    lines.append("- `merged_fn_samples.csv`：合并后的 FN 基表")
    lines.append("- `manual_annotation_template.csv`：人工标注模板")
    lines.append("- `reason_distribution_auto.csv`：自动原因统计")
    lines.append("- `person_stats.csv`：按目标统计")
    lines.append("- `camera_stats.csv`：按摄像头统计")
    lines.append("- `*.png`：自动统计图")
    lines.append("")
    (OUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    caption_map = load_caption_map(LABEL_JSON)
    jpg_index = build_file_index([IMG_FN_ROOT, TXT_FN_ROOT], "*.jpg")
    query_image_index = build_file_index([IMG_FN_ROOT], "*.jpg")
    text_query_map = build_text_query_map(TXT_FN_ROOT)
    img = prepare_image_fn(caption_map)
    txt = prepare_text_fn(caption_map)
    merged = pd.concat([img, txt], ignore_index=True)
    build_outputs(merged, jpg_index, query_image_index, text_query_map)
    print(f"Done. Outputs saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()

