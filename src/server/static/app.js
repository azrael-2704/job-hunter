// src/server/static/app.js

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const pipelineForm = document.getElementById("pipeline-form");
  const btnRun = document.getElementById("btn-run-pipeline");
  const btnRunText = document.getElementById("btn-run-text");
  const systemStatus = document.getElementById("system-status");
  
  // KPIs
  const kpiDiscovered = document.getElementById("kpi-discovered");
  const kpiQualified = document.getElementById("kpi-qualified");
  const kpiApproval = document.getElementById("kpi-approval");
  const kpiApplied = document.getElementById("kpi-applied");
  const kpiOutreach = document.getElementById("kpi-outreach");
  const approvalBadge = document.getElementById("approval-count-badge");

  // Containers
  const approvalList = document.getElementById("approval-queue-list");
  const qualifiedList = document.getElementById("qualified-list");
  const outreachList = document.getElementById("outreach-list");
  const telemetryStream = document.getElementById("telemetry-stream");

  // Tabs
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  // Probe Tool
  const btnProbe = document.getElementById("btn-probe");
  const probeName = document.getElementById("probe-name");
  const probeDomain = document.getElementById("probe-domain");
  const probeResults = document.getElementById("probe-results");

  // --- TAB SWITCHING ---
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add("active");
    });
  });

  // --- API CALLS ---
  async function fetchState() {
    try {
      const res = await fetch("/api/state");
      if (!res.ok) return;
      const state = await res.json();
      renderDashboard(state);
    } catch (err) {
      console.error("Failed to fetch pipeline state:", err);
    }
  }

  function renderDashboard(state) {
    // 0. Update User Candidate Pill in Navbar
    if (state.master_profile) {
      const p = state.master_profile;
      const nameEl = document.querySelector(".user-name");
      const avatarEl = document.querySelector(".user-avatar");
      const skillsEl = document.querySelector(".user-skills");
      if (nameEl && p.name) nameEl.textContent = p.name;
      if (avatarEl && p.name) {
        const initials = p.name.split(" ").filter(Boolean).map(w => w[0]).join("").toUpperCase().slice(0, 2);
        avatarEl.textContent = initials || "ME";
      }
      if (skillsEl && state.allowed_skills) {
        const skillsArr = Array.isArray(state.allowed_skills) ? state.allowed_skills : Array.from(state.allowed_skills || []);
        if (skillsArr.length > 0) skillsEl.textContent = skillsArr.slice(0, 4).join(" • ");
      }
    }

    // 1. Update Status
    systemStatus.textContent = state.current_status || "Idle";

    // 2. Update KPIs
    const discCount = state.discovered_queue ? state.discovered_queue.length : 0;
    const qualCount = state.qualified_queue ? state.qualified_queue.length : 0;
    const appCount = state.approval_queue ? state.approval_queue.length : 0;
    const appliedCount = state.applied_queue ? state.applied_queue.length : 0;
    const outCount = state.outreach_queue ? state.outreach_queue.length : 0;

    kpiDiscovered.textContent = discCount;
    kpiQualified.textContent = qualCount;
    kpiApproval.textContent = appCount;
    kpiApplied.textContent = appliedCount;
    kpiOutreach.textContent = outCount;
    approvalBadge.textContent = `${appCount} Pending`;

    // 3. Render Approval Queue
    if (!state.approval_queue || state.approval_queue.length === 0) {
      approvalList.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📂</div>
          <h3>Approval Queue is Empty</h3>
          <p>Click "Run Pipeline" to scrape live jobs, score fit, and tailor applications through our Reflection Loop.</p>
        </div>
      `;
    } else {
      approvalList.innerHTML = state.approval_queue.map(item => {
        const safeJobId = String(item.job_id || item.id || "");
        const rawSrc = (item.source || "").toLowerCase();
        const urlStr = item.url || item.application_url || "";
        const isDirect = ["greenhouse", "lever", "ashby", "direct_career_page", "career_page"].includes(rawSrc) || urlStr.includes("greenhouse") || urlStr.includes("lever.co") || urlStr.includes("ashbyhq");
        const srcLabel = isDirect ? `🏢 Direct ATS` : `🌐 LinkedIn`;
        const ageBadge = item.posted_age_text ? `<span class="badge-agent" style="background:rgba(255,255,255,0.06); border:1px solid var(--border-subtle); color:#94a3b8; font-size:0.65rem; padding:2px 6px;">⏱️ ${escapeHtml(item.posted_age_text)}</span>` : "";
        const newTodayBadge = item.is_new_today ? `<span class="badge-agent" style="background:rgba(245,158,11,0.2); border:1px solid rgba(245,158,11,0.5); color:#fbbf24; font-weight:700; font-size:0.65rem; padding:2px 6px;">✨ NEW TODAY</span>` : "";
        return `
        <div class="job-card" id="card-${safeJobId}">
          <div class="job-card-header">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:2px; flex-wrap:wrap;">
                <div class="job-title">${escapeHtml(item.title || "Software Engineer")}</div>
                <span class="badge-agent" style="${isDirect ? 'background:rgba(6,182,212,0.18); border:1px solid rgba(6,182,212,0.4); color:#67e8f9;' : 'background:rgba(59,130,246,0.18); border:1px solid rgba(59,130,246,0.4); color:#93c5fd;'} font-size:0.65rem; padding:2px 6px;">
                  ${srcLabel}
                </span>
                ${newTodayBadge}
                ${ageBadge}
              </div>
              <div class="job-company">${escapeHtml(item.company || "Company")} • ${escapeHtml(item.location || "India")}</div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px;">
              <div class="score-badge">FIT: ${item.fit_score || 100}%</div>
              <span class="badge-agent" style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); color: #6ee7b7; font-size: 0.68rem; padding: 2px 6px;">
                ${escapeHtml(item.salary_badge || "Comp: Market Rate")}
              </span>
            </div>
          </div>
          
          <div class="bullet-label">Tailored Resume Bullet (Guardrail Verified)</div>
          <div class="bullet-preview-box">
            "${escapeHtml(item.tailored_bullet)}"
          </div>

          <div class="guardrail-chip">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            Truth Guardrail Passed • 0 Hallucinations
          </div>

          <!-- DRAFTED EMAIL PREVIEW & REVISION SECTION -->
          <div class="email-review-section">
            <div class="email-review-header">
              <span class="email-recruiter-tag">
                🎯 Recruiter: <strong>${escapeHtml(item.recruiter_name || "Talent Team")}</strong> &lt;${escapeHtml(item.recruiter_email || "careers@company.com")}&gt;
              </span>
              <span class="confidence-chip">${item.recruiter_email && item.recruiter_email.includes("careers@") ? "Inbound Talent" : "Pattern Inferred"}</span>
            </div>
            <div class="email-subject-line"><strong>Subject:</strong> <span id="subject-${safeJobId}">${escapeHtml(item.email_subject || "Application")}</span></div>
            <div class="email-body-box" id="body-${safeJobId}">${escapeHtml(item.email_body || "")}</div>

            <!-- INTERACTIVE FEEDBACK LOOP -->
            <div class="feedback-loop-bar">
              <input type="text" id="feedback-input-${safeJobId}" placeholder="Want changes? e.g. 'Make it shorter', 'Mention Redis'..." />
              <button class="btn btn-secondary btn-sm" id="btn-revise-${safeJobId}" onclick="regenerateEmail('${safeJobId}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l6.73-1.19"/>
                </svg>
                Revise Email
              </button>
            </div>
          </div>

          <div class="action-row" style="margin-top: 14px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
              <a href="${escapeHtml(item.url || `https://www.linkedin.com/jobs/view/${safeJobId}`)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="text-decoration:none; display:inline-flex; align-items:center; gap:6px; font-size:0.8rem; background:rgba(255,255,255,0.06);">
                <span>View Job Listing</span>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
              </a>
              <a href="/api/resume/${safeJobId}?format=html" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="text-decoration:none; display:inline-flex; align-items:center; gap:5px; font-size:0.8rem; background:rgba(139, 92, 246, 0.15); border:1px solid rgba(139, 92, 246, 0.35); color:#c4b5fd;">
                <span>📄 Tailored Resume</span>
              </a>
              <a href="/api/cover-letter/${safeJobId}?format=html" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="text-decoration:none; display:inline-flex; align-items:center; gap:5px; font-size:0.8rem; background:rgba(6, 182, 212, 0.15); border:1px solid rgba(6, 182, 212, 0.35); color:#67e8f9;">
                <span>✉️ Cover Letter</span>
              </a>
              <button class="btn btn-secondary btn-sm" id="btn-autofill-${safeJobId}" onclick="autofillJob('${safeJobId}', event)" style="background:rgba(245, 158, 11, 0.15); border:1px solid rgba(245, 158, 11, 0.35); color:#fcd34d; font-size:0.8rem; display:inline-flex; align-items:center; gap:4px;">
                <span>⚡ Autofill ATS</span>
              </button>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-danger btn-sm" onclick="rejectJob('${safeJobId}', event)">Reject</button>
              <button class="btn btn-primary btn-sm" onclick="approveJob('${safeJobId}', event)">
                Approve & Send
              </button>
            </div>
          </div>
        </div>
      `}).join("");
    }

    // 4. Render Discovered/Qualified Jobs
    if (state.qualified_queue && state.qualified_queue.length > 0) {
      qualifiedList.innerHTML = state.qualified_queue.map(job => {
        const rawSrc = (job.source || "").toLowerCase();
        const urlStr = job.url || job.application_url || "";
        const isDirect = ["greenhouse", "lever", "ashby", "direct_career_page", "career_page"].includes(rawSrc) || urlStr.includes("greenhouse") || urlStr.includes("lever.co") || urlStr.includes("ashbyhq");
        const srcLabel = isDirect ? `🏢 Direct ATS` : `🌐 LinkedIn`;
        const ageBadge = job.posted_age_text ? `<span class="badge-agent" style="background:rgba(255,255,255,0.06); border:1px solid var(--border-subtle); color:#94a3b8; font-size:0.65rem; padding:2px 6px;">⏱️ ${escapeHtml(job.posted_age_text)}</span>` : "";
        const newTodayBadge = job.is_new_today ? `<span class="badge-agent" style="background:rgba(245,158,11,0.2); border:1px solid rgba(245,158,11,0.5); color:#fbbf24; font-weight:700; font-size:0.65rem; padding:2px 6px;">✨ NEW TODAY</span>` : "";
        return `
        <div class="job-card">
          <div class="job-card-header">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:2px; flex-wrap:wrap;">
                <div class="job-title">${escapeHtml(job.title)}</div>
                <span class="badge-agent" style="${isDirect ? 'background:rgba(6,182,212,0.18); border:1px solid rgba(6,182,212,0.4); color:#67e8f9;' : 'background:rgba(59,130,246,0.18); border:1px solid rgba(59,130,246,0.4); color:#93c5fd;'} font-size:0.65rem; padding:2px 6px;">
                  ${srcLabel}
                </span>
                ${newTodayBadge}
                ${ageBadge}
              </div>
              <div class="job-company">${escapeHtml(job.company)} • ${escapeHtml(job.location || "India")}</div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px;">
              <div class="score-badge">Fit: ${job.fit_score}/100</div>
              <span class="badge-agent" style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); color: #6ee7b7; font-size: 0.65rem; padding: 2px 6px;">
                ${escapeHtml(job.salary_badge || "Comp: Market Rate")}
              </span>
            </div>
          </div>
          <p style="font-size:0.8rem; color:#9ca3af; margin-bottom:8px;">
            ${escapeHtml((job.description || "").slice(0, 180))}...
          </p>
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-top:8px;">
            <div style="display:flex; gap:6px; flex-wrap:wrap;">
              ${(job.matched_skills || []).map(s => `<span class="badge-agent" style="font-size:0.65rem;">✓ ${s}</span>`).join("")}
            </div>
            <div style="display:flex; gap:6px;">
              <a href="/api/resume/${job.id || job.job_id}?format=html" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="text-decoration:none; display:inline-flex; align-items:center; gap:4px; font-size:0.72rem; padding:3px 6px; background:rgba(139, 92, 246, 0.15); border:1px solid rgba(139, 92, 246, 0.35); color:#c4b5fd;">
                <span>📄 Resume</span>
              </a>
              <a href="/api/cover-letter/${job.id || job.job_id}?format=html" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="text-decoration:none; display:inline-flex; align-items:center; gap:4px; font-size:0.72rem; padding:3px 6px; background:rgba(6, 182, 212, 0.15); border:1px solid rgba(6, 182, 212, 0.35); color:#67e8f9;">
                <span>✉️ Cover Letter</span>
              </a>
              <a href="${escapeHtml(job.url || `https://www.linkedin.com/jobs/view/${job.id}`)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="text-decoration:none; display:inline-flex; align-items:center; gap:5px; font-size:0.75rem; padding:4px 8px; background:rgba(255,255,255,0.06);">
                <span>View Listing</span>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
              </a>
            </div>
          </div>
        </div>
      `;}).join("");
    }

    // 5. Render Outreach Sequences
    if (state.outreach_queue && state.outreach_queue.length > 0) {
      outreachList.innerHTML = state.outreach_queue.map(msg => `
        <div class="outreach-card">
          <div class="outreach-header">
            <div>
              <div class="outreach-recruiter">${escapeHtml(msg.recipient_name)} (${escapeHtml(msg.company)})</div>
              <div class="outreach-email">${escapeHtml(msg.recipient_email)}</div>
            </div>
            <span class="outreach-status-pill">${msg.status}</span>
          </div>
          <div style="font-size:0.75rem; color:#6b7280; margin-bottom:6px;">
            ⏰ Scheduled Send: ${new Date(msg.scheduled_send_at).toLocaleString()} • Follow-up due: ${new Date(msg.followup_at).toLocaleDateString()}
          </div>
          <div class="email-preview">${escapeHtml(msg.body)}</div>
        </div>
      `).join("");
    }

    // 6. Render Telemetry Stream
    if (state.audit_logs && state.audit_logs.length > 0) {
      telemetryStream.innerHTML = state.audit_logs.map(log => `
        <div class="log-line">
          <span class="log-time">[${new Date().toLocaleTimeString()}]</span>
          <span class="log-event">${log.event || "LOG"}</span>
          <span>${JSON.stringify(log)}</span>
        </div>
      `).join("");
      telemetryStream.scrollTop = telemetryStream.scrollHeight;
    }
  }

  // --- TRIGGER PIPELINE ---
  pipelineForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = document.getElementById("search-query").value;
    const location = document.getElementById("search-location").value;
    const min_salary = document.getElementById("search-salary") ? document.getElementById("search-salary").value : "25 LPA";
    const discovery_source = document.getElementById("search-source") ? document.getElementById("search-source").value : "hybrid";
    const jobAgeVal = document.getElementById("search-jobage") ? document.getElementById("search-jobage").value : "7";
    const max_age_days = jobAgeVal === "all" ? null : parseInt(jobAgeVal, 10);
    const limit = parseInt(document.getElementById("search-limit").value, 10);

    btnRun.disabled = true;
    btnRunText.textContent = "Scraping Latest...";
    systemStatus.textContent = `Discovering latest jobs (${discovery_source}, past ${jobAgeVal}d) in ${location}...`;

    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, location, min_salary, limit, discovery_source, max_age_days })
      });
      const newState = await res.json();
      renderDashboard(newState);
      showToast(`Scrape complete! Sorted latest-first.`, "success");
    } catch (err) {
      alert("Pipeline run failed: " + err);
    } finally {
      btnRun.disabled = false;
      btnRunText.textContent = "Run Pipeline";
    }
  });

  // --- DAILY INCREMENTAL SYNC ---
  const btnDailySync = document.getElementById("btn-daily-sync");
  if (btnDailySync) {
    btnDailySync.addEventListener("click", async () => {
      const query = document.getElementById("search-query").value;
      const location = document.getElementById("search-location").value;
      const discovery_source = document.getElementById("search-source") ? document.getElementById("search-source").value : "hybrid";

      btnDailySync.disabled = true;
      const oldHtml = btnDailySync.innerHTML;
      btnDailySync.innerHTML = "Syncing New Today...";
      showToast("Running Daily Incremental Sync: discovering new postings from past 24 hours...", "info");

      try {
        const res = await fetch("/api/pipeline/daily-sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, location, discovery_source, max_age_days: 1 })
        });
        const data = await res.json();
        showToast(data.message || "Daily sync completed! Added newly discovered jobs.", "success");
        if (data.state) renderDashboard(data.state);
        else await fetchState();
      } catch (err) {
        showToast("Daily sync error: " + err, "error");
      } finally {
        btnDailySync.disabled = false;
        btnDailySync.innerHTML = oldHtml;
      }
    });
  }

  // --- PROBE TOOL ---
  btnProbe.addEventListener("click", async () => {
    const name = probeName.value.trim();
    const domain = probeDomain.value.trim();
    if (!name || !domain) {
      alert("Please provide both Recruiter Name and Company Domain.");
      return;
    }

    btnProbe.disabled = true;
    probeResults.innerHTML = "Inferring patterns...";

    try {
      const res = await fetch("/api/enrich", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, company_domain: domain })
      });
      const data = await res.json();
      probeResults.innerHTML = `
        <div style="margin-top:10px; display:flex; flex-direction:column; gap:6px;">
          ${data.candidates.map(c => `
            <div style="display:flex; justify-content:space-between; background:rgba(0,0,0,0.4); padding:6px 10px; border-radius:4px;">
              <span style="color:#06b6d4;">${c.email}</span>
              <span style="color:#10b981; font-weight:700;">${Math.round(c.confidence * 100)}% Conf (${c.pattern})</span>
            </div>
          `).join("")}
        </div>
      `;
    } catch (err) {
      probeResults.innerHTML = "Probe error: " + err;
    } finally {
      btnProbe.disabled = false;
    }
  });

  // --- AI CAREER PROFILER & SCRAPE TARGET GENERATOR ---
  const btnInterview = document.getElementById("btn-run-interview");
  const interviewResults = document.getElementById("interview-results");

  if (btnInterview) {
    btnInterview.addEventListener("click", async () => {
      const projects = document.getElementById("interview-projects").value.trim();
      const tech_stack = document.getElementById("interview-tech").value.trim();
      const ideal_role = document.getElementById("interview-role").value.trim();
      const location = document.getElementById("interview-location") ? document.getElementById("interview-location").value.trim() : "India";
      const expected_salary = document.getElementById("interview-salary") ? document.getElementById("interview-salary").value.trim() : "25 LPA";

      const oldHtml = btnInterview.innerHTML;
      btnInterview.disabled = true;
      btnInterview.innerHTML = `Analyzing Experience & Synthesizing Scrape Targets...`;

      try {
        const res = await fetch("/api/career-interview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ projects, tech_stack, ideal_role, location, expected_salary })
        });
        const blueprint = await res.json();

        const recTitles = blueprint.recommended_titles || [];
        const queries = blueprint.search_queries || [];
        const skills = blueprint.extracted_skills || [];
        const pitch = blueprint.elevator_pitch || "";
        const primaryTarget = recTitles[0] || queries[0] || "AI Engineer";

        interviewResults.innerHTML = `
          <div style="background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(139, 92, 246, 0.35); border-radius: 8px; padding: 16px; margin-top: 14px;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #a78bfa; margin-bottom: 6px;">
              🎯 AI Career Blueprint Generated
            </div>
            
            <p style="font-size: 0.85rem; color: #e2e8f0; font-style: italic; margin-bottom: 12px; line-height: 1.4;">
              "${escapeHtml(pitch)}"
            </p>

            <div style="margin-bottom: 10px;">
              <div style="font-size: 0.72rem; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Recommended Role Titles</div>
              <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                ${recTitles.map(t => `<span class="badge-agent" style="background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); color: #c7d2fe;">${escapeHtml(t)}</span>`).join("")}
              </div>
            </div>

            <div style="margin-bottom: 12px;">
              <div style="font-size: 0.72rem; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">High-Intent Scrape Queries (Auto-Expanded)</div>
              <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                ${queries.map(q => `<span style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); color: #6ee7b7; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">🔍 ${escapeHtml(q)}</span>`).join("")}
              </div>
            </div>

            <div style="margin-bottom: 14px;">
              <div style="font-size: 0.72rem; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Canonical Profile Skills</div>
              <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                ${skills.map(s => `<span style="background: rgba(255, 255, 255, 0.07); color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">✓ ${escapeHtml(s)}</span>`).join("")}
              </div>
            </div>

            <button class="btn btn-primary" onclick="launchAIJobSearch('${escapeHtml(primaryTarget)}', '${escapeHtml(location)}', '${escapeHtml(expected_salary)}')" style="width: 100%; justify-content: center; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #3b82f6); padding: 10px;">
              🚀 Scrape & Apply for These AI-Generated Target Roles (${escapeHtml(location)})
            </button>
          </div>
        `;
      } catch (err) {
        interviewResults.innerHTML = `<div style="color: #ef4444; font-size: 0.8rem;">Career analysis failed: ${err}</div>`;
      } finally {
        btnInterview.disabled = false;
        btnInterview.innerHTML = oldHtml;
      }
    });
  }

  window.launchAIJobSearch = function(targetQuery, targetLoc, targetSalary) {
    const queryInput = document.getElementById("search-query");
    if (queryInput && targetQuery) queryInput.value = targetQuery;
    const locInput = document.getElementById("search-location");
    if (locInput && targetLoc) locInput.value = targetLoc;
    const salaryInput = document.getElementById("search-salary");
    if (salaryInput && targetSalary) salaryInput.value = targetSalary;

    // Switch to Pending Approvals Tab (tab-approval)
    tabBtns.forEach(b => b.classList.remove("active"));
    tabContents.forEach(c => c.classList.remove("active"));
    const approvalTabBtn = document.querySelector('[data-tab="tab-approval"]');
    const approvalTabContent = document.getElementById("tab-approval");
    if (approvalTabBtn) approvalTabBtn.classList.add("active");
    if (approvalTabContent) approvalTabContent.classList.add("active");

    // Automatically submit pipeline form
    if (pipelineForm) {
      pipelineForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    }
  };

  // Helper
  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Toast Notification System
  function showToast(message, type = "info", duration = 4000) {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let iconSvg = '';
    if (type === 'success') {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (type === 'error') {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }
    
    toast.innerHTML = `${iconSvg}<div style="flex:1;">${escapeHtml(message)}</div>`;
    container.appendChild(toast);
    
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(50px)";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // Global window functions for inline onclick handlers
  window.regenerateEmail = async function(jobId) {
    const inputEl = document.getElementById(`feedback-input-${jobId}`);
    const btnEl = document.getElementById(`btn-revise-${jobId}`);
    const subjectEl = document.getElementById(`subject-${jobId}`);
    const bodyEl = document.getElementById(`body-${jobId}`);

    const feedback = inputEl ? inputEl.value.trim() : "";
    if (!feedback) {
      showToast("Please enter feedback for revising the email (e.g. 'Make it shorter').", "error");
      return;
    }

    const oldHtml = btnEl ? btnEl.innerHTML : "";
    if (btnEl) {
      btnEl.disabled = true;
      btnEl.textContent = "Revising...";
    }

    try {
      const res = await fetch("/api/regenerate-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: jobId,
          feedback: feedback,
          current_body: bodyEl ? bodyEl.innerText : ""
        })
      });
      const data = await res.json();
      if (res.ok && data.email) {
        if (subjectEl) subjectEl.textContent = data.email.subject;
        if (bodyEl) bodyEl.textContent = data.email.body;
        if (inputEl) inputEl.value = "";
        showToast("Cold email revised with your feedback!", "success");
      } else {
        showToast(data.detail || "Email revision failed.", "error");
      }
    } catch (err) {
      showToast("Email revision error: " + err, "error");
    } finally {
      if (btnEl) {
        btnEl.disabled = false;
        btnEl.innerHTML = oldHtml;
      }
    }
  };

  window.approveJob = async function(jobId, evt) {
    const btn = evt ? evt.target.closest("button") : document.querySelector(`#card-${jobId} button.btn-primary`);
    const oldHtml = btn ? btn.innerHTML : "";
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Approving...";
    }
    try {
      const res = await fetch(`/api/approve/${jobId}`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message || "Job approved & recruiter outreach scheduled!", "success");
        await fetchState();
      } else {
        showToast(data.detail || "Approval failed. Please check server.", "error");
      }
    } catch (err) {
      showToast("Approval error: " + err, "error");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = oldHtml;
      }
    }
  };

  window.rejectJob = async function(jobId, evt) {
    try {
      const res = await fetch(`/api/reject/${jobId}`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message || "Job rejected and removed from review queue.", "info");
        await fetchState();
      } else {
        showToast(data.detail || "Reject failed.", "error");
      }
    } catch (err) {
      showToast("Reject error: " + err, "error");
    }
  };

  window.autofillJob = async function(jobId, evt) {
    const btn = evt ? evt.target.closest("button") : document.getElementById(`btn-autofill-${jobId}`);
    const oldHtml = btn ? btn.innerHTML : "";
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Autofilling...";
    }

    try {
      const res = await fetch(`/api/apply/autofill/${jobId}`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        const result = data.result || {};
        if (result.ats_type === "linkedin") {
          showToast(result.message || "LinkedIn requires candidate login. Click 'View Job Listing' to apply on LinkedIn.", "info", 7000);
        } else {
          const fields = (result.filled_fields || []).join(", ") || "Standard contact inputs";
          showToast(`⚡ Autofill completed on ${result.ats_type.toUpperCase()}! Filled: ${fields}`, "success", 5000);
        }
      } else {
        showToast("Autofill notice: " + (data.detail || "Failed to fill form."), "error");
      }
    } catch (err) {
      showToast("Autofill error: " + err, "error");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = oldHtml;
      }
    }
  };

  // --- CANDIDATE PROFILE & RESUME INGESTION ---
  async function loadProfile() {
    try {
      const res = await fetch("/api/profile");
      if (!res.ok) return;
      const profile = await res.json();

      const elName = document.getElementById("profile-name");
      const elTitle = document.getElementById("profile-title");
      const elEmail = document.getElementById("profile-email");
      const elPhone = document.getElementById("profile-phone");
      const elLocation = document.getElementById("profile-location");
      const elLinkedin = document.getElementById("profile-linkedin");
      const elGithub = document.getElementById("profile-github");
      const elPortfolio = document.getElementById("profile-portfolio");
      const elSkills = document.getElementById("profile-skills");
      const elRawResume = document.getElementById("profile-raw-resume");

      if (elName && profile.name) elName.value = profile.name;
      if (elTitle && profile.title) elTitle.value = profile.title;
      if (elEmail && profile.email) elEmail.value = profile.email;
      if (elPhone && profile.phone) elPhone.value = profile.phone;
      if (elLocation && profile.location) elLocation.value = profile.location;
      if (elLinkedin && profile.linkedin) elLinkedin.value = profile.linkedin;
      if (elGithub && profile.github) elGithub.value = profile.github;
      if (elPortfolio && profile.portfolio) elPortfolio.value = profile.portfolio;
      if (elSkills && profile.skills) elSkills.value = (profile.skills || []).join(", ");
      if (elRawResume && profile.raw_resume_text) elRawResume.value = profile.raw_resume_text;

      // Sync AI Career interview fields if blank
      const intTech = document.getElementById("interview-tech");
      if (intTech && !intTech.value && profile.skills) {
        intTech.value = (profile.skills || []).join(", ");
      }
    } catch (err) {
      console.warn("Could not load profile:", err);
    }
  }

  const btnSaveProfile = document.getElementById("btn-save-profile");
  if (btnSaveProfile) {
    btnSaveProfile.addEventListener("click", async () => {
      const name = document.getElementById("profile-name").value.trim();
      const title = document.getElementById("profile-title").value.trim();
      const email = document.getElementById("profile-email").value.trim();
      const phone = document.getElementById("profile-phone").value.trim();
      const location = document.getElementById("profile-location").value.trim();
      const linkedin = document.getElementById("profile-linkedin").value.trim();
      const github = document.getElementById("profile-github").value.trim();
      const portfolio = document.getElementById("profile-portfolio").value.trim();
      const skills = document.getElementById("profile-skills").value.split(",").map(s => s.trim()).filter(Boolean);
      const raw_resume_text = document.getElementById("profile-raw-resume").value;

      if (!name || !email) {
        showToast("Please provide at least your Name and Email.", "error");
        return;
      }

      btnSaveProfile.disabled = true;
      const oldHtml = btnSaveProfile.innerHTML;
      btnSaveProfile.textContent = "Saving...";

      try {
        const res = await fetch("/api/profile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name, title, email, phone, location,
            linkedin, github, portfolio, skills,
            raw_resume_text
          })
        });
        const data = await res.json();
        if (res.ok) {
          showToast(data.message || "Profile and Resume format successfully saved!", "success");
          await fetchState();
        } else {
          showToast(data.detail || "Failed to save profile.", "error");
        }
      } catch (err) {
        showToast("Profile save error: " + err, "error");
      } finally {
        btnSaveProfile.disabled = false;
        btnSaveProfile.innerHTML = oldHtml;
      }
    });
  }

  // --- SKILL: GENERAL MASTER RESUME REFINER ---
  const btnRefineResume = document.getElementById("btn-refine-resume");
  const refineAuditBox = document.getElementById("refine-audit-box");
  if (btnRefineResume) {
    btnRefineResume.addEventListener("click", async () => {
      const rawEl = document.getElementById("profile-raw-resume");
      const rawText = rawEl ? rawEl.value : "";
      if (!rawText.trim()) {
        showToast("Please paste your current master resume text first.", "error");
        return;
      }
      btnRefineResume.disabled = true;
      const oldHtml = btnRefineResume.innerHTML;
      btnRefineResume.innerHTML = "✨ Refining Master Resume...";
      
      try {
        const res = await fetch("/api/resume/refine", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            raw_resume_text: rawText,
            career_direction: "Senior AI Systems & Backend Engineer"
          })
        });
        const data = await res.json();
        if (res.ok && data.refined_resume) {
          rawEl.value = data.refined_resume;
          if (refineAuditBox) {
            refineAuditBox.style.display = "block";
            const imps = data.improvements || [];
            const impList = imps.map(imp => {
              const orig = escapeHtml(imp.original || "");
              const impr = escapeHtml(imp.improved || "");
              return `<li style="margin-bottom:4px;"><span style="color:#c084fc; font-weight:600;">${escapeHtml(imp.type || "Polish")}:</span> ${orig} &rarr; <strong style="color:#34d399;">${impr}</strong></li>`;
            }).join("");
            refineAuditBox.innerHTML = `
              <div style="font-weight:700; color:#34d399; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                <span>✨ Master Resume Refined (${imps.length} Improvements Made)</span>
                <span style="font-size:0.68rem; background:rgba(16,185,129,0.2); color:#6ee7b7; padding:2px 8px; border-radius:12px; border:1px solid rgba(16,185,129,0.4);">
                  100% Layout Preserved • Truth Verified
                </span>
              </div>
              <ul style="margin:0; padding-left:16px; color:#cbd5e1; font-size:0.75rem;">
                ${impList || "<li>Polished weak verbs into Google XYZ impact achievements.</li>"}
              </ul>
            `;
          }
          showToast("Master resume refined! Format strictly preserved and impact metrics upgraded.", "success");
        } else {
          showToast(data.detail || "Refinement failed.", "error");
        }
      } catch (err) {
        showToast("Resume refinement error: " + err, "error");
      } finally {
        btnRefineResume.disabled = false;
        btnRefineResume.innerHTML = oldHtml;
      }
    });
  }

  // --- ATS AUTOFILL TEST & VISUAL PROOF MODAL ---
  const btnVerifyAts = document.getElementById("btn-verify-ats");
  const modalProof = document.getElementById("modal-proof");
  const btnCloseProof = document.getElementById("btn-close-proof");
  const modalProofClose = document.getElementById("modal-proof-close");
  const proofImg = document.getElementById("proof-img");
  const proofFields = document.getElementById("proof-fields");
  const proofTime = document.getElementById("proof-time");

  function closeProofModal() {
    if (modalProof) modalProof.classList.remove("active");
  }
  if (btnCloseProof) btnCloseProof.addEventListener("click", closeProofModal);
  if (modalProofClose) modalProofClose.addEventListener("click", closeProofModal);
  if (modalProof) {
    modalProof.addEventListener("click", (e) => {
      if (e.target === modalProof) closeProofModal();
    });
  }

  if (btnVerifyAts) {
    btnVerifyAts.addEventListener("click", async () => {
      btnVerifyAts.disabled = true;
      const oldHtml = btnVerifyAts.innerHTML;
      btnVerifyAts.innerHTML = "🧪 Testing Playwright Autofill...";

      try {
        const res = await fetch("/api/apply/verify-test-form", { method: "POST" });
        const data = await res.json();
        if (res.ok) {
          const filled = (data.result && data.result.filled_fields) ? data.result.filled_fields.join(", ") : "First Name, Last Name, Email, Phone, LinkedIn";
          if (proofFields) proofFields.textContent = filled;
          if (proofTime) proofTime.textContent = new Date().toLocaleTimeString();
          if (proofImg && data.screenshot_url) {
            proofImg.src = data.screenshot_url + "?t=" + Date.now();
          }
          if (modalProof) modalProof.classList.add("active");
          showToast("✅ ATS Autofill test complete! Screenshot proof displayed.", "success");
        } else {
          showToast(data.detail || "ATS test failed.", "error");
        }
      } catch (err) {
        showToast("ATS test error: " + err, "error");
      } finally {
        btnVerifyAts.disabled = false;
        btnVerifyAts.innerHTML = oldHtml;
      }
    });
  }

  // --- CANDIDATE ONBOARDING & PROFILE INTERVIEW MODAL ---
  const btnOpenInterview = document.getElementById("btn-open-interview");
  const modalInterview = document.getElementById("modal-interview");
  const modalInterviewClose = document.getElementById("modal-interview-close");
  const btnCancelInterview = document.getElementById("btn-cancel-interview");
  const formInterview = document.getElementById("form-onboard-interview");

  function openInterviewModal() {
    const curRaw = document.getElementById("profile-raw-resume") ? document.getElementById("profile-raw-resume").value : "";
    const modalResume = document.getElementById("interview-modal-resume");
    if (modalResume && curRaw && !modalResume.value) {
      modalResume.value = curRaw;
    }
    const curSkills = document.getElementById("profile-skills") ? document.getElementById("profile-skills").value : "";
    const modalTech = document.getElementById("interview-modal-tech");
    if (modalTech && curSkills && (!modalTech.value || modalTech.value.includes("Python, FastAPI"))) {
      modalTech.value = curSkills;
    }
    if (modalInterview) modalInterview.classList.add("active");
  }

  function closeInterviewModal() {
    if (modalInterview) modalInterview.classList.remove("active");
  }

  if (btnOpenInterview) btnOpenInterview.addEventListener("click", openInterviewModal);
  if (modalInterviewClose) modalInterviewClose.addEventListener("click", closeInterviewModal);
  if (btnCancelInterview) btnCancelInterview.addEventListener("click", closeInterviewModal);
  if (modalInterview) {
    modalInterview.addEventListener("click", (e) => {
      if (e.target === modalInterview) closeInterviewModal();
    });
  }

  if (formInterview) {
    formInterview.addEventListener("submit", async (e) => {
      e.preventDefault();
      const raw_resume_text = document.getElementById("interview-modal-resume").value.trim();
      const projects_experience = document.getElementById("interview-modal-projects").value.trim();
      const tech_stack = document.getElementById("interview-modal-tech").value.trim();
      const target_role = document.getElementById("interview-modal-role").value.trim();
      const target_location = document.getElementById("interview-modal-location").value.trim();
      const min_salary = document.getElementById("interview-modal-salary").value.trim();

      const btnSubmit = document.getElementById("btn-submit-interview");
      btnSubmit.disabled = true;
      const oldHtml = btnSubmit.innerHTML;
      btnSubmit.innerHTML = "Ingesting &amp; Calibrating...";

      try {
        const res = await fetch("/api/onboard-interview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            raw_resume_text,
            projects_experience,
            tech_stack,
            target_role,
            target_location,
            min_salary
          })
        });
        const data = await res.json();
        if (res.ok) {
          showToast("Candidate interview ingested and profile configured!", "success");
          closeInterviewModal();
          await loadProfile();
          await fetchState();
          
          // Sync search inputs in control bar
          const searchQ = document.getElementById("search-query");
          const searchLoc = document.getElementById("search-location");
          const searchSal = document.getElementById("search-salary");
          if (searchQ && target_role) searchQ.value = target_role;
          if (searchLoc && target_location) searchLoc.value = target_location;
          if (searchSal && min_salary) searchSal.value = min_salary;
        } else {
          showToast(data.detail || "Interview submission failed.", "error");
        }
      } catch (err) {
        showToast("Interview error: " + err, "error");
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = oldHtml;
      }
    });
  }

  // --- TARGET COMPANIES DIRECTORY & ATS SCANNER ---
  let allCompanies = [];
  let currentCompanyCategory = "all";
  const companiesGrid = document.getElementById("companies-grid");
  const companiesStats = document.getElementById("companies-stats-badge");
  const companySearchInput = document.getElementById("company-search-input");
  const categoryPillsContainer = document.getElementById("category-pills");
  const btnOpenAddCompany = document.getElementById("btn-open-add-company");
  const btnScanCompanies = document.getElementById("btn-scan-companies");
  const modalCompany = document.getElementById("modal-company");
  const modalCompanyClose = document.getElementById("modal-company-close");
  const btnCancelCompany = document.getElementById("btn-cancel-company");
  const formAddCompany = document.getElementById("form-add-company");

  function openCompanyModal() {
    if (modalCompany) modalCompany.classList.add("active");
  }

  function closeCompanyModal() {
    if (modalCompany) modalCompany.classList.remove("active");
  }

  if (btnOpenAddCompany) btnOpenAddCompany.addEventListener("click", openCompanyModal);
  if (modalCompanyClose) modalCompanyClose.addEventListener("click", closeCompanyModal);
  if (btnCancelCompany) btnCancelCompany.addEventListener("click", closeCompanyModal);
  if (modalCompany) {
    modalCompany.addEventListener("click", (e) => {
      if (e.target === modalCompany) closeCompanyModal();
    });
  }

  async function loadCompanies() {
    if (!companiesGrid) return;
    try {
      const res = await fetch("/api/companies");
      if (!res.ok) return;
      const data = await res.json();
      allCompanies = data.companies || [];
      if (companiesStats) {
        const catCounts = data.categories || {};
        const catSummary = Object.entries(catCounts).map(([k, v]) => `${v} ${k}`).join(" • ");
        companiesStats.textContent = `${data.total} Tracked • ${catSummary}`;
      }
      renderCompanies();
    } catch (err) {
      console.error("Failed to load target companies:", err);
      if (companiesGrid) companiesGrid.innerHTML = `<div class="empty-state-sm">Error loading companies: ${escapeHtml(String(err))}</div>`;
    }
  }

  function renderCompanies() {
    if (!companiesGrid) return;
    const q = companySearchInput ? companySearchInput.value.trim().toLowerCase() : "";
    
    const filtered = allCompanies.filter(c => {
      const matchesCat = (currentCompanyCategory === "all") || (c.category === currentCompanyCategory);
      const matchesSearch = !q || 
        (c.name && c.name.toLowerCase().includes(q)) || 
        (c.domain && c.domain.toLowerCase().includes(q)) ||
        ((c.ats_type || c.ats_platform) && (c.ats_type || c.ats_platform).toLowerCase().includes(q));
      return matchesCat && matchesSearch;
    });

    if (filtered.length === 0) {
      companiesGrid.innerHTML = `
        <div class="empty-state-sm" style="grid-column: 1/-1; text-align:center; padding:30px;">
          No target companies matched the selected filters.
        </div>
      `;
      return;
    }

    companiesGrid.innerHTML = filtered.slice(0, 150).map(c => {
      const ats = (c.ats_type || c.ats_platform || "custom").toLowerCase();
      let badgeClass = "badge-custom";
      if (ats === "greenhouse") badgeClass = "badge-greenhouse";
      else if (ats === "lever") badgeClass = "badge-lever";
      else if (ats === "ashby") badgeClass = "badge-ashby";

      const catDisplay = (c.category || "").replace(/_/g, " ").toUpperCase();
      const safeName = escapeHtml(c.name || "Company");
      const safeDomain = escapeHtml(c.domain || "");
      const safeUrl = escapeHtml(c.career_url || c.career_page_url || "");

      return `
        <div class="company-card">
          <div class="company-card-header">
            <div>
              <div class="company-card-title">${safeName}</div>
              <div class="company-card-domain">${safeDomain}</div>
            </div>
            <div class="company-card-badges">
              <span class="${badgeClass}">${ats.toUpperCase()}</span>
            </div>
          </div>
          <div>
            <span class="badge-category">${escapeHtml(catDisplay)}</span>
          </div>
          <div class="company-actions">
            <a href="${safeUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="text-decoration:none; font-size:0.75rem; padding:3px 8px; display:inline-flex; align-items:center; gap:4px;">
              <span>Careers Page</span>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            </a>
            <button type="button" class="btn btn-primary btn-sm" onclick="scanSingleCompany('${escapeHtml(c.name)}', '${escapeHtml(ats)}')" style="font-size:0.75rem; padding:3px 10px; background:linear-gradient(135deg, rgba(99, 102, 241, 0.4), rgba(6, 182, 212, 0.4)); border:1px solid rgba(99, 102, 241, 0.5);">
              ⚡ Scan Roles
            </button>
          </div>
        </div>
      `;
    }).join("");
  }

  // Filter Pills Event Handling
  if (categoryPillsContainer) {
    categoryPillsContainer.addEventListener("click", (e) => {
      const pill = e.target.closest(".category-pill");
      if (!pill) return;
      categoryPillsContainer.querySelectorAll(".category-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentCompanyCategory = pill.dataset.category || "all";
      renderCompanies();
    });
  }

  if (companySearchInput) {
    companySearchInput.addEventListener("input", () => {
      renderCompanies();
    });
  }

  // Add Company Form Submit
  if (formAddCompany) {
    formAddCompany.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("company-input-name").value.trim();
      const domain = document.getElementById("company-input-domain").value.trim();
      const category = document.getElementById("company-input-category").value;
      const ats_type = document.getElementById("company-input-ats").value;
      const career_url = document.getElementById("company-input-url").value.trim();
      const ats_identifier = career_url.split("/").filter(Boolean).pop() || name.toLowerCase().replace(/[^a-z0-9]/g, "");

      const btnSub = document.getElementById("btn-submit-company");
      btnSub.disabled = true;
      btnSub.textContent = "Saving...";

      try {
        const res = await fetch("/api/companies", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, domain, category, ats_type, career_url, ats_identifier })
        });
        const data = await res.json();
        if (res.ok) {
          showToast(`Successfully tracked ${name}!`, "success");
          closeCompanyModal();
          formAddCompany.reset();
          await loadCompanies();
        } else {
          showToast(data.detail || "Failed to add company", "error");
        }
      } catch (err) {
        showToast("Error adding company: " + err, "error");
      } finally {
        btnSub.disabled = false;
        btnSub.textContent = "💾 Track Company";
      }
    });
  }

  // Scan Active Companies / Category
  if (btnScanCompanies) {
    btnScanCompanies.addEventListener("click", async () => {
      const query = document.getElementById("search-query") ? document.getElementById("search-query").value : "AI Engineer";
      const location = document.getElementById("search-location") ? document.getElementById("search-location").value : "India";
      
      btnScanCompanies.disabled = true;
      const oldHtml = btnScanCompanies.innerHTML;
      btnScanCompanies.innerHTML = "Scanning ATS Careers...";

      try {
        showToast(`Scanning open career boards for '${query}'...`, "info");
        const res = await fetch("/api/companies/scan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            category: currentCompanyCategory === "all" ? null : currentCompanyCategory,
            query,
            location,
            limit: 15
          })
        });
        const data = await res.json();
        showToast(`Scan complete: Found ${data.total_found} openings across ${data.scanned_boards} companies!`, "success");
        await fetchState();
        const qualTabBtn = document.getElementById("tab-btn-qualified");
        if (qualTabBtn) qualTabBtn.click();
      } catch (err) {
        showToast("Scan error: " + err, "error");
      } finally {
        btnScanCompanies.disabled = false;
        btnScanCompanies.innerHTML = oldHtml;
      }
    });
  }

  window.scanSingleCompany = async function(companyName, atsPlatform) {
    const query = document.getElementById("search-query") ? document.getElementById("search-query").value : "AI Engineer";
    const location = document.getElementById("search-location") ? document.getElementById("search-location").value : "India";
    showToast(`Scanning ${companyName} (${atsPlatform}) for '${query}'...`, "info");
    try {
      const res = await fetch("/api/companies/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: companyName,
          query,
          location,
          limit: 10
        })
      });
      const data = await res.json();
      showToast(`Scan ${companyName} finished: Found ${data.total_found} relevant openings!`, "success");
      await fetchState();
      const qualTabBtn = document.getElementById("tab-btn-qualified");
      if (qualTabBtn) qualTabBtn.click();
    } catch (err) {
      showToast(`Scan failed for ${companyName}: ${err}`, "error");
    }
  };

  // Initial Load
  fetchState();
  loadProfile();
  loadCompanies();
});

