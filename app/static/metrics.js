(function () {
  var POLL_MS = 5000;
  var timer = null;

  var statusEl = document.getElementById("read-status");
  var lastReadEl = document.getElementById("last-read");

  function text(id, value) {
    document.getElementById(id).textContent = value;
  }

  function formatBytes(value) {
    var units = ["B", "KB", "MB", "GB", "TB"];
    var size = Number(value);
    var unit = 0;
    while (size >= 1024 && unit < units.length - 1) {
      size /= 1024;
      unit += 1;
    }
    var digits = unit === 0 ? 0 : 1;
    return size.toFixed(digits) + " " + units[unit];
  }

  function formatRate(value) {
    if (value === null || value === undefined) {
      return "—";
    }
    return formatBytes(value) + "/s";
  }

  function cell(value) {
    var item = document.createElement("td");
    item.textContent = value;
    return item;
  }

  function emptyRow(columnCount, message) {
    var row = document.createElement("tr");
    var item = document.createElement("td");
    item.colSpan = columnCount;
    item.textContent = message;
    row.appendChild(item);
    return row;
  }

  function renderNetwork(rows) {
    var body = document.getElementById("network-body");
    body.replaceChildren();
    if (!rows.length) {
      body.appendChild(emptyRow(4, "No non-loopback interfaces."));
      return;
    }
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.appendChild(cell(row.name));
      tr.appendChild(cell(formatBytes(row.bytes_recv)));
      tr.appendChild(cell(formatBytes(row.bytes_sent)));
      if (row.recv_rate === null || row.sent_rate === null) {
        tr.appendChild(cell("—"));
      } else {
        tr.appendChild(cell(formatRate(row.recv_rate) + " in, " + formatRate(row.sent_rate) + " out"));
      }
      body.appendChild(tr);
    });
  }

  function renderPorts(rows) {
    var body = document.getElementById("ports-body");
    body.replaceChildren();
    if (!rows.length) {
      body.appendChild(emptyRow(5, "No listening TCP or UDP ports."));
      return;
    }
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.appendChild(cell(String(row.port)));
      tr.appendChild(cell(row.protocol));
      tr.appendChild(cell(row.address));
      tr.appendChild(cell(row.process || "—"));
      tr.appendChild(cell(row.pid === null || row.pid === undefined ? "—" : String(row.pid)));
      body.appendChild(tr);
    });
  }

  function render(metrics) {
    var load = metrics.cpu.load_average;
    text("cpu-busy", Number(metrics.cpu.busy_percent).toFixed(1) + "%");
    text("cpu-load", Number(load[0]).toFixed(2) + ", " + Number(load[1]).toFixed(2) + ", " + Number(load[2]).toFixed(2));
    text("mem-total", formatBytes(metrics.memory.total));
    text("mem-used", formatBytes(metrics.memory.used));
    text("mem-available", formatBytes(metrics.memory.available));
    text("mem-percent", Number(metrics.memory.used_percent).toFixed(1) + "%");
    text("swap-total", formatBytes(metrics.memory.swap_total));
    text("swap-used", formatBytes(metrics.memory.swap_used));
    renderNetwork(metrics.network);
    renderPorts(metrics.ports);
    lastReadEl.textContent = "Last successful read: " + metrics.read_at;
  }

  function showFailure() {
    statusEl.classList.add("status-error");
    statusEl.textContent = "The latest read failed.";
  }

  function stop() {
    if (timer !== null) {
      clearInterval(timer);
      timer = null;
    }
  }

  function refresh() {
    fetch("/api/metrics", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    }).then(function (response) {
      if (response.status === 401) {
        stop();
        window.location.assign("/login");
        return null;
      }
      if (!response.ok) {
        showFailure();
        return null;
      }
      return response.json();
    }).then(function (body) {
      if (!body) {
        return;
      }
      if (!body.metrics) {
        showFailure();
        return;
      }
      render(body.metrics);
      statusEl.classList.remove("status-error");
      statusEl.textContent = "Live read succeeded.";
    }).catch(function () {
      showFailure();
    });
  }

  refresh();
  timer = window.setInterval(refresh, POLL_MS);
  window.addEventListener("pagehide", stop);
})();
