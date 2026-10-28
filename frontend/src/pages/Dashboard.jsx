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

export default function Dashboard({ org }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function loadDashboard() {
    setLoading(true);
    setError("");
    api(`/dashboard?org_id=${org.org_id}`)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load dashboard");
        setLoading(false);
      });
  }

  useEffect(() => {
    loadDashboard();
  }, [org]);

  if (loading) return <div className="card"><p>Loading dashboard…</p></div>;
  if (error) return <div className="card"><p className="error">{error}</p><button onClick={loadDashboard}>Retry</button></div>;
  if (!data) return null;

  return (
    <div className="card">
      <div className="flex-between">
        <h2>{data.organization} — AI Maturity Dashboard</h2>
        <button className="secondary" onClick={loadDashboard}>Refresh</button>
      </div>

      <div className="notice">
        <strong>Privacy Threshold:</strong> Departments with fewer than 5 completed diagnostics are automatically aggregated under "Other teams" to prevent individual employee identification.
      </div>

      <h3>Department Overview</h3>
      <table>
        <thead>
          <tr>
            <th>Department</th>
            <th>Employees</th>
            <th>Responded</th>
            <th>Avg Score</th>
            <th>Maturity Level</th>
          </tr>
        </thead>
        <tbody>
          {data.departments.map((d) => (
            <tr key={d.department}>
              <td>
                <strong>{d.department}</strong>
                {d.department === "Other teams" && (
                  <span style={{ fontSize: "0.8rem", color: "#64748b", display: "block" }}>
                    Combined small teams (&lt; 5 respondents)
                  </span>
                )}
              </td>
              <td>{d.employees}</td>
              <td>{d.responded}</td>
              <td>{d.average_score !== null ? d.average_score : "—"}</td>
              <td>
                <span className={badgeClass(d.level)}>{d.level}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Top Company Risks</h3>
      {data.top_risks.length > 0 ? (
        <ul>
          {data.top_risks.map(([risk, count]) => (
            <li key={risk}>
              <strong>{formatRisk(risk)}:</strong> flagged {count} {count === 1 ? "time" : "times"}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ color: "#64748b" }}>
          No risks surfaced. (Company-level risks are suppressed when fewer than 5 employees have completed the diagnostic).
        </p>
      )}
    </div>
  );
}
