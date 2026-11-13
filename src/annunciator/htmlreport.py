"""HTML report of a run.

The function :func:`write_html_report` writes one HTML file that
contains the events of a run. The file has no external parts. You can
open it in a browser without a network connection and send it to other
persons.

The page has the style of a printed industrial report: a title block,
numbered sections and ruled tables in a fixed-width font, without
colour. It shows the number of events for each severity and for each
message code, the distinct failures and a table of the events. The reader can select events by
severity, by message code and by text. A click on an event shows its
fields, cause, remedy and traceback.

Examples
--------
>>> import os, tempfile
>>> from annunciator import Event, Severity
>>> from annunciator.htmlreport import write_html_report
>>> events = [Event(severity=Severity.ERROR, message="No beam", code="APP-E-0001")]
>>> path = write_html_report(events, os.path.join(tempfile.mkdtemp(), "run.html"))
>>> path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
True
"""

from __future__ import annotations

import datetime as _dt
import html
import json
from pathlib import Path
from typing import Iterable, List, Union

from ._version import __version__
from .events import Event, json_default
from .report import EventReport

__all__ = ["write_html_report"]

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
html { background: #d8d8d4; }
body { margin: 0; color: #000;
       font: 13px/1.35 "Courier New", Courier, "Liberation Mono", monospace; }
#sheet { max-width: 1120px; margin: 18px auto; padding: 28px 34px 34px;
         background: #fdfdf8; border: 1px solid #000; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #000; padding: 3px 7px; text-align: left;
         vertical-align: top; }
th { font-weight: bold; text-transform: uppercase; background: #e9e9e2; }
td.num, th.num { text-align: right; white-space: nowrap; }
td.nowrap { white-space: nowrap; }
#titleblock { border: 2px solid #000; margin-bottom: 6px; }
#titleblock td { border: 1px solid #000; padding: 4px 8px; }
#titleblock .label { display: block; font-size: 10px; text-transform: uppercase;
                     letter-spacing: .08em; }
#titleblock .value { font-weight: bold; }
#titleblock .title { font-size: 20px; font-weight: bold; text-transform: uppercase;
                     letter-spacing: .04em; }
