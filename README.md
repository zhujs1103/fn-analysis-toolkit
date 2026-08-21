# False-Negative Analysis Toolkit

A small Pandas + Streamlit toolkit for reviewing false-negative image/text samples, assigning root-cause labels and generating progress/statistics reports.

## Features

- Six configurable reason categories with fast numeric input.
- Image/query comparison, filtering, row navigation and immediate save.
- Rule-based automatic pre-labeling with confidence fields.
- Progress summaries and reusable analysis/report pipeline.
- Designed around a 4,289-sample internal workflow; the public repository contains code and documentation only.

## Quick start

```bash
python -m pip install -r requirements.txt
streamlit run annotate_fn_enhanced.py
```

Pass your own CSV path according to the script help or adapt the documented column names. Do not commit private datasets or generated annotation workbooks.

## Verification status

All included Python files pass syntax parsing. The curated public copy does not include the original CSV/XLSX data, images or completed team annotations, so an end-to-end run requires a user-provided dataset.

The older Chinese guides are retained for workflow context; paths referring to `outputs/fn_analysis` are examples from the original project layout.

## License

The original code in this curated repository is released under the MIT License.
Private datasets, annotations and generated reports are not included.
