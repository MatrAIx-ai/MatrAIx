# Nemotron Domain Selection Plots

This directory contains the PR90 Nemotron domain-selection summaries and plot
artifacts.

Regenerate the standard-library SVG plots and metrics:

```bash
python3 personas/existing_data_curation/scripts/render_nemotron_domain_selection_plots.py
```

Regenerate the Matplotlib PNG/PDF/SVG cluster figure as well:

```bash
python3 personas/existing_data_curation/scripts/render_nemotron_domain_selection_plots.py --matplotlib
```

`--matplotlib` requires `matplotlib`; the default command only uses the Python
standard library and rewrites the SVG/CSV artifacts from the committed metrics
and cluster CSVs. If `nemotron_test_users_50_per_domain.json` is present, the
script will use it to regenerate the metrics CSVs before rendering; otherwise it
uses the existing committed CSV summaries.
