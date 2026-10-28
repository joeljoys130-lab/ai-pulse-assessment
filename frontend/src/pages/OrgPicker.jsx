import React, { useState } from "react";
import { api, setToken, setStoredOrg } from "../api.js";

export default function OrgPicker({ orgs, onPick }) {
  const [selecting, setSelecting] = useState(null);
  const [error, setError] = useState("");

  async function pick(o) {
    setSelecting(o.org_id);
    setError("");
    try {
      const data = await api("/auth/select-org", { method: "POST", body: JSON.stringify({ org_id: o.org_id }) });
      setToken(data.token);
      setStoredOrg(o);
      await onPick(o);
    } catch (err) {
      setError(err.message || "Failed to select organization");
    } finally {
      setSelecting(null);
    }
  }

  return (
    <div className="card">
      <h2>Choose an organization</h2>
      {error && <p className="error">{error}</p>}
      {orgs.map((o) => (
        <p key={o.org_id}>
          <button disabled={selecting !== null} onClick={() => pick(o)}>
            {selecting === o.org_id ? "Selecting…" : o.org_name}
          </button>{" "}
          <small>({o.role})</small>
        </p>
      ))}
    </div>
  );
}
