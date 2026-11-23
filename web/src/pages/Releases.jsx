import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { fmtDateTime } from "../rules.js";
import { Chip, Dialog, Icon, Loading, Seg, useLoad, useRun } from "../ui.jsx";

// Nouvelles versions : Tamtam surveille un dépôt GitHub ou une appli App Store et fait rédiger par Claude un
// brouillon d'annonce à chaque nouvelle version.

const KINDS = [{ value: "appstore", label: "App Store" }, { value: "github", label: "GitHub" }];

function AddDialog({ projectId, onClose, onSaved }) {
  const run = useRun();
  const [f, setF] = useState({ kind: "appstore", ref: "", country: "fr", token: "", instructions: "" });
  const [busy, setBusy] = useState(false);
  const set = (p) => setF({ ...f, ...p });
  const save = async () => {
    setBusy(true);
    const r = await run(() => api.post(`/projects/${projectId}/releases`, f), "Source ajoutée");
    setBusy(false);
    if (r) onSaved(r);
  };
  return (
    <Dialog title="Suivre les nouvelles versions" onClose={onClose}>
      <div className="stack">
        <Seg label="Source" value={f.kind} onChange={(kind) => set({ kind })} options={KINDS} />
        {f.kind === "appstore" ? (
          <>
            <label className="field">Adresse de la fiche App Store
              <input id="rel-ref" className="input" value={f.ref} onChange={(e) => set({ ref: e.target.value })} placeholder="https://apps.apple.com/fr/app/mon-appli/id123456789" /></label>
            <label className="field">Pays de la boutique
              <input className="input mono" style={{ width: 80 }} maxLength={2} value={f.country} onChange={(e) => set({ country: e.target.value.toLowerCase() })} /></label>
            <p className="small muted" style={{ margin: 0 }}>Tamtam lit la version et les notes « Nouveautés » de la fiche publique. Le brouillon reprend le lien de la fiche et sa première capture d'écran.</p>
          </>
        ) : (
          <>
            <label className="field">Dépôt
              <input id="rel-ref" className="input mono" value={f.ref} onChange={(e) => set({ ref: e.target.value })} placeholder="proprietaire/depot ou https://github.com/proprietaire/depot" /></label>
            <label className="field">Jeton GitHub (seulement pour un dépôt privé)
              <input className="input mono" type="password" autoComplete="off" value={f.token} onChange={(e) => set({ token: e.target.value })} placeholder="github_pat_…" /></label>
            <p className="small muted" style={{ margin: 0 }}>Tamtam suit la dernière release publiée (pas les préversions) et donne ses notes à Claude. Pour un dépôt privé : sur GitHub, Settings → Developer settings → Fine-grained tokens, accès à ce seul dépôt, permission « Contents : Read-only ». Le jeton est gardé chiffré.</p>
          </>
        )}
        <label className="field">Consigne pour Claude (facultative)
          <input className="input" maxLength={1000} value={f.instructions} onChange={(e) => set({ instructions: e.target.value })} placeholder="« termine par le code LANCEMENT », « tutoie »…" /></label>
        <div className="dialog-foot"><button type="button" className="btn" onClick={onClose}>Annuler</button>
          <button type="button" id="rel-save" className="btn primary" disabled={busy || !f.ref.trim()} onClick={save}>{busy ? "Lecture…" : "Ajouter"}</button></div>
      </div>
    </Dialog>
  );
}

