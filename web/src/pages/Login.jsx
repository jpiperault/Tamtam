import React, { useState } from "react";
import { api } from "../api.js";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/login", { email, password });
      onLogin(await api.get("/auth/me"));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="login">
      <form className="card" onSubmit={submit}>
        <div className="brand" style={{ padding: 0 }}>
          <span className="brand-mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="var(--accent-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <ellipse cx="8.5" cy="8" rx="5.5" ry="2.4" /><path d="M3 8v8a5.5 2.4 0 0 0 11 0V8M17 9.5a4 4 0 0 1 0 5M20 7a8 8 0 0 1 0 10" />
            </svg>
          </span>
          <b>Tamtam</b>
        </div>
        <h1 style={{ fontSize: 24 }}>Connexion</h1>
        <label className="field">Adresse e-mail
          <input className="input" type="email" autoComplete="username" required value={email}
            onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">Mot de passe
          <input className="input" type="password" autoComplete="current-password" required value={password}
            onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <div className="notice danger" role="alert">{error}</div>}
        <button className="btn primary" type="submit" disabled={busy}>{busy ? "Connexion…" : "Se connecter"}</button>
        <p className="muted small" style={{ margin: 0 }}>Pas encore de compte ? Demandez-le à l'administrateur.</p>
        <p className="muted small" style={{ margin: 0 }}><a href="/confidentialite">Confidentialité</a> · <a href="/conditions">Conditions d'utilisation</a></p>
      </form>
    </div>
  );
}
