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

// Always 24-hour, never AM/PM — an explicit locale/options object rather
// than relying on the browser's default locale, which may render 12-hour
// time depending on the user's system settings.
const CHART_TIME_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const CLOCK_TIME_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

// Graph axis labels: HH:mm, no seconds.
function fmtChartTime(msOrDate) {
  const d = msOrDate instanceof Date ? msOrDate : new Date(msOrDate);
  return CHART_TIME_FORMATTER.format(d);
}

// Other displayed timestamps (e.g. "last poll"): HH:mm:ss, seconds are
// useful there for judging how fresh a reading is.
function fmtTime(iso) {
  if (!iso) return "never";
  return CLOCK_TIME_FORMATTER.format(new Date(iso));
}

function healthClass(health) {
  return "health-" + (health || "unknown");
}

// The /measurements endpoint interleaves independently-scheduled ICMP rows
// (latency/loss/jitter/availability, traffic fields null) and SNMP rows
// (rx/tx/total_bps, ICMP fields null) on one timeline. A traffic dataset
// must only be built from rows where that specific field is a real,
// finite number — never from an ICMP-only row's null, and never treating
// non-finite values (NaN/Infinity, which can't happen server-side today
// but shouldn't silently render as 0 if they ever did) as valid.
function trafficPoints(measurements, field) {
  return measurements
    .filter(m => Number.isFinite(m[field]))
    .map(m => ({ x: new Date(m.timestamp).getTime(), y: m[field] }));
}

// A freshly-selected SNMP interface's first successful poll only
// establishes the counter baseline (no prior sample to diff against, so
// no rate) — the *second* poll produces the first graphable point. With
// only one point on the graph there is nothing for a line to connect, so
// it must render as a visible dot instead of silently vanishing; once a
// second point arrives a line becomes meaningful and dominates instead.
function pointRadiusForCount(count) {
  return count === 1 ? 3 : 0;
}
