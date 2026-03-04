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
<!doctype html>

<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>rbui log analysis report</title>
  <meta name="description" content="rbui log analysis report">
  <style type="text/css">
    html, body {
      background-color: black;
      margin: 0;
      padding: 0;
    }
    th {
      text-align: center;
      color: silver;
      font-style: bold;
      padding: 5px;
      cursor: pointer;
    }
    table {
      width: 98%;
      border-collapse: collapse;
      margin: 1%;
      color: silver;
    }
    td {
      text-align: right;
      font-size: 1.1em;
      padding: 5px;
      white-space: nowrap;
    }
    .report-table-body-cell-url {
      text-align: left;
      max-width: 600px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .clipped {
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden !important;
      max-width: 100%;
      word-wrap: break-word;
      display: inline-block;
    }
    .url {
      cursor: pointer;
      color: #729FCF;
    }
    .alert {
      color: red;
    }
  </style>
</head>

<body>
  <table border="1" class="report-table">
  <thead>
    <tr class="report-table-header-row">
    </tr>
  </thead>
  <tbody class="report-table-body">
  </tbody>

  <script>
  /* jQuery — inlined for offline use */
  $jquery_js
  </script>
  <script>
  /* jQuery Tablesorter — inlined for offline use */
  $tablesorter_js
  </script>
  <script type="text/javascript">
  !function($$$$) {
    var table = $table_json;
    var reportDates;
    var columns = [
        {title: "URL", data_key: "url"},
        {title: "count", data_key: "count"},
        {title: "count_perc", data_key: "count_perc"},
        {title: "time_avg", data_key: "time_avg"},
        {title: "time_max", data_key: "time_max"},
        {title: "time_med", data_key: "time_med"},
        {title: "time_perc", data_key: "time_perc"},
        {title: "time_sum", data_key: "time_sum"}
    ];
    var $$$$table = $$$$('.report-table');
    var $$$$header = $$$$table.find('.report-table-header-row');
    var $$$$body = $$$$table.find('.report-table-body');
    $$$$.each(columns, function(i, col) {
        $$$$header.append($$$$('<th>').text(col.title));
    });
    $$$$.each(table, function(i, row) {
        var $$$$row = $$$$('<tr>').addClass('report-table-body-row');
        $$$$.each(columns, function(j, col) {
            var $$$$cell = $$$$('<td>').addClass('report-table-body-cell-' + col.data_key);
            var value = row[col.data_key];
            if (col.data_key === 'url') {
                $$$$cell.html('<span class="url clipped">' + value + '</span>');
            } else {
                $$$$cell.text(value);
            }
            if (col.data_key === 'time_avg' && value > 1) {
                $$$$cell.addClass('alert');
            }
            $$$$row.append($$$$cell);
        });
        $$$$body.append($$$$row);
    });
    $$$$table.tablesorter();
  }(jQuery);
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
        table_json=table_json,
        jquery_js=_JQUERY_JS,
        tablesorter_js=_TABLESORTER_JS,
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path
