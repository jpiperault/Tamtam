import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { parseHash, useApp } from "../App.jsx";
import { fmtDateTime } from "../rules.js";
import { Chip, Icon, Loading, NETWORKS, Net, POST_STATUS, Seg, TARGET_STATUS, useLoad, useRun } from "../ui.jsx";

const FILTERS = [
  { value: "", label: "Tout" },
  { value: "upcoming", label: "À venir" },
  { value: "problems", label: "Échecs" },
  { value: "review", label: "À valider" },
  { value: "draft", label: "Brouillons" },
  { value: "done", label: "Publiés" },
];

export function PostRow({ post, onChange }) {
  const run = useRun();
  const { me } = useApp();
  const [confirm, setConfirm] = useState(false);
  const [rejecting, setRejecting] = useState(null);
  const approve = async () => { if (await run(() => api.post(`/posts/${post.id}/approve`), "Post validé : il partira à l'heure prévue")) onChange(); };
  const reject = async () => { if (await run(() => api.post(`/posts/${post.id}/reject`, { note: rejecting }), "Post refusé : il redevient un brouillon")) { setRejecting(null); onChange(); } };
  const [tone, label] = POST_STATUS[post.status] || ["neutral", post.status];
  const editable = post.status === "draft" || post.status === "scheduled" || post.status === "review";
  const retry = async () => {
    if (await run(() => api.post(`/posts/${post.id}/retry`), "Nouvel essai lancé")) onChange();
  };
  const del = async () => {
    if (await run(() => api.del(`/posts/${post.id}`), "Post supprimé de Tamtam")) onChange();
  };
  return (
    <div className="post-row">
      <div className="post-when">
        {post.status === "draft" && !post.scheduled_at ? "Brouillon" : fmtDateTime(post.scheduled_at)}
        <div style={{ marginTop: 6 }}><Chip tone={tone}>{label}</Chip></div>
      </div>
      <div className="stack" style={{ gap: 8, minWidth: 0 }}>
        <div className="row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
          {post.media[0] && (post.media[0].kind === "video"
            ? <video src={post.media[0].url} muted preload="metadata" style={{ width: 56, height: 56, objectFit: "cover", borderRadius: 6, flex: "none" }} />
            : <img src={post.media[0].url} alt="" style={{ width: 56, height: 56, objectFit: "cover", borderRadius: 6, flex: "none" }} />)}
          <div className="post-body grow">{post.body || <span className="muted">(texte adapté par réseau)</span>}
            {post.campaign && <div className="small muted">Campagne : {post.campaign}</div>}</div>
        </div>
        <div className="row" style={{ gap: 14 }}>
          {post.targets.map((t) => {
            const [tt, tl] = TARGET_STATUS[t.status] || ["neutral", t.status];
            return (
              <span key={t.id} className="tgt">
                <Net platform={t.platform} size="s" />
                {t.external_url ? <a href={t.external_url} target="_blank" rel="noreferrer">{NETWORKS[t.platform].label}</a> : NETWORKS[t.platform].label}
                <Chip tone={tt}>{tl}</Chip>
                {t.link_code && <span className="small muted mono" title="Clics sur le lien suivi">{t.clicks} clic{t.clicks > 1 ? "s" : ""}</span>}
              </span>
            );
          })}
          {post.targets.length === 0 && <span className="small muted">Aucun compte choisi</span>}
        </div>
        {post.status === "review" && <div className="small muted">Proposé par {post.author || "un membre"}, en attente de validation par un administrateur.</div>}
        {post.status === "draft" && post.auto_note && <div className="notice info small"><Icon name="sparkle" size={16} />{post.auto_note}</div>}
        {post.status === "draft" && post.review_note && <div className="notice warn small"><Icon name="alert" size={16} />Refusé : {post.review_note}</div>}
        {rejecting !== null && (
          <div className="stack" style={{ gap: 6 }}>
            <textarea className="textarea reject-note" style={{ minHeight: 60 }} maxLength={1000} placeholder="Ce qu'il faut corriger (visible par l'auteur)" value={rejecting} onChange={(e) => setRejecting(e.target.value)} />
            <div className="row"><button type="button" className="btn small danger" onClick={reject}>Refuser</button><button type="button" className="btn small" onClick={() => setRejecting(null)}>Annuler</button></div>
          </div>
        )}
        {post.targets.filter((t) => t.error).map((t) => (
          <div key={t.id} className="err">{NETWORKS[t.platform].label} : {t.error}{t.status === "pending" && t.not_before ? ` (nouvel essai vers ${fmtDateTime(t.not_before)})` : ""}</div>
        ))}
      </div>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        {post.status === "review" && me.is_admin && <>
          <button type="button" className="btn small primary" onClick={approve}><Icon name="check" size={14} />Valider</button>
          <button type="button" className="btn small" onClick={() => setRejecting("")}>Refuser</button>
        </>}
        {editable && <a className="btn small" href={`#/nouveau/${post.id}`}><Icon name="edit" size={14} />Modifier</a>}
        {(post.status === "failed" || post.status === "partial") && <button type="button" className="btn small" onClick={retry}><Icon name="refresh" size={14} />Réessayer</button>}
        {(post.status === "done" || post.status === "partial") && <a className="btn small" href={`#/nouveau?recycle=${post.id}`} title="Republier ce post dans une nouvelle version rédigée par Claude"><Icon name="sparkle" size={14} />Recycler</a>}
        <a className="btn small" href={`#/nouveau?copy=${post.id}`} title="Créer un nouveau post à partir de celui-ci"><Icon name="copy" size={14} />Dupliquer</a>
        {confirm ? (
          <>
            <button type="button" className="btn small danger" onClick={del}>Confirmer</button>
            <button type="button" className="btn small" onClick={() => setConfirm(false)}>Annuler</button>
          </>
        ) : (
          <button type="button" className="btn small ghost" aria-label="Supprimer" title={post.status === "done" || post.status === "partial" ? "Supprime de Tamtam seulement : le post reste en ligne sur les réseaux" : "Supprimer"}
            onClick={() => setConfirm(true)} disabled={post.status === "publishing"}><Icon name="trash" size={14} /></button>
        )}
      </div>
    </div>
  );
}

