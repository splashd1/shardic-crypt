(() => {
  "use strict";

  const state = {
    phase: 1,
    trustees: new Map(),      // username -> {fingerprint, status}
    ceremony: null,           // {ceremony_id, status, slots, backup_queue, ...} or null
    vault: null,              // {prime_trustee, pool_trustees, threshold, pool_threshold}
    recovery: null,           // {repliedUsernames: Set, poolThreshold}
    finalized: null,          // {trustees_used, outdir}
    lastVerify: null,         // {match}
  };

  const $ = (id) => document.getElementById(id);
  const phaseSections = Array.from(document.querySelectorAll(".phase"));
  const phaseRadios = Array.from(document.querySelectorAll('input[name="phase"]'));
  const phaseIndicator = $("phase-indicator");

  function setPhase(n) {
    state.phase = n;
    phaseSections.forEach((el) => el.classList.toggle("is-active", Number(el.dataset.phase) === n));
    phaseRadios.forEach((el) => { el.checked = Number(el.value) === n; });
    phaseIndicator.textContent = `Phase ${n} of 4`;
  }

  phaseRadios.forEach((el) => el.addEventListener("change", () => setPhase(Number(el.value))));
  $("phase-prev").addEventListener("click", () => setPhase(Math.max(1, state.phase - 1)));
  $("phase-next").addEventListener("click", () => setPhase(Math.min(4, state.phase + 1)));

  // --------------------------------------------------------------- logging

  function log(text, isError) {
    const line = document.createElement("div");
    line.className = "ceremony-log__line" + (isError ? " ceremony-log__line--error" : "");
    const time = document.createElement("span");
    time.className = "ceremony-log__time";
    time.textContent = new Date().toLocaleTimeString();
    line.appendChild(time);
    line.appendChild(document.createTextNode(text));
    $("ceremony-log").prepend(line);
  }

  // -------------------------------------------------------------- diagram

  const SVGNS = "http://www.w3.org/2000/svg";
  const diagramSvg = $("ceremony-diagram");
  const edgesGroup = $("diagram-edges");
  const tokensGroup = $("diagram-tokens");
  const trusteesGroup = $("diagram-trustees");
  const combinerCenter = { x: 260, y: 178 };
  const diagramNodePositions = new Map();
  let knownDiagramNodes = new Set();

  function svgEl(tag, attrs) {
    const el = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
    return el;
  }

  function computeDiagramLayout(usernames) {
    const radius = 135;
    const n = usernames.length;
    diagramNodePositions.clear();
    usernames.forEach((username, i) => {
      const angle = -Math.PI / 2 + (2 * Math.PI * i) / n;
      diagramNodePositions.set(username, {
        x: combinerCenter.x + radius * Math.cos(angle),
        y: combinerCenter.y + radius * Math.sin(angle),
      });
    });
  }

  function renderDiagram() {
    const usernames = Array.from(state.trustees.keys()).sort();
    computeDiagramLayout(usernames);

    const primeName = state.vault ? state.vault.prime_trustee : null;
    const contributed = state.recovery ? state.recovery.repliedUsernames : new Set();
    const finalizedUsed = state.finalized ? new Set(state.finalized.trustees_used) : null;

    diagramSvg.classList.toggle("is-vault", !!state.vault);
    diagramSvg.classList.toggle("is-recovering", !!state.recovery && !state.finalized);
    diagramSvg.classList.toggle("is-done", !!state.finalized);

    edgesGroup.innerHTML = "";
    for (const username of usernames) {
      const pos = diagramNodePositions.get(username);
      const rec = state.trustees.get(username);
      let cls = "diagram-edge";
      if (finalizedUsed) {
        cls += finalizedUsed.has(username) ? " diagram-edge--contributed" : " diagram-edge--paused";
      } else if (state.recovery) {
        if (contributed.has(username)) cls += " diagram-edge--contributed";
        else if (rec.status === "paused") cls += " diagram-edge--paused";
        else cls += " diagram-edge--active";
      } else if (state.vault) {
        cls += " diagram-edge--sealed";
      } else if (rec.status === "paused") {
        cls += " diagram-edge--paused";
      }
      edgesGroup.appendChild(svgEl("line", {
        x1: combinerCenter.x, y1: combinerCenter.y, x2: pos.x, y2: pos.y, class: cls,
      }));
    }

    const nowKnown = new Set();
    trusteesGroup.innerHTML = "";
    for (const username of usernames) {
      nowKnown.add(username);
      const pos = diagramNodePositions.get(username);
      const rec = state.trustees.get(username);
      const isPrime = username === primeName;
      const isPaused = rec.status === "paused";
      const hasContributed = contributed.has(username) || (finalizedUsed && finalizedUsed.has(username));
      const notNeeded = finalizedUsed && !finalizedUsed.has(username);

      let cls = "trustee-node";
      if (!knownDiagramNodes.has(username)) cls += " is-entering";
      if (isPrime) cls += " trustee-node--prime";
      cls += isPaused ? " trustee-node--paused" : " trustee-node--live";
      if (hasContributed) cls += " trustee-node--contributed";
      if (notNeeded) cls += " trustee-node--not-needed";
      if (state.recovery && !state.finalized && !isPaused && !hasContributed) cls += " trustee-node--pulse";

      const g = svgEl("g", { class: cls, transform: `translate(${pos.x},${pos.y})` });
      g.appendChild(svgEl("circle", { class: "trustee-node__ring", r: 24 }));

      const label = svgEl("text", { class: "trustee-node__label", y: 4 });
      label.textContent = username;
      g.appendChild(label);

      if (isPrime || notNeeded) {
        const tag = svgEl("text", { class: "trustee-node__tag", y: -30 });
        tag.textContent = isPrime ? "prime" : "not needed";
        g.appendChild(tag);
      }

      const badgePos = svgEl("g", { transform: "translate(0,36)" });
      const badge = svgEl("g", { class: "trustee-node__badge" });
      badge.appendChild(svgEl("circle", { r: 7 }));
      badge.appendChild(svgEl("path", { d: "M-3,0 l2,2.5 l4,-5" }));
      badgePos.appendChild(badge);
      g.appendChild(badgePos);

      trusteesGroup.appendChild(g);
    }
    knownDiagramNodes = nowKnown;
  }

  function spawnToken(username) {
    const pos = diagramNodePositions.get(username);
    if (!pos) return;
    const token = svgEl("circle", { class: "diagram-token", r: 5, cx: pos.x, cy: pos.y });
    const motion = svgEl("animateMotion", {
      dur: "0.9s",
      fill: "freeze",
      path: `M0,0 L${combinerCenter.x - pos.x},${combinerCenter.y - pos.y}`,
    });
    token.appendChild(motion);
    tokensGroup.appendChild(token);
    motion.addEventListener("endEvent", () => token.remove());
    setTimeout(() => token.remove(), 1200);
  }

  // ------------------------------------------------------------- rendering

  function renderTrustees() {
    const grid = $("trustee-grid");
    grid.innerHTML = "";
    const primeName = state.vault ? state.vault.prime_trustee : null;
    const sorted = Array.from(state.trustees.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    for (const [username, rec] of sorted) {
      const card = document.createElement("div");
      card.className = "trustee-card" + (username === primeName ? " trustee-card--prime" : "");
      const dot = document.createElement("span");
      dot.className = "trustee-dot trustee-dot--" + (rec.status === "paused" ? "paused" : "live");
      const name = document.createElement("span");
      name.className = "trustee-card__name";
      name.textContent = username;
      const fp = document.createElement("span");
      fp.className = "trustee-card__fp";
      fp.textContent = rec.fingerprint ? rec.fingerprint.slice(0, 12) : "";
      card.append(dot, name, fp);
      grid.appendChild(card);
    }
  }

  function renderFormation() {
    const hasVault = !!state.vault;
    $("formation-callout").hidden = !hasVault;
    $("formation-pipeline").hidden = !hasVault;
    if (hasVault) {
      $("formation-prime").textContent = state.vault.prime_trustee;
      $("formation-pool").textContent = state.vault.pool_trustees.join(", ");
      $("formation-split-label").textContent =
        `prime mask + ${state.vault.pool_trustees.length} pool shards (pool threshold ${state.vault.pool_threshold})`;
      $("dormant-prime").textContent = state.vault.prime_trustee;
      $("dormant-pool").textContent = state.vault.pool_trustees.join(", ");
    }
  }

  function renderShardProgress() {
    const primeName = state.vault ? state.vault.prime_trustee : null;
    const replied = state.recovery ? state.recovery.repliedUsernames : new Set();
    $("shard-prime-status").className =
      "shard-dot " + (primeName && replied.has(primeName) ? "shard-dot--received" : "shard-dot--pending");

    const poolThreshold = state.recovery && state.recovery.poolThreshold != null
      ? state.recovery.poolThreshold
      : (state.vault ? state.vault.pool_threshold : "?");
    const poolReplied = Array.from(replied).filter((u) => u !== primeName);
    $("shard-pool-count").textContent = poolReplied.length;
    $("shard-pool-threshold").textContent = poolThreshold;

    const list = $("shard-pool-list");
    list.innerHTML = "";
    for (const username of poolReplied) {
      const chip = document.createElement("span");
      chip.className = "shard-chip";
      chip.textContent = username;
      list.appendChild(chip);
    }
  }

  function renderFinalize() {
    if (state.finalized) {
      $("finalize-trustees").textContent = state.finalized.trustees_used.join(", ");
      $("finalize-outdir").textContent = state.finalized.outdir;
    }
    const banner = $("verify-banner");
    if (state.lastVerify == null) {
      banner.className = "verify-banner verify-banner--pending";
      banner.textContent = "Recovery not yet verified.";
    } else if (state.lastVerify.match) {
      banner.className = "verify-banner verify-banner--match";
      banner.textContent = "MATCH — recovered plaintext is byte-for-byte identical to the original.";
    } else {
      banner.className = "verify-banner verify-banner--mismatch";
      banner.textContent = "MISMATCH — recovered plaintext does not match the original.";
    }
  }

  function renderControls() {
    const formed = !!state.ceremony && state.ceremony.status === "formed";
    $("btn-create-vault").disabled = !!state.vault || !formed;
    $("btn-start-recovery").disabled = !state.vault;
    $("btn-finalize").disabled = !state.recovery;
    $("btn-verify").disabled = !state.finalized;
  }

  function renderAll() {
    renderTrustees();
    renderFormation();
    renderShardProgress();
    renderFinalize();
    renderControls();
    renderDiagram();
  }

  // ------------------------------------------------------------ SSE wiring

  function applySnapshot(data) {
    state.trustees = new Map(data.trustees.map((t) => [t.username, { fingerprint: t.fingerprint, status: t.status }]));
    state.ceremony = data.ceremony;
    state.vault = data.vault;
    state.recovery = data.recovery
      ? { repliedUsernames: new Set(data.recovery.replied_usernames), poolThreshold: data.recovery.pool_threshold }
      : null;
    state.lastVerify = data.last_verify;
    // Can't distinguish "finalized" from "in-progress" purely from the
    // snapshot (recovery_session isn't cleared on finalize) -- `finalized`
    // stays unset on reconnect; the Verify button re-enables once Finalize
    // is (re-)clicked or a fresh recovery_finalized event lands.
    let phase = 1;
    if (state.lastVerify) phase = 4;
    else if (state.recovery) phase = 3;
    else if (state.vault) phase = 2;
    setPhase(phase);
    renderAll();
  }

  function connect() {
    const source = new EventSource("/events");
    source.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      handleEvent(msg.type, msg.data);
    };
    source.onerror = () => log("SSE connection lost -- browser will retry automatically.", true);
  }

  function handleEvent(type, data) {
    switch (type) {
      case "snapshot":
        applySnapshot(data);
        log("dashboard connected, state synced");
        return;
      case "trustee_registered":
        state.trustees.set(data.username, { fingerprint: data.fingerprint, status: "live" });
        log(`trustee registered: ${data.username} (${data.fingerprint.slice(0, 12)})`);
        break;
      case "trustee_status": {
        const rec = state.trustees.get(data.username);
        if (rec) rec.status = data.status;
        log(`${data.username} is now ${data.status}`);
        break;
      }
      case "ceremony_initiated": {
        const invited = data.invited.map((s) => `${s.username} (${s.role})`).join(", ");
        state.ceremony = { ceremony_id: data.ceremony_id, status: "forming" };
        log(`ceremony initiated: invited ${invited}` + (data.backup_queue.length ? `; backups: ${data.backup_queue.join(", ")}` : ""));
        break;
      }
      case "invitation_responded":
        log(`${data.role} invitation ${data.accept ? "accepted" : "declined"}`);
        break;
      case "invitation_expired":
        log(`${data.role} invitation to ${data.username} expired (no response within the TTL)`, true);
        break;
      case "backfill_invited":
        log(`ceremony backfill: ${data.username} invited to fill the ${data.role} slot`);
        break;
      case "ceremony_formed":
        if (state.ceremony) state.ceremony.status = "formed";
        log("ceremony formed — every slot accepted, ready to create the vault");
        break;
      case "ceremony_failed":
        if (state.ceremony) state.ceremony.status = "failed";
        log("ceremony failed — backup list exhausted before every slot was filled", true);
        break;
      case "vault_created":
        state.vault = data;
        state.ceremony = null;
        log(`vault created — prime: ${data.prime_trustee}, pool: ${data.pool_trustees.join(", ")}`);
        setPhase(2);
        break;
      case "recovery_started":
        state.recovery = { repliedUsernames: new Set(), poolThreshold: state.vault ? state.vault.pool_threshold : null };
        state.finalized = null;
        state.lastVerify = null;
        log(`recovery session started (${data.session_id})`);
        setPhase(3);
        break;
      case "unsealed_shard_received":
        spawnToken(data.username);
        if (state.recovery) {
          state.recovery.repliedUsernames.add(data.username);
          state.recovery.poolThreshold = data.pool_threshold;
        }
        log(`unsealed shard received from ${data.username} (${data.replied_count} received so far)`);
        break;
      case "recovery_finalized":
        state.finalized = data;
        log(`recovery finalized — trustees used: ${data.trustees_used.join(", ")}`);
        break;
      case "recovery_verified":
        state.lastVerify = data;
        log(data.match ? "verification: MATCH" : "verification: MISMATCH");
        setPhase(4);
        break;
      default:
        log(`unrecognized event: ${type}`);
    }
    renderAll();
  }

  // ------------------------------------------------------------- controls

  function operatorToken() {
    return $("admin-token").value;
  }

  async function callAdmin(path) {
    const res = await fetch(path, { method: "POST", headers: { "Authorization": `Bearer ${operatorToken()}` } });
    let body = {};
    try { body = await res.json(); } catch (_e) { /* no body */ }
    if (!res.ok) {
      log(`${path} failed: ${body.error || res.status}`, true);
      return null;
    }
    return body;
  }

  $("admin-token").value = localStorage.getItem("shardic_operator_token") || "";
  $("admin-token").addEventListener("input", (e) => {
    localStorage.setItem("shardic_operator_token", e.target.value);
  });

  $("btn-create-vault").addEventListener("click", () => callAdmin("/admin/vault/create"));
  $("btn-start-recovery").addEventListener("click", () => callAdmin("/admin/recovery/start"));
  $("btn-finalize").addEventListener("click", async () => {
    const result = await callAdmin("/admin/recovery/finalize");
    if (result) renderControls();
  });
  $("btn-verify").addEventListener("click", () => callAdmin("/admin/recovery/verify"));

  setPhase(1);
  connect();
})();
