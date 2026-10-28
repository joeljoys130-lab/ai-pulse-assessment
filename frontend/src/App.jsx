import React, { useEffect, useState } from "react";
import Login from "./pages/Login.jsx";
import OrgPicker from "./pages/OrgPicker.jsx";
import Diagnostic from "./pages/Diagnostic.jsx";
import Report from "./pages/Report.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import {
  api,
  getToken,
  clearAuth,
  getStoredSession,
  getStoredOrg,
  setStoredOrg,
} from "./api.js";

export default function App() {
  const [step, setStep] = useState("loading");
  const [session, setSession] = useState(null);
  const [org, setOrg] = useState(null);
  const [authError, setAuthError] = useState("");

  // Rehydrate authenticated session from localStorage on startup / page refresh
  useEffect(() => {
    async function rehydrate() {
      const token = getToken();
      const storedSession = getStoredSession();
      const storedOrg = getStoredOrg();

      if (!token || !storedSession) {
        clearAuth();
        setStep("login");
        return;
      }

      setSession(storedSession);

      if (!storedOrg) {
        setStep("org");
        return;
      }

      setOrg(storedOrg);

      // Verify organization authorization with the backend
      try {
        if (storedOrg.role === "admin") {
          await api(`/dashboard?org_id=${storedOrg.org_id}`);
          setStep("dashboard");
        } else {
          const rep = await api("/reports/me");
          setStep(rep.answered > 0 ? "report" : "diagnostic");
        }
      } catch (err) {
        const msg = err.message || "";
        // If token expired, invalid, or access revoked, return to login safely
        if (
          msg === "Missing token" ||
          msg === "Invalid token" ||
          msg === "Access denied for this organization" ||
          msg === "Not a member of this organization" ||
          msg === "Select an organization first" ||
          msg.includes("401") ||
          msg.includes("403")
        ) {
          clearAuth();
          setSession(null);
          setOrg(null);
          setStep("login");
        } else {
          // Visible handling for unexpected or network errors
          setAuthError(`Unable to verify session with server: ${msg}`);
          setStep("org");
        }
      }
    }

    rehydrate();
  }, []);

  function logout() {
    clearAuth();
    setSession(null);
    setOrg(null);
    setAuthError("");
    setStep("login");
  }

  function switchOrg() {
    setOrg(null);
    setStoredOrg(null);
    setAuthError("");
    setStep("org");
  }

  async function handleOrgPick(selectedOrg) {
    setOrg(selectedOrg);
    setStoredOrg(selectedOrg);
    setAuthError("");

    if (selectedOrg.role === "admin") {
      setStep("dashboard");
      return;
    }

    // For employees, query GET /reports/me to determine routing
    try {
      const rep = await api("/reports/me");
      if (rep.answered > 0) {
        setStep("report");
      } else {
        setStep("diagnostic");
      }
    } catch (err) {
      // Visibly handle authentication or network failures; do not treat failure as "no responses"
      setAuthError(`Failed to load assessment status: ${err.message}`);
    }
  }

  if (step === "loading") {
    return (
      <div className="wrap">
        <h1>AI Pulse</h1>
        <div className="card">
          <p>Restoring session…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <div className="flex-between">
        <h1>AI Pulse</h1>
        {session && (
          <div style={{ display: "flex", gap: "8px" }}>
            {session.organizations && session.organizations.length > 1 && (
              <button className="secondary" onClick={switchOrg}>
                Switch Org
              </button>
            )}
            <button className="secondary" onClick={logout}>
              Sign Out
            </button>
          </div>
        )}
      </div>

      {authError && (
        <div className="card">
          <p className="error">{authError}</p>
          <button className="secondary" onClick={() => setAuthError("")}>
            Dismiss
          </button>
        </div>
      )}

      {step === "login" && (
        <Login
          onDone={(s) => {
            setSession(s);
            setStep("org");
          }}
        />
      )}
      {step === "org" && (
        <OrgPicker
          orgs={session?.organizations || []}
          onPick={handleOrgPick}
        />
      )}
      {step === "diagnostic" && (
        <Diagnostic onDone={() => setStep("report")} />
      )}
      {step === "report" && (
        <Report onRetake={() => setStep("diagnostic")} />
      )}
      {step === "dashboard" && <Dashboard org={org} />}
    </div>
  );
}