export default function Posts() {
  const { projectId, project } = useApp();
  const initial = parseHash(window.location.hash).params.get("status") || "";
  const [filter, setFilter] = useState(initial);
  const { data, error, reload } = useLoad(() => api.get(`/posts?project_id=${projectId}${filter ? `&status=${filter}` : ""}`), [projectId, filter]);
  // Rafraîchit tant qu'une publication est en cours.
  const busy = (data || []).some((p) => p.status === "publishing" || (p.status === "scheduled" && new Date(p.scheduled_at) < new Date(Date.now() + 60e3)));
  useEffect(() => {
    if (!busy) return undefined;
    const t = setInterval(reload, 4000);
    return () => clearInterval(t);
  }, [busy, reload]);
  return (
    <>
      <div className="page-head">
        <div><h1>Publications</h1><p>{project.name} · suivez chaque post réseau par réseau.</p></div>
        <a className="btn primary" href="#/nouveau"><Icon name="plus" size={16} />Nouveau post</a>
      </div>
      <div style={{ marginBottom: 14 }}><Seg label="Filtre" value={filter} onChange={setFilter} options={FILTERS} /></div>
      {!data ? <Loading error={error} /> : data.length === 0 ? (
        <div className="card empty">Rien ici pour l'instant. <a href="#/nouveau">Écrire un premier post</a></div>
      ) : (
        <div className="card flush">{data.map((p) => <PostRow key={p.id} post={p} onChange={reload} />)}</div>
      )}
    </>
  );
}
