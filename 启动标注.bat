@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo ════════════════════════════════════════════════════════════════
echo   🎯 FN标注Web界面 - 一键启动
echo ════════════════════════════════════════════════════════════════
echo.

echo 📊 项目信息：
echo   - 样本总数：4,289 条
echo   - 待标注：4,186 条
echo   - CSV路径：outputs/fn_analysis/manual_annotation_template_with_paths.csv
echo.

echo 🚀 启动Web服务...
echo.

python -m streamlit run annotate_fn_enhanced.py

echo.
echo ════════════════════════════════════════════════════════════════
echo 📌 提示：Web界面已关闭，标注数据已保存到CSV
echo ════════════════════════════════════════════════════════════════
echo.

pause