function Source({ s, onChange }) {
  const run = useRun();
  const [busy, setBusy] = useState("");
  const [ask, setAsk] = useState(s.instructions);
  const act = async (what, fn, msg) => {
    setBusy(what);
    const r = await run(fn, msg);
    setBusy("");
    if (r) onChange();
    return r;
  };
  const check = () => act("check", () => api.post(`/releases/${s.id}/check`)).then((r) => {
    if (r?.post_id) window.location.hash = `#/nouveau/${r.post_id}`;
  });
  const draft = () => act("draft", () => api.post(`/releases/${s.id}/draft`), "Brouillon créé").then((r) => {
    if (r?.post_id) window.location.hash = `#/nouveau/${r.post_id}`;
  });
  return (
    <div className="card stack release">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <b>{s.label || s.ref}</b> <Chip>{s.kind === "appstore" ? `App Store ${s.country.toUpperCase()}` : "GitHub"}</Chip>
          {!s.enabled && <> <Chip tone="warn">en pause</Chip></>}
          <div className="small muted mono">{s.ref}{s.has_token ? " · jeton enregistré" : ""}</div>
        </div>
        <div className="row" style={{ gap: 6 }}>
          {s.url && <a className="btn small ghost" href={s.url} target="_blank" rel="noreferrer"><Icon name="link" size={14} />Voir</a>}
          <button type="button" className="btn small ghost" onClick={() => act("pause", () => api.patch(`/releases/${s.id}`, { enabled: !s.enabled }))}>{s.enabled ? "Mettre en pause" : "Reprendre"}</button>
          <button type="button" className="btn small ghost" aria-label="Ne plus suivre" onClick={() => window.confirm("Ne plus suivre cette source ?") && act("del", () => api.del(`/releases/${s.id}`), "Source retirée")}><Icon name="trash" size={14} /></button>
        </div>
      </div>
      <div className="small">
        Version actuelle : <b className="mono">{s.last_version || "–"}</b>
        {s.last_seen_at && <span className="muted"> (vue le {fmtDateTime(s.last_seen_at)})</span>}
        {s.last_checked_at && <span className="muted"> · vérifié le {fmtDateTime(s.last_checked_at)}</span>}
      </div>
      {s.last_error && <div className="notice danger small"><Icon name="alert" size={16} />{s.last_error}</div>}
      {s.last_post_id && <div className="small">Dernier brouillon : <a href={`#/nouveau/${s.last_post_id}`}>ouvrir</a></div>}
      <div className="row" style={{ gap: 8 }}>
        <input className="input" style={{ flex: "1 1 240px" }} maxLength={1000} value={ask} onChange={(e) => setAsk(e.target.value)} placeholder="Consigne pour Claude (facultative)" />
        {ask !== s.instructions && <button type="button" className="btn small" onClick={() => act("ask", () => api.patch(`/releases/${s.id}`, { instructions: ask }), "Consigne enregistrée")}>Enregistrer</button>}
      </div>
      <div className="row" style={{ gap: 8, justifyContent: "flex-end" }}>
        <button type="button" className="btn small rel-check" disabled={!!busy} onClick={check}><Icon name="refresh" size={14} />{busy === "check" ? "Vérification…" : "Vérifier maintenant"}</button>
        <button type="button" className="btn small primary rel-draft" disabled={!!busy || !s.last_version} onClick={draft}><Icon name="sparkle" size={14} />{busy === "draft" ? "Claude rédige…" : `Brouillon pour la ${s.last_version || "version"}`}</button>
      </div>
    </div>
  );
}

export default function Releases() {
  const { projectId, project } = useApp();
  const [adding, setAdding] = useState(false);
  const { data, error, reload } = useLoad(() => api.get(`/projects/${projectId}/releases`), [projectId]);
  if (!data) return <Loading error={error} />;
  return (
    <>
      <div className="page-head">
        <div><h1>Nouvelles versions</h1><p>{project.name} · à chaque nouvelle version de l'appli, Claude prépare un brouillon d'annonce.</p></div>
        <button type="button" id="rel-add" className="btn primary" onClick={() => setAdding(true)}><Icon name="plus" size={16} />Suivre une appli</button>
      </div>
      {data.length === 0 ? (
        <div className="card empty">Aucune appli suivie. Ajoutez la fiche App Store ou le dépôt GitHub de {project.name} : dès qu'une nouvelle version sort, un brouillon rédigé à partir des notes de version vous attend dans Publications.</div>
      ) : <div className="stack">{data.map((s) => <Source key={s.id} s={s} onChange={reload} />)}</div>}
      <p className="small muted" style={{ marginTop: 16 }}>Vérification toutes les heures. Rien n'est publié tout seul : le brouillon attend votre relecture (alerte Telegram si elle est activée). Google Play n'est pas pris en charge : Google n'offre pas de moyen public et fiable de lire la version d'une appli.</p>
      {adding && <AddDialog projectId={projectId} onClose={() => setAdding(false)} onSaved={() => { setAdding(false); reload(); }} />}
    </>
  );
}
