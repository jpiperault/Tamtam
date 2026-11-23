import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { fmtDateTime } from "../rules.js";
import { Chip, Icon, Loading, NETWORKS, Net } from "../ui.jsx";

// État des connexions : diagnostic en direct de tout ce qu'il faut pour publier en vrai.

const short = (s) => s.replace("https://www.googleapis.com/auth/", "");

export default function Health() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const check = useCallback(async () => {
    setBusy(true); setError("");
    try { setData(await api.post("/admin/diagnostics")); } catch (e) { setError(e.message); }
    setBusy(false);
  }, []);
  useEffect(() => { check(); }, [check]);
  if (!data) return busy ? <div className="card empty">Vérification en cours auprès de chaque réseau…</div> : <Loading error={error} />;
  const p = data.public;
  const bad = data.accounts.filter((a) => !a.ok);
  return (
    <>
      <div className="page-head">
        <div><h1>État des connexions</h1><p>Vérifié le {fmtDateTime(data.checked_at)} auprès de chaque réseau.</p></div>
        <button type="button" id="health-check" className="btn" disabled={busy} onClick={check}><Icon name="refresh" size={16} />{busy ? "Vérification…" : "Vérifier à nouveau"}</button>
      </div>
      {data.simulation && <div className="notice warn" style={{ marginBottom: 14 }}><Icon name="alert" size={16} />Mode simulation : les comptes de démonstration ne contactent aucun réseau. Pour publier en vrai, il faut arrêter la simulation (variable SIMULATION=false) sur le serveur.</div>}
      <div className="kpis" style={{ marginBottom: 16 }}>
        <div className="card kpi"><b className="mono">{data.accounts.length - bad.length}/{data.accounts.length}</b><span>comptes prêts</span></div>
        <div className="card kpi"><b className="mono">{data.apps.filter((a) => a.configured).length}/{data.apps.length}</b><span>applications configurées</span></div>
        <div className="card kpi"><b>{p.https ? "HTTPS" : "HTTP"}</b><span>adresse publique</span></div>
        <div className="card kpi"><b>{p.reachable ? "Joignable" : "Injoignable"}</b><span>depuis le serveur</span></div>
      </div>

      <div className="card stack" style={{ marginBottom: 16 }}>
        <h2>Adresse publique</h2>
        <p style={{ margin: 0 }}><span className="mono">{p.url}</span> {p.https && p.reachable ? <Chip tone="ok">OK</Chip> : <Chip tone="bad">À corriger</Chip>}</p>
        {!p.https && <div className="notice danger small"><Icon name="alert" size={16} />Meta, TikTok et Threads exigent une adresse en https:// pour venir chercher les médias. Corrigez PUBLIC_URL sur le serveur.</div>}
        {p.https && !p.reachable && <div className="notice warn small"><Icon name="alert" size={16} />Le serveur n'arrive pas à se joindre par son adresse publique ({p.detail || "pas de réponse"}). Ce n'est pas forcément grave (certains réseaux privés l'empêchent) : vérifiez que {p.url}/health répond « ok » depuis votre téléphone.</div>}
      </div>

      <div className="card stack" style={{ marginBottom: 16 }}>
        <h2>Applications des réseaux</h2>
        <div className="row" style={{ gap: 10 }}>
          {data.apps.map((a) => (
            <span key={a.provider} className="chip-line">{a.label} {a.configured ? <Chip tone="ok">configurée</Chip> : <Chip tone={a.accounts ? "bad" : "neutral"}>à configurer</Chip>}</span>
          ))}
        </div>
        <p className="small muted" style={{ margin: 0 }}>Bluesky n'a pas besoin d'application. Les identifiants se saisissent dans <a href="#/admin">Administration</a>.</p>
      </div>

      <div className="card flush">
        {data.accounts.length === 0 ? <div className="empty">Aucun compte connecté.</div> : data.accounts.map((a) => (
          <div key={a.id} className="post-row health-row" style={{ gridTemplateColumns: "minmax(0,220px) minmax(0,1fr) auto" }}>
            <div className="row" style={{ gap: 8, flexWrap: "nowrap", alignItems: "flex-start" }}>
              <Net platform={a.platform} />
              <div style={{ minWidth: 0 }}><b>{a.name || NETWORKS[a.platform].label}</b><div className="small muted">{a.project}</div></div>
            </div>
            <div className="stack" style={{ gap: 4, minWidth: 0 }}>
              {a.problem ? <span className={a.ok ? "small" : "err"}>{a.problem}</span>
                : <span className="small">{a.simulated ? "Compte de démonstration : aucun réseau contacté." : `Autorisation acceptée par ${NETWORKS[a.platform].label}.`}</span>}
              {a.missing.length > 0 && <span className="small">Manquantes : <span className="mono">{a.missing.map(short).join(", ")}</span></span>}
              {a.scopes && <span className="small muted">Accordées ({a.scopes_source}) : <span className="mono">{a.scopes.map(short).join(", ") || "aucune"}</span></span>}
              {!a.scopes && !a.simulated && a.platform !== "bluesky" && <span className="small muted">Permissions accordées inconnues{a.scopes_source ? ` : ${a.scopes_source}` : " : reconnectez le compte pour les afficher"}.</span>}
              {a.expires_at && <span className="small muted">Autorisation valable jusqu'au {fmtDateTime(a.expires_at)}</span>}
            </div>
            <div>{a.simulated ? <Chip tone="warn">démo</Chip> : a.ok ? <Chip tone="ok">Prêt</Chip> : <Chip tone="bad">À corriger</Chip>}
              {!a.ok && <div style={{ marginTop: 6 }}><a className="btn small" href="#/comptes">Reconnecter</a></div>}</div>
          </div>
        ))}
      </div>
    </>
  );
}