h2 { font: inherit; font-weight: bold; text-transform: uppercase;
     margin: 26px 0 8px; padding-bottom: 2px; border-bottom: 2px solid #000; }
.half { width: auto; min-width: 46%; }
.cols { display: flex; flex-wrap: wrap; gap: 0 40px; align-items: flex-start; }
.note { margin: 6px 0; }
.sev-W, .sev-E, .sev-C { font-weight: bold; }
.sev-E::before, .sev-C::before { content: "* "; }
tr.event, tr.pick { cursor: pointer; }
tr.event:hover td, tr.pick:hover td { background: #efefe6; }
tr.detail > td { background: #f4f4ec; padding: 6px 10px 8px 34px; }
tr.detail table { width: auto; margin: 2px 0; }
tr.detail th { width: 150px; }
pre { margin: 0; font: inherit; white-space: pre-wrap; overflow-wrap: anywhere; }
td.msg { overflow-wrap: anywhere; }
#tools { border: 1px solid #000; padding: 6px 8px; margin: 0 0 8px;
         display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; }
#tools label { text-transform: uppercase; }
input, select, button { font: inherit; color: #000; background: #fff;
       border: 1px solid #000; border-radius: 0; padding: 2px 6px; }
input[type=search] { flex: 1 1 240px; }
input[type=checkbox] { margin: 0; vertical-align: middle; }
button { background: #e9e9e2; cursor: pointer; text-transform: uppercase; }
button:active { background: #cfcfc6; }
#end { text-align: center; margin-top: 30px; letter-spacing: .3em; }
#foot { display: flex; justify-content: space-between; margin-top: 10px;
        border-top: 1px solid #000; padding-top: 4px; font-size: 11px; }
@media print {
  html { background: #fff; }
  #sheet { border: 0; margin: 0; padding: 0; max-width: none; background: #fff; }
  #tools, .screen { display: none; }
  tr { page-break-inside: avoid; }
  thead { display: table-header-group; }
  th { background: #fff; }
}
</style>
</head>
<body>
<div id="sheet">
<table id="titleblock">
  <tr>
    <td rowspan="2" style="width:46%"><span class="label">Report title</span>
        <span class="title">__TITLE__</span></td>
    <td><span class="label">Report type</span><span class="value">EVENT LOG REPORT</span></td>
    <td><span class="label">Date of issue (UTC)</span><span class="value">__GENERATED__</span></td>
  </tr>
  <tr>
    <td><span class="label">Events recorded</span><span class="value">__TOTAL__</span></td>
    <td><span class="label">Worst severity</span><span class="value">__WORST__</span></td>
  </tr>
  <tr>
    <td colspan="3"><span class="label">Period of the record (UTC)</span>
        <span class="value">__PERIOD__</span></td>
  </tr>
</table>
<div class="note">__NOTE__</div>

<div class="cols">
<div>
<h2>1. Summary by severity</h2>
<table class="half" id="severities">
  <thead><tr><th>Severity</th><th class="num">Events</th><th class="screen">Show</th></tr></thead>
  <tbody></tbody>
</table>
</div>
<div>
<h2>2. Summary by message code</h2>
<table class="half" id="codes">
  <thead><tr><th>Message code</th><th class="num">Events</th></tr></thead>
  <tbody></tbody>
</table>
</div>
</div>

<h2>3. Distinct failures</h2>
<div id="failures"></div>

<h2>4. Event log</h2>
<div id="tools">
  <label for="search">Find:</label>
  <input type="search" id="search" placeholder="text in message, logger or fields">
  <label for="code">Code:</label>
  <select id="code"><option value="">ALL</option></select>
  <button id="problems" type="button">Warnings and errors only</button>
  <button id="reset" type="button">Show all</button>
  <button id="expand" type="button">Expand all</button>
  <button id="print" type="button">Print</button>
</div>
<div class="note" id="count"></div>
<table id="log">
  <thead><tr><th class="num">No.</th><th>Time (UTC)</th><th>Severity</th><th>Code</th>
  <th>Logger</th><th>Message</th></tr></thead>
  <tbody id="rows"></tbody>
</table>
<p class="screen"><button id="more" type="button" hidden>Show more events</button></p>

<div id="end">*** END OF REPORT ***</div>
<div id="foot"><span>__FOOTER__</span><span>__TITLE__</span></div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  "use strict";
  var data = JSON.parse(document.getElementById("data").textContent);
  var events = data.events, order = data.severities;
  var active = {}, boxes = {}, limit = 500, query = "", codeFilter = "", expandAll = false;
  order.forEach(function (name) { active[name] = true; });
  function el(tag, text, cls) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) { node.textContent = text; }
    if (cls) { node.className = cls; }
    return node;
  }
  function cls(name) { return "sev-" + name.charAt(0); }
  var sevBody = document.querySelector("#severities tbody");
  order.slice().reverse().forEach(function (name) {
    var row = el("tr", null, "pick");
    row.appendChild(el("td", name, cls(name)));
    row.appendChild(el("td", String(data.counts[name] || 0), "num"));
    var cell = el("td", null, "screen"), box = el("input");
    box.type = "checkbox"; box.checked = true;
    cell.appendChild(box); row.appendChild(cell);
    boxes[name] = box;
    row.title = "Show or hide " + name;
    row.addEventListener("click", function (ev) {
      if (ev.target !== box) { box.checked = !box.checked; }
      active[name] = box.checked;
      render();
    });
    sevBody.appendChild(row);
  });
  var total = el("tr");
  total.appendChild(el("th", "Total"));
  total.appendChild(el("th", String(data.total), "num"));
  total.appendChild(el("th", "", "screen"));
  sevBody.appendChild(total);
  var select = document.getElementById("code");
  var codeBody = document.querySelector("#codes tbody");
  data.codes.forEach(function (item) {
    var option = el("option", item[0] + " (" + item[1] + ")");
    option.value = item[0];
    select.appendChild(option);
    var row = el("tr", null, "pick");
    row.appendChild(el("td", item[0]));
    row.appendChild(el("td", String(item[1]), "num"));
    row.title = "Show the events with this code";
    row.addEventListener("click", function () {
      select.value = item[0]; codeFilter = item[0]; limit = 500; render();
    });
    codeBody.appendChild(row);
  });
  if (!data.codes.length) {
    var none = el("tr"), cell0 = el("td", "No events with a message code.");
    cell0.colSpan = 2; none.appendChild(cell0); codeBody.appendChild(none);
  }
  var box3 = document.getElementById("failures");
  if (data.failures.length) {
    var table = el("table"), thead = el("thead"), head = el("tr"), body = el("tbody");
    [["No.", "num"], ["Fingerprint", ""], ["Events", "num"], ["Exception", ""],
     ["First message", ""]].forEach(function (t) { head.appendChild(el("th", t[0], t[1])); });
    thead.appendChild(head); table.appendChild(thead);
    data.failures.forEach(function (f, index) {
      var row = el("tr", null, "pick");
      row.appendChild(el("td", String(index + 1), "num"));
      row.appendChild(el("td", f.fingerprint, "nowrap"));
      row.appendChild(el("td", String(f.count), "num"));
      row.appendChild(el("td", f.type));
      row.appendChild(el("td", f.message, "msg"));
      row.title = "Show the events of this failure";
      row.addEventListener("click", function () {
        document.getElementById("search").value = f.fingerprint;
        query = f.fingerprint.toLowerCase(); limit = 500;
        render();
      });
      body.appendChild(row);
    });
    table.appendChild(body); box3.appendChild(table);
  } else {
    box3.appendChild(el("div", "NIL. No exceptions were recorded.", "note"));
  }
  events.forEach(function (e, index) {
    e._no = data.first_number + index;
    e._text = [e.message, e.logger, e.code, JSON.stringify(e.fields || {}),
               e.exception ? e.exception.fingerprint + " " + e.exception.type : ""]
              .join(" ").toLowerCase();
  });
  function detail(e) {
    var table = el("table");
    function add(name, value, pre) {
      if (value === undefined || value === null || value === "") { return; }
      var row = el("tr");
      row.appendChild(el("th", name));
      var cell = el("td");
      cell.appendChild(pre ? el("pre", value) : document.createTextNode(value));
      row.appendChild(cell);
      table.appendChild(row);
    }
    add("Cause", e.cause);
    add("Remedy", e.remedy);
    if (e.fields && Object.keys(e.fields).length) {
      add("Fields", Object.keys(e.fields).map(function (k) {
        var v = e.fields[k];
        return k + " = " + (typeof v === "object" ? JSON.stringify(v) : v);
      }).join("\\n"), true);
    }
    if (e.source) { add("Source", e.source.file + ":" + e.source.line + " in " + e.source.function); }
    if (e.exception) {
      add("Exception", e.exception.type + ": " + e.exception.message);
      add("Fingerprint", e.exception.fingerprint);
      add("Traceback", e.exception.traceback, true);
      if (e.exception.locals) { add("Local variables", JSON.stringify(e.exception.locals, null, 2), true); }
    }
    add("Process / thread", (e.process || "") + " / " + (e.thread || ""));
    add("Event identifier", e.event_id);
    return table;
  }
  function detailRow(e) {
    var extra = el("tr", null, "detail"), cell = el("td");
    cell.colSpan = 6;
    cell.appendChild(detail(e));
    extra.appendChild(cell);
    return extra;
  }
  var rows = document.getElementById("rows");
  function render() {
    rows.textContent = "";
    var shown = 0, total = 0;
    events.forEach(function (e) {
      if (!active[e.severity]) { return; }
      if (codeFilter && e.code !== codeFilter) { return; }
      if (query && e._text.indexOf(query) === -1) { return; }
      total += 1;
      if (shown >= limit) { return; }
      shown += 1;
      var row = el("tr", null, "event");
      row.appendChild(el("td", String(e._no), "num"));
      row.appendChild(el("td", (e.timestamp || "").replace("T", " ").replace("Z", ""), "nowrap"));
      row.appendChild(el("td", e.severity, "nowrap " + cls(e.severity)));
      row.appendChild(el("td", e.code || "-", "nowrap"));
      row.appendChild(el("td", e.logger || "-"));
      row.appendChild(el("td", e.message, "msg"));
      row.addEventListener("click", function () {
        var next = row.nextSibling;
        if (next && next.className === "detail") { next.remove(); return; }
        row.parentNode.insertBefore(detailRow(e), row.nextSibling);
      });
      rows.appendChild(row);
      if (expandAll) { rows.appendChild(detailRow(e)); }
    });
    if (!total) {
      var empty = el("tr"), cell = el("td", "NIL. No events agree with the selection.");
      cell.colSpan = 6; empty.appendChild(cell); rows.appendChild(empty);
    }
    document.getElementById("count").textContent =
      "LISTED: " + shown + " OF " + total + " SELECTED EVENTS. EVENTS IN THE FILE: " +
      events.length + ". ENTRIES MARKED * ARE ERRORS.";
    document.getElementById("more").hidden = shown >= total;
    document.getElementById("expand").textContent = expandAll ? "Collapse all" : "Expand all";
  }
  document.getElementById("search").addEventListener("input", function (ev) {
    query = ev.target.value.trim().toLowerCase(); limit = 500; render();
  });
  select.addEventListener("change", function (ev) { codeFilter = ev.target.value; limit = 500; render(); });
  function setAll(test) {
    order.forEach(function (name) { active[name] = test(name); boxes[name].checked = active[name]; });
    render();
  }
  document.getElementById("problems").addEventListener("click", function () {
    setAll(function (name) { return order.indexOf(name) >= order.indexOf("WARNING"); });
  });
  document.getElementById("reset").addEventListener("click", function () {
    document.getElementById("search").value = ""; query = "";
    select.value = ""; codeFilter = ""; expandAll = false;
    setAll(function () { return true; });
  });
  document.getElementById("expand").addEventListener("click", function () {
    expandAll = !expandAll; render();
  });
  document.getElementById("print").addEventListener("click", function () { window.print(); });
  document.getElementById("more").addEventListener("click", function () { limit += 1000; render(); });
  render();
}());
</script>
</body>
</html>
"""


def write_html_report(
    events: Iterable[Event],
    path: Union[str, Path],
    *,
    title: str = "Run report",
    max_events: int = 20000,
) -> Path:
    """Write the events of a run to one HTML file.

    Parameters
    ----------
    events
        The events of the run.
    path
        The path of the HTML file.
    title
        The title of the page.
    max_events
        The maximum number of events in the file. If the run has more
        events, the file contains the last events. The counts at the
        top of the page always include all events.

    Returns
    -------
    pathlib.Path
        The path of the file.
    """
    items: List[Event] = list(events)
    report = EventReport.from_events(items)
    kept = items[-max_events:] if max_events and len(items) > max_events else items
    severities = ["TRACE", "DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL"]
    data = {
        "total": report.total,
        "first_number": len(items) - len(kept) + 1,
        "severities": severities,
        "counts": report.by_severity,
        "codes": sorted(report.by_code.items()),
        "failures": [
            {
                "fingerprint": key,
                "count": item["count"],
                "type": item["type"],
                "message": str(item["message"]).splitlines()[0][:200]
                if item["message"] else "",
            }
            for key, item in sorted(
                report.by_fingerprint.items(), key=lambda pair: -pair[1]["count"]
            )
        ],
        "events": [event.to_dict() for event in kept],
    }
    text = json.dumps(data, default=json_default, ensure_ascii=False)
    # Make the JSON text safe in an HTML script element.
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    if report.first and report.last:
        period = (
            f"{report.first.strftime('%Y-%m-%d %H:%M:%S')} TO "
            f"{report.last.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        period = "NIL"
    note = ""
    if len(kept) < len(items):
        note = (
            f"NOTE: SECTION 4 LISTS THE LAST {len(kept)} EVENTS. "
            "SECTIONS 1 TO 3 INCLUDE ALL EVENTS."
        )
    generated = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    page = (
        _PAGE.replace("__TITLE__", html.escape(title))
        .replace("__GENERATED__", generated)
        .replace("__TOTAL__", str(report.total))
        .replace("__WORST__", report.worst.name if report.worst else "NIL")
        .replace("__PERIOD__", period)
        .replace("__NOTE__", html.escape(note))
        .replace("__FOOTER__", html.escape(f"annunciator {__version__}"))
        .replace("__DATA__", text)
    )
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(page, encoding="utf-8")
    return file
