/* TAK Device Monitor — live view over the backend snapshot stream. */
(function () {
  "use strict";

  var state = { snapshot: null, clockSkew: 0 };
  var el = {
    total: document.getElementById("sum-total"),
    online: document.getElementById("sum-online"),
    stale: document.getElementById("sum-stale"),
    offline: document.getElementById("sum-offline"),
    rows: document.getElementById("device-rows"),
    empty: document.getElementById("empty-state"),
    objectsCount: document.getElementById("sum-objects"),
    objectRows: document.getElementById("object-rows"),
    objectsEmpty: document.getElementById("objects-empty"),
    objectsPanel: document.getElementById("objects-panel"),
    objectsToggle: document.getElementById("objects-toggle"),
    objcheckNote: document.getElementById("objcheck-note"),
    takPill: document.getElementById("tak-pill"),
    takPillText: document.getElementById("tak-pill-text"),
    udpPill: document.getElementById("udp-pill"),
    udpPillText: document.getElementById("udp-pill-text"),
    martiPill: document.getElementById("marti-pill"),
    martiPillText: document.getElementById("marti-pill-text"),
    bridgePill: document.getElementById("bridge-pill"),
    bridgePillText: document.getElementById("bridge-pill-text"),
  };

  // ---- websocket to the Django backend --------------------------------
  var retryMs = 1000;

  function connect() {
    var proto = location.protocol === "https:" ? "wss://" : "ws://";
    var ws = new WebSocket(proto + location.host + "/ws/devices");

    ws.onopen = function () {
      retryMs = 1000;
      setPill(el.bridgePill, el.bridgePillText, "ok", "bridge connected");
    };
    ws.onmessage = function (evt) {
      var msg = JSON.parse(evt.data);
      if (msg.type !== "snapshot") return;
      state.snapshot = msg;
      state.clockSkew = Date.now() - msg.now;
      render();
    };
    ws.onclose = function () {
      setPill(el.bridgePill, el.bridgePillText, "bad", "bridge reconnecting…");
      setTimeout(connect, retryMs);
      retryMs = Math.min(retryMs * 2, 15000);
    };
  }

  function setPill(pill, textEl, cls, text) {
    pill.classList.remove("ok", "warn", "bad");
    if (cls) pill.classList.add(cls);
    textEl.textContent = text;
  }

  // ---- rendering -------------------------------------------------------
  var STATUS_LABEL = { online: "Online", stale: "Stale", offline: "Offline" };

  function relTime(epochMs) {
    if (!epochMs) return "—";
    var secs = Math.max(0, Math.round((Date.now() - state.clockSkew - epochMs) / 1000));
    if (secs < 60) return secs + "s ago";
    var mins = Math.floor(secs / 60);
    if (mins < 60) return mins + "m " + (secs % 60) + "s ago";
    var hours = Math.floor(mins / 60);
    if (hours < 24) return hours + "h " + (mins % 60) + "m ago";
    return Math.floor(hours / 24) + "d ago";
  }

  function deviceLabel(d) {
    if (d.platform && d.device) return d.platform + " · " + d.device;
    return d.platform || d.device || "—";
  }

  function td(cls, text) {
    var cell = document.createElement("td");
    if (cls) cell.className = cls;
    cell.textContent = text;
    return cell;
  }

  function render() {
    var snap = state.snapshot;
    if (!snap) return;

    el.total.textContent = snap.summary.total;
    el.online.textContent = snap.summary.online;
    el.stale.textContent = snap.summary.stale;
    // Offline devices are pruned; the tile shows the running removal total.
    el.offline.textContent = snap.summary.removed != null
      ? snap.summary.removed
      : snap.summary.offline;

    var tak = snap.tak || {};
    if (tak.state === "connected") {
      setPill(el.takPill, el.takPillText, "ok", "TAK server connected");
    } else if (tak.state === "connecting") {
      setPill(el.takPill, el.takPillText, "warn", "TAK server connecting…");
    } else {
      setPill(el.takPill, el.takPillText, "bad", "TAK server " + (tak.state || "offline"));
    }
    el.takPill.title = (tak.url || "") + (tak.error ? " — " + tak.error : "");

    var udp = snap.udp || {};
    if (udp.state && udp.state !== "disabled") {
      el.udpPill.hidden = false;
      if (udp.state === "listening") {
        setPill(el.udpPill, el.udpPillText, "ok", "UDP listening");
      } else {
        setPill(el.udpPill, el.udpPillText, "bad", "UDP " + udp.state);
      }
      el.udpPill.title = (udp.url || "") + (udp.error ? " — " + udp.error : "");
    } else {
      el.udpPill.hidden = true;
    }

    var marti = snap.marti || {};
    if (marti.state && marti.state !== "disabled") {
      el.martiPill.hidden = false;
      setPill(el.martiPill, el.martiPillText,
        marti.state === "ok" ? "ok" : "bad",
        marti.state === "ok" ? "TAK API" : "TAK API " + marti.state);
      el.martiPill.title = (marti.url || "") + (marti.error ? " — " + marti.error : "");
    } else {
      el.martiPill.hidden = true;
    }

    el.empty.hidden = snap.devices.length > 0;

    var tbody = document.createElement("tbody");
    tbody.id = "device-rows";
    snap.devices.forEach(function (d) {
      var tr = document.createElement("tr");
      if (d.status === "offline") tr.className = "is-offline";

      var statusTd = document.createElement("td");
      var span = document.createElement("span");
      span.className = "status " + d.status;
      var dot = document.createElement("span");
      dot.className = "dot";
      span.appendChild(dot);
      span.appendChild(
        document.createTextNode(STATUS_LABEL[d.status] || d.status)
      );
      statusTd.appendChild(span);
      if (d.server_status) statusTd.title = "TAK server: " + d.server_status;
      tr.appendChild(statusTd);

      tr.appendChild(td("c-callsign", d.callsign || "—"));
      var uidTd = td("c-uid", d.uid);
      uidTd.title = d.uid;
      tr.appendChild(uidTd);
      var deviceTd = td("c-device", deviceLabel(d));
      deviceTd.title = deviceLabel(d);
      tr.appendChild(deviceTd);
      tr.appendChild(td("c-type", d.cot_type || "—"));
      tr.appendChild(td("c-mgrs", d.mgrs || "—"));
      tr.appendChild(
        td(
          "c-latlon",
          d.lat != null && d.lon != null
            ? d.lat.toFixed(5) + ", " + d.lon.toFixed(5)
            : "—"
        )
      );

      var protoTd = document.createElement("td");
      var badge = document.createElement("span");
      badge.className = "badge";
      // No live transport but known to the server -> came from the Marti API.
      badge.textContent = d.protocol || (d.marti ? "TAK API" : "SSL");
      protoTd.appendChild(badge);
      tr.appendChild(protoTd);

      tr.appendChild(td("c-ip", d.ip || "—"));
      var ping = td("c-ping", relTime(d.last_seen));
      ping.dataset.lastSeen = d.last_seen || "";
      tr.appendChild(ping);

      tbody.appendChild(tr);
    });
    el.rows.replaceWith(tbody);
    el.rows = tbody;

    renderObjects(snap.objects);
    renderObjcheck(snap.objcheck);
  }

  // ---- plotted objects -------------------------------------------------
  var AFFIL_CLASS = {
    friendly: "affil-friendly", hostile: "affil-hostile",
    neutral: "affil-neutral", unknown: "affil-unknown",
  };

  function geomLabel(g) {
    if (!g) return "—";
    if (g.type === "Point") return "point";
    if (g.type === "LineString") return "line (" + g.coordinates.length + ")";
    if (g.type === "Polygon") return "area (" + (g.coordinates[0].length - 1) + ")";
    return g.type.toLowerCase();
  }

  // Routine-check verdicts -> status style + label.
  var CHECK_VIEW = {
    verified: { cls: "online", label: "Verified" },
    unverified: { cls: "stale", label: "Unverified" },
    missing: { cls: "offline", label: "Missing" },
    expired: { cls: "offline", label: "Expired" },
  };

  function renderObjcheck(oc) {
    if (!oc || !oc.last_check) {
      el.objcheckNote.textContent = "";
      return;
    }
    var c = oc.counts || {};
    var parts = [c.verified + " verified"];
    if (c.unverified) parts.push(c.unverified + " unverified");
    if (c.missing) parts.push(c.missing + " missing");
    if (c.expired) parts.push(c.expired + " expired");
    if (oc.removed_total) parts.push(oc.removed_total + " pruned");
    var text = "check: " + parts.join(" · ") + " · ran " + relTime(oc.last_check);
    if (oc.state === "error") text += " · statesaver error";
    el.objcheckNote.textContent = text;
  }

  function renderObjects(fc) {
    var feats = (fc && fc.features) || [];
    el.objectsCount.textContent = feats.length;
    el.objectsEmpty.hidden = feats.length > 0;

    var tbody = document.createElement("tbody");
    tbody.id = "object-rows";
    feats.forEach(function (f) {
      var p = f.properties || {};
      var tr = document.createElement("tr");

      var chk = p.check || {};
      var view = CHECK_VIEW[chk.state];
      var chkTd = document.createElement("td");
      if (view) {
        var cspan = document.createElement("span");
        cspan.className = "status " + view.cls;
        var cdot = document.createElement("span");
        cdot.className = "dot";
        cspan.appendChild(cdot);
        cspan.appendChild(document.createTextNode(view.label));
        chkTd.appendChild(cspan);
        var vouched = Object.keys(p.sources || {}).join(", ");
        chkTd.title =
          "checked " + relTime(chk.checked_at) +
          (vouched ? " · seen via: " + vouched : "") +
          (chk.misses ? " · missed " + chk.misses + "×" : "");
        if (view.cls === "offline") tr.className = "is-offline";
      } else {
        chkTd.textContent = "—";
        chkTd.title = "awaiting first routine check";
      }
      tr.appendChild(chkTd);

      tr.appendChild(td("c-kind", p.kind || "—"));
      tr.appendChild(td("c-label", p.callsign || p.uid || "—"));

      var affTd = document.createElement("td");
      var aff = document.createElement("span");
      aff.className = "affil " + (AFFIL_CLASS[p.affiliation] || "affil-other");
      var adot = document.createElement("span");
      adot.className = "dot";
      aff.appendChild(adot);
      aff.appendChild(document.createTextNode(p.affiliation || "—"));
      affTd.appendChild(aff);
      tr.appendChild(affTd);

      tr.appendChild(td("c-type", p.cot_type || "—"));
      tr.appendChild(td("c-geom", geomLabel(f.geometry)));
      tr.appendChild(td("c-mgrs", p.mgrs || "—"));
      tr.appendChild(
        td("c-latlon",
          p.lat != null && p.lon != null
            ? p.lat.toFixed(5) + ", " + p.lon.toFixed(5) : "—")
      );
      var rem = td("c-remarks", p.remarks || "—");
      if (p.remarks) rem.title = p.remarks;
      tr.appendChild(rem);

      tbody.appendChild(tr);
    });
    el.objectRows.replaceWith(tbody);
    el.objectRows = tbody;
  }

  el.objectsToggle.addEventListener("change", function () {
    el.objectsPanel.classList.toggle("collapsed", !el.objectsToggle.checked);
  });

  // Tick the "last ping" column between snapshots.
  setInterval(function () {
    if (!state.snapshot) return;
    var cells = el.rows.querySelectorAll("td.c-ping");
    cells.forEach(function (cell) {
      var ts = Number(cell.dataset.lastSeen);
      if (ts) cell.textContent = relTime(ts);
    });
  }, 1000);

  connect();
})();
