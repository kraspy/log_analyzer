"""Render a per-URL statistics HTML report using ``string.Template``.

The template substitutes ``$table_json`` with a JSON array of
per-URL stat objects (as required by the HW specification).

The rendered page uses embedded JavaScript to dynamically build
an HTML table from the JSON data and provides client-side
column sorting via ``jquery.tablesorter`` (bundled inline for
offline use — no CDN dependency).
"""

from pathlib import Path
from string import Template

# ---------------------------------------------------------------------------
# Load vendor JS once at import time (jquery + tablesorter).
# These are bundled in cli/vendor/ so reports work fully offline.
# ---------------------------------------------------------------------------
_VENDOR_DIR = Path(__file__).parent / "vendor"


def _load_vendor(filename: str) -> str:
    """Load a vendored JavaScript file as a string.

    Args:
        filename: Name of the JS file in the vendor directory.

    Returns:
        The file contents as a string.
    """
    return (_VENDOR_DIR / filename).read_text(encoding="utf-8")


_JQUERY_JS = _load_vendor("jquery.min.js")
_TABLESORTER_JS = _load_vendor("tablesorter.min.js")

# ---------------------------------------------------------------------------
# HTML template — jQuery + tablesorter inlined for offline use.
# $table_json is substituted with a JSON array of per-URL rows.
# ---------------------------------------------------------------------------
_REPORT_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nginx Log Report — $report_date</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
         "Helvetica Neue", Arial, sans-serif; margin: 2rem; background: #f5f5f5; }
  h1   { color: #333; }
  table { width: 100%; border-collapse: collapse; background: #fff;
          box-shadow: 0 1px 3px rgba(0,0,0,.12); }
  th, td { padding: 8px 12px; text-align: right; border-bottom: 1px solid #eee; }
  th { background: #4a90d9; color: #fff; cursor: pointer; user-select: none; }
  td:first-child, th:first-child { text-align: left; }
  tr:hover { background: #f0f7ff; }
  .meta { color: #666; margin-bottom: 1.5rem; }
  /* tablesorter header indicators */
  th.headerSortUp::after   { content: " ▲"; }
  th.headerSortDown::after { content: " ▼"; }
</style>
</head>
<body>
<h1>Nginx Log Report</h1>
<p class="meta">Date: <strong>$report_date</strong></p>
<table id="report" class="tablesorter">
<thead>
<tr>
  <th>URL</th>
  <th>Count</th>
  <th>Count %</th>
  <th>Time Sum</th>
  <th>Time %</th>
  <th>Time Avg</th>
  <th>Time Max</th>
  <th>Time Med</th>
</tr>
</thead>
<tbody></tbody>
</table>
<script>
/* jQuery — inlined for offline use */
$jquery_js
</script>
<script>
/* jQuery Tablesorter — inlined for offline use */
$tablesorter_js
</script>
<script>
/* Data injected from Python via string.Template */
var table_json = $table_json;

/* Build table rows from JSON */
var tbody = document.querySelector('#report tbody');
table_json.forEach(function(row) {
  var tr = document.createElement('tr');
  tr.innerHTML =
    '<td>' + row.url + '</td>' +
    '<td>' + row.count + '</td>' +
    '<td>' + row.count_perc.toFixed(2) + '%</td>' +
    '<td>' + row.time_sum.toFixed(3) + '</td>' +
    '<td>' + row.time_perc.toFixed(2) + '%</td>' +
    '<td>' + row.time_avg.toFixed(3) + '</td>' +
    '<td>' + row.time_max.toFixed(3) + '</td>' +
    '<td>' + row.time_med.toFixed(3) + '</td>';
  tbody.appendChild(tr);
});

/* Activate tablesorter */
$$$$(function(){ $$$$('#report').tablesorter(); });
</script>
</body>
</html>
""")


def render_report(
    table_json: str,
    report_date: str,
    output_path: Path,
) -> Path:
    """Render per-URL statistics to a self-contained HTML file.

    Uses ``string.Template`` with ``$table_json`` substitution,
    as specified in the HW requirements. jQuery and tablesorter
    are embedded inline — the report works fully offline.

    Args:
        table_json: JSON-serialized array of per-URL stat objects.
        report_date: Human-readable date string for the report title.
        output_path: Where to write the HTML file.

    Returns:
        The path the report was written to.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html = _REPORT_TEMPLATE.substitute(
        report_date=report_date,
        table_json=table_json,
        jquery_js=_JQUERY_JS,
        tablesorter_js=_TABLESORTER_JS,
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path
