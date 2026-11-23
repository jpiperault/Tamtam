import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Chip, Dialog, Icon, Loading, NETWORKS, Net, Seg, useLoad, useRun, useToast } from "../ui.jsx";

// Page « lien en bio » : une page publique par projet, à mettre dans la bio des réseaux.

const BIO_NETS = ["instagram", "tiktok", "threads", "x", "bluesky", "youtube", "linkedin", "facebook"];
const SRC_LABEL = { direct: "Accès direct" };

function CopyLine({ label, text, platform }) {
  const toast = useToast();
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); toast("Adresse copiée"); } catch { toast("Copie impossible : sélectionnez le texte", true); }
  };
  return (
    <div className="row bio-url" style={{ gap: 8, flexWrap: "nowrap" }}>
      {platform ? <Net platform={platform} size="s" /> : null}
      <span className="small" style={{ minWidth: 90 }}>{label}</span>
      <code className="grow small" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{text}</code>
      <button type="button" className="btn small ghost" onClick={copy} aria-label={`Copier l'adresse pour ${label}`}><Icon name="copy" size={14} /></button>
    </div>
  );
}

function AvatarPicker({ projectId, onPick, onClose }) {
  const { data, error } = useLoad(() => api.get(`/projects/${projectId}/media`), [projectId]);
  const images = (data || []).filter((m) => m.kind === "image");
  return (
    <Dialog title="Image de la page" onClose={onClose}>
      {!data ? <Loading error={error} /> : images.length === 0 ? <div className="empty">Aucune image dans la médiathèque du projet. Ajoutez-en une depuis « Nouveau post ».</div> : (
        <div className="media-strip">{images.map((m) => (
          <button key={m.id} type="button" className="thumb" style={{ padding: 0 }} onClick={() => onPick(m)}><img src={m.url} alt={m.filename} /></button>
        ))}</div>
      )}
    </Dialog>
  );
}

