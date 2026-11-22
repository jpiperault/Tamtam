import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { fmtDateTime } from "../rules.js";
import { Chip, Icon, Loading, NETWORKS, Net, Seg, useLoad, useRun } from "../ui.jsx";

// Boîte de réception : les commentaires reçus sous les posts publiés, tous réseaux confondus.

const FILTERS = [
  { value: "new", label: "À traiter" }, { value: "replied", label: "Répondus" },
  { value: "done", label: "Traités" }, { value: "all", label: "Tout" },
];
const LIMITS = { x: 280, bluesky: 300, threads: 500 };

function Item({ it, onChange }) {
  const run = useRun();
  const [text, setText] = useState("");
  const [ask, setAsk] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const limit = LIMITS[it.platform];
  const suggest = async () => {
    setBusy("claude"); setErr("");
    try {
      const r = await api.post(`/inbox/${it.id}/suggest`, { instructions: ask });
      setText(r.reply); setNote(r.note);
    } catch (e) { setErr(e.message); }
    setBusy("");
  };
  const send = async () => {
    setBusy("send"); setErr("");
    try { await api.post(`/inbox/${it.id}/reply`, { text }); onChange(); } catch (e) { setErr(e.message); }
    setBusy("");
  };
  const mark = async (status) => { if (await run(() => api.post(`/inbox/${it.id}/status`, { status }))) onChange(); };
  return (
    <div className="card stack inbox-item">
      <div className="row" style={{ gap: 10, alignItems: "flex-start", flexWrap: "nowrap" }}>
        {it.author_avatar ? <img className="av" src={it.author_avatar} alt="" /> : <div className="av" />}
        <div className="grow" style={{ minWidth: 0 }}>
          <div className="row" style={{ gap: 6 }}>
            <b>{it.author_name || it.author_handle || "Quelqu'un"}</b>
            {it.author_handle && it.author_handle !== it.author_name && <span className="muted small">@{it.author_handle}</span>}
            <span className="row small muted" style={{ gap: 4 }}><Net platform={it.platform} size="s" />{NETWORKS[it.platform].label}</span>
            {it.commented_at && <span className="small muted">{fmtDateTime(it.commented_at)}</span>}
          </div>
          <div className="inbox-text">{it.text}</div>
          <div className="small muted inbox-post">Sous le post : {it.external_url ? <a href={it.external_url} target="_blank" rel="noreferrer">{it.post_text || "voir"}</a> : it.post_text}</div>
        </div>
        {it.status === "replied" && <Chip tone="ok">Répondu</Chip>}
        {it.status === "done" && <Chip>Traité</Chip>}
      </div>
      {it.status === "replied" ? (
        <div className="small inbox-reply"><b>Votre réponse</b>{it.replied_by_name ? ` (${it.replied_by_name}, ${fmtDateTime(it.replied_at)})` : ""} : {it.reply_text}</div>
      ) : it.status === "done" ? (
        <div className="row"><button type="button" className="btn small" onClick={() => mark("new")}>Remettre à traiter</button></div>
      ) : (
        <div className="stack" style={{ gap: 8 }}>
          <textarea className="textarea inbox-answer" style={{ minHeight: 70 }} value={text} onChange={(e) => setText(e.target.value)} placeholder="Votre réponse…" />
          {limit && <span className={`small ${text.length > limit ? "err" : "muted"}`}>{text.length}/{limit}</span>}
          {note && <div className="notice warn small"><Icon name="alert" size={16} />{note}</div>}
          {err && <div className="notice danger small"><Icon name="alert" size={16} />{err}</div>}
          <div className="row" style={{ gap: 8 }}>
            <input className="input" style={{ flex: "1 1 220px" }} value={ask} onChange={(e) => setAsk(e.target.value)} maxLength={1000} placeholder="Consigne pour Claude (facultatif) : « tutoie », « propose un code promo »…" />
            <button type="button" className="btn small inbox-suggest" disabled={!!busy} onClick={suggest}><Icon name="sparkle" size={14} />{busy === "claude" ? "Claude rédige…" : "Proposer avec Claude"}</button>
          </div>
          <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button type="button" className="btn small" onClick={() => mark("done")}>Marquer comme traité</button>
            <button type="button" className="btn small primary inbox-send" disabled={!!busy || !text.trim() || (limit && text.length > limit)} onClick={send}>
              <Icon name="check" size={14} />{busy === "send" ? "Envoi…" : `Répondre sur ${NETWORKS[it.platform].label}`}</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Inbox() {
  const { projectId, project, me } = useApp();
  const run = useRun();
  const [filter, setFilter] = useState("new");
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState([]);
  const { data, error, reload } = useLoad(() => api.get(`/inbox?project_id=${projectId}&status=${filter}`), [projectId, filter]);
  if (!data) return <Loading error={error} />;
  const refresh = async () => {
    setBusy(true);
    const r = await run(() => api.post(`/inbox/refresh?project_id=${projectId}`));
    setBusy(false);
    if (r) { setErrors(r.errors); reload(); }
  };
  const off = ["facebook", "instagram", "threads", "youtube", "x"].filter((p) => !data.enabled.includes(p));
  return (
    <>
      <div className="page-head">
        <div><h1>Boîte de réception</h1><p>{project.name} · les commentaires reçus sous vos posts, tous réseaux confondus.</p></div>
        <button type="button" id="inbox-refresh" className="btn" disabled={busy} onClick={refresh}><Icon name="refresh" size={16} />{busy ? "Relève…" : "Relever"}</button>
      </div>
      <div style={{ marginBottom: 14 }}><Seg label="Filtre" value={filter} onChange={setFilter} options={FILTERS} /></div>
      {errors.map((e) => <div key={e} className="notice warn small" style={{ marginBottom: 8 }}><Icon name="alert" size={16} />{e}</div>)}
      {data.items.length === 0 ? (
        <div className="card empty">{filter === "new" ? "Aucun commentaire à traiter." : "Rien ici."} Tamtam relève les commentaires toutes les 30 minutes, sur les posts publiés depuis moins de 30 jours.</div>
      ) : <div className="stack">{data.items.map((it) => <Item key={it.id} it={it} onChange={reload} />)}</div>}
      <p className="small muted" style={{ marginTop: 16 }}>
        Relevés : {data.enabled.map((p) => NETWORKS[p].label).join(", ")}.
        {off.length > 0 && <> Pas encore : {off.map((p) => NETWORKS[p].label).join(", ")} ({me.is_admin ? <a href="#/admin">permissions à activer dans Administration</a> : "un administrateur doit activer les permissions"}).</>}
        {" "}TikTok et LinkedIn ne permettent pas de lire les commentaires.
      </p>
    </>
  );
}
