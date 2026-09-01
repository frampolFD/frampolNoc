async function api(path, options = {}) {
  const opts = Object.assign({ credentials: "same-origin" }, options);
  if (opts.body && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
    opts.headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  }
  const res = await fetch(path, opts);
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("Not authenticated");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (e) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

function fmtBps(bps) {
  if (bps === null || bps === undefined) return "—";
  if (bps >= 1e9) return (bps / 1e9).toFixed(2) + " Gbps";
  if (bps >= 1e6) return (bps / 1e6).toFixed(2) + " Mbps";
  if (bps >= 1e3) return (bps / 1e3).toFixed(1) + " Kbps";
  return bps.toFixed(0) + " bps";
}

function fmtPercent(v) {
  if (v === null || v === undefined) return "—";
  return v.toFixed(1) + "%";
}

function fmtMs(v) {
  if (v === null || v === undefined) return "—";
  return v.toFixed(1) + " ms";
}

function fmtTime(iso) {
  if (!iso) return "never";
  const d = new Date(iso);
  return d.toLocaleTimeString();
}

function healthClass(health) {
  return "health-" + (health || "unknown");
}
