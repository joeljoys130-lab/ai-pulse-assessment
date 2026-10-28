import React, { useEffect, useState } from "react";
import { api } from "../api.js";

function badgeClass(level) {
  switch (level) {
    case "Leader":
      return "badge badge-leader";
    case "Practitioner":
      return "badge badge-practitioner";
    case "Exploring":
      return "badge badge-exploring";
    case "Beginner":
      return "badge badge-beginner";
    default:
      return "badge badge-na";
  }
}

function formatRisk(key) {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function Report({ onRetake }) {
  const [report, setReport] = useState(null);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [togglingAction, setTogglingAction] = useState("");

  function loadData() {
    setLoading(true);
    setError("");
    Promise.all([api("/reports/me"), api("/reports/actions")])
      .then(([rep, act]) => {
        setReport(rep);
        setActions(act);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load report data");
        setLoading(false);
      });
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleToggleAction(actionId) {
    setTogglingAction(actionId);
    try {
      const res = await api(`/reports/actions/${actionId}/toggle`, { method: "POST" });
      setActions((prev) =>
        prev.map((a) => (a.id === actionId ? { ...a, completed: res.completed } : a))
      );
    } catch (err) {
      setError(err.message || "Failed to update action");
    } finally {
      setTogglingAction("");
    }
  }

  async function handleDelete() {
    const confirmed = window.confirm(
      "Are you sure you want to delete all your diagnostic answers, actions, and report data? This action will immediately remove your data from company dashboards."
    );
    if (!confirmed) return;

    setDeleting(true);
    setStatusMessage("");
    setError("");
    try {
      const res = await api("/reports/me", { method: "DELETE" });
      setStatusMessage(res.message || "Your diagnostic data has been deleted.");
      await loadData();
    } catch (err) {
      setError(err.message || "Failed to delete diagnostic data");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) return <div className="card"><p>Loading report…</p></div>;
  if (error) return <div className="card"><p className="error">{error}</p><button onClick={loadData}>Retry</button></div>;
  if (!report) return null;

  return (
    <div className="card">
      <div className="flex-between">
        <h2>{report.name} — Personal AI Report</h2>
        <span className={badgeClass(report.level)}>{report.level}</span>
      </div>

      <p style={{ color: "#475569" }}>
        <strong>Organization:</strong> {report.organization} | <strong>Questions Answered:</strong> {report.answered}
      </p>

      {statusMessage && <div className="success">{statusMessage}</div>}

      {report.answered === 0 ? (
        <div>
          <p>You have no submitted answers on record, or your data has been deleted.</p>
          {onRetake && <button onClick={onRetake}>Take Diagnostic</button>}
        </div>
      ) : (
        <>
          <p>
            <strong>Average Score:</strong> {report.average_score !== null ? `${report.average_score} / 5.0` : "Not assessed"}
          </p>

          <h3>Identified Risks</h3>
          {report.risks && report.risks.length > 0 ? (
            <ul>
              {report.risks.map((r) => (
                <li key={r}>
                  <strong>{formatRisk(r)}</strong>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ color: "#64748b" }}>No AI risks identified in your responses.</p>
          )}

          {/* Diagnostic Action Planner Feature */}
          <h3>Personalized Diagnostic Action Plan</h3>
          <p style={{ fontSize: "0.9rem", color: "#64748b", marginTop: "-6px" }}>
            Prioritized actions derived deterministically from your diagnostic results and skill gaps.
          </p>

          {actions.length > 0 ? (
            actions.map((act) => (
              <div key={act.id} className={`action-card ${act.completed ? "done" : ""}`}>
                <div className="action-header">
                  <div>
                    <div className="action-title">{act.title}</div>
                    <div className="action-exp">{act.explanation}</div>
                  </div>
                  <button
                    className={act.completed ? "secondary" : ""}
                    onClick={() => handleToggleAction(act.id)}
                    disabled={togglingAction === act.id}
                    style={{ whiteSpace: "nowrap", minWidth: "120px" }}
                  >
                    {togglingAction === act.id
                      ? "Updating…"
                      : act.completed
                      ? "✓ Completed"
                      : "Mark Done"}
                  </button>
                </div>
                <div className="action-step">
                  <strong>Recommended Next Step:</strong> {act.next_step}
                </div>
              </div>
            ))
          ) : (
            <p style={{ color: "#64748b" }}>Complete the diagnostic to receive your personalized action plan.</p>
          )}

          <hr style={{ margin: "24px 0", border: "0", borderTop: "1px solid #e2e8f0" }} />

          <div>
            <h4>Data Privacy & Control</h4>
            <p style={{ fontSize: "0.9rem", color: "#64748b" }}>
              Under our privacy policy, you have the right to delete all your diagnostic answers, action records, and report data at any time. Your results will disappear from company dashboards immediately.
            </p>
            <button className="danger" onClick={handleDelete} disabled={deleting}>
              {deleting ? "Deleting…" : "Delete My Diagnostic Data"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