function Stats({ projectId, links, version }) {
  const [days, setDays] = useState(30);
  const { data, error, reload } = useLoad(() => api.get(`/projects/${projectId}/bio/stats?days=${days}`), [projectId, days]);
  useEffect(() => { reload(); }, [version]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return <Loading error={error} />;
  const total = data.views.reduce((a, v) => a + v.n, 0);
  const clicks = data.clicks.reduce((a, v) => a + v.n, 0);
  const label = (id) => links.find((l) => l.id === id)?.label || "lien retiré";
  return (
    <div className="card stack">
      <div className="row" style={{ justifyContent: "space-between" }}><h2>Visites et clics</h2>
        <Seg label="Période" value={days} onChange={setDays} options={[{ value: 7, label: "7 j" }, { value: 30, label: "30 j" }, { value: 90, label: "90 j" }]} /></div>
      <div className="kpis" style={{ gridTemplateColumns: "repeat(3, minmax(0,1fr))" }}>
        <div className="card kpi"><b className="mono">{total}</b><span>visites</span></div>
        <div className="card kpi"><b className="mono">{clicks}</b><span>clics sur les liens</span></div>
        <div className="card kpi"><b className="mono">{total ? Math.round((clicks / total) * 100) : 0} %</b><span>des visites cliquent</span></div>
      </div>
      {total === 0 ? <p className="muted small" style={{ margin: 0 }}>Pas encore de visite sur la période.</p> : (
        <div className="grid2">
          <div><span className="label">Visites par réseau d'origine</span>
            {data.views.map((v) => <div key={v.source} className="row small" style={{ justifyContent: "space-between" }}><span className="row" style={{ gap: 6 }}>{NETWORKS[v.source] && <Net platform={v.source} size="s" />}{NETWORKS[v.source]?.label || SRC_LABEL[v.source] || v.source}</span><span className="mono">{v.n}</span></div>)}</div>
          <div><span className="label">Clics par lien</span>
            {data.clicks.map((c) => <div key={c.link_id} className="row small" style={{ justifyContent: "space-between" }}><span>{label(c.link_id)}</span><span className="mono">{c.n}</span></div>)}</div>
        </div>
      )}
    </div>
  );
}

export default function Bio() {
  const { projectId, project } = useApp();
  const run = useRun();
  const [f, setF] = useState(null);
  const [saved, setSaved] = useState(null);
  const [picker, setPicker] = useState(false);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    setF(null);
    api.get(`/projects/${projectId}/bio`).then((b) => { setF(b); setSaved(b); }).catch(() => setF(false));
  }, [projectId]);
  if (f === null) return <Loading />;
  if (f === false) return <div className="notice danger">Page indisponible.</div>;
  const set = (patch) => setF({ ...f, ...patch });
  const setLink = (i, patch) => set({ links: f.links.map((l, j) => (j === i ? { ...l, ...patch } : l)) });
  const move = (i, d) => { const l = [...f.links]; [l[i], l[i + d]] = [l[i + d], l[i]]; set({ links: l }); };
  const save = async (patch = {}) => {
    const body = { ...f, ...patch, links: (patch.links || f.links).filter((l) => l.label.trim() || l.url.trim()) };
    const r = await run(() => api.put(`/projects/${projectId}/bio`, body), patch.enabled === true ? "Page en ligne" : patch.enabled === false ? "Page désactivée" : "Page enregistrée");
    if (r) { setF(r); setSaved(r); setVersion((v) => v + 1); }
  };
  const dirty = JSON.stringify(f) !== JSON.stringify(saved);
  return (
    <>
      <div className="page-head">
        <div><h1>Lien en bio</h1><p>{project.name} · une page publique avec vos liens, à mettre dans la bio d'Instagram, TikTok, Threads…</p></div>
        <div className="row">
          {saved.enabled ? <Chip tone="ok">En ligne</Chip> : <Chip>Hors ligne</Chip>}
          {saved.enabled && <a className="btn" href={saved.url} target="_blank" rel="noreferrer"><Icon name="link" size={16} />Ouvrir la page</a>}
          <button type="button" id="bio-toggle" className={`btn ${saved.enabled ? "" : "primary"}`} onClick={() => save({ enabled: !saved.enabled })}>{saved.enabled ? "Désactiver" : "Mettre en ligne"}</button>
        </div>
      </div>
      <div className="compose">
        <div className="card stack">
          <label className="field">Adresse de la page
            <div className="row" style={{ gap: 6, flexWrap: "nowrap" }}><span className="small muted mono">{saved.url.replace(/\/b\/.*$/, "/b/")}</span>
              <input id="bio-slug" className="input mono" value={f.slug} maxLength={40} onChange={(e) => set({ slug: e.target.value.toLowerCase() })} /></div>
          </label>
          <div className="row" style={{ gap: 12, alignItems: "center" }}>
            {f.avatar_url ? <img src={f.avatar_url} alt="" style={{ width: 56, height: 56, borderRadius: "50%", objectFit: "cover" }} />
              : <div style={{ width: 56, height: 56, borderRadius: "50%", background: project.color, color: "#fff", display: "grid", placeItems: "center", fontWeight: 700, fontSize: 22 }}>{project.name[0]?.toUpperCase()}</div>}
            <button type="button" className="btn small" onClick={() => setPicker(true)}><Icon name="image" size={14} />Choisir une image</button>
            {f.avatar_media_id && <button type="button" className="btn small ghost" onClick={() => set({ avatar_media_id: null, avatar_url: "" })}>Retirer</button>}
          </div>
          <label className="field">Titre<input id="bio-title" className="input" maxLength={80} value={f.title} onChange={(e) => set({ title: e.target.value })} placeholder={project.name} /></label>
          <label className="field">Phrase d'accroche (facultative)<input className="input" maxLength={200} value={f.subtitle} onChange={(e) => set({ subtitle: e.target.value })} placeholder="L'appli qui…" /></label>
          <div className="field"><span className="label">Liens (boutons de la page, dans cet ordre)</span>
            <div className="stack" style={{ gap: 8 }}>
              {f.links.map((l, i) => (
                <div key={l.id || i} className="row bio-link" style={{ gap: 6, flexWrap: "nowrap" }}>
                  <input className="input" style={{ flex: "0 1 40%" }} placeholder="Texte du bouton" value={l.label} maxLength={80} onChange={(e) => setLink(i, { label: e.target.value })} />
                  <input className="input grow" type="url" placeholder="https://" value={l.url} onChange={(e) => setLink(i, { url: e.target.value })} />
                  <button type="button" className="btn small ghost" disabled={i === 0} onClick={() => move(i, -1)} aria-label="Monter">↑</button>
                  <button type="button" className="btn small ghost" disabled={i === f.links.length - 1} onClick={() => move(i, 1)} aria-label="Descendre">↓</button>
                  <button type="button" className="btn small ghost" onClick={() => set({ links: f.links.filter((_, j) => j !== i) })} aria-label="Retirer"><Icon name="trash" size={14} /></button>
                </div>
              ))}
              {f.links.length < 20 && <button type="button" id="bio-add" className="btn small" style={{ alignSelf: "flex-start" }} onClick={() => set({ links: [...f.links, { id: "", label: "", url: "" }] })}><Icon name="plus" size={14} />Ajouter un lien</button>}
              <span className="small muted">Idées : App Store, Google Play, site, offre de lancement, newsletter. Chaque clic est compté.</span>
            </div>
          </div>
          <label className="check"><input type="checkbox" checked={f.show_latest} onChange={(e) => set({ show_latest: e.target.checked })} /><span>Montrer le dernier post publié (texte, image et liens vers les réseaux)</span></label>
          <div className="actions"><button type="button" id="bio-save" className="btn primary" disabled={!dirty} onClick={() => save()}>Enregistrer</button></div>
        </div>
        <div className="stack">
          <div className="card stack">
            <h2>Adresses à mettre dans vos bios</h2>
            <p className="small muted" style={{ margin: 0 }}>Une adresse par réseau, pour savoir d'où viennent les visites. Collez-la dans le champ « Site web » ou « Lien » du profil.</p>
            {BIO_NETS.map((n) => <CopyLine key={n} platform={n} label={NETWORKS[n].label} text={saved.per_network[n]} />)}
            <CopyLine label="Autre" text={saved.url} />
          </div>
          {saved.enabled ? <iframe title="Aperçu de la page" src={`${saved.url.replace(/^https?:\/\/[^/]+/, "")}?preview=1&v=${version}`} className="bio-preview" />
            : <div className="card empty small">La page est hors ligne : « Mettre en ligne » pour la publier et voir l'aperçu (l'aperçu n'est pas compté dans les visites).</div>}
          <Stats projectId={projectId} links={saved.links} version={version} />
        </div>
      </div>
      {picker && <AvatarPicker projectId={projectId} onClose={() => setPicker(false)} onPick={(m) => { set({ avatar_media_id: m.id, avatar_url: m.url }); setPicker(false); }} />}
    </>
  );
}
