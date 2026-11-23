import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { Dialog, Icon, Loading, NETWORKS, Net, Seg, useRun, useToast } from "../ui.jsx";

// Outils de l'écran de rédaction : bibliothèque du projet, traduction par Claude, visuels d'annonce.

export const KIND_LABELS = { hashtags: "Hashtags", signature: "Signatures", text: "Textes" };

// --- Bibliothèque : groupes de hashtags, signatures, textes réutilisables

export function LibraryDialog({ projectId, onInsert, onClose }) {
  const run = useRun();
  const [list, setList] = useState(null);
  const [f, setF] = useState({ kind: "hashtags", name: "", body: "" });
  const [editing, setEditing] = useState(null);
  const load = () => api.get(`/projects/${projectId}/snippets`).then(setList).catch(() => setList([]));
  useEffect(() => { load(); }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async () => {
    const r = await run(() => (editing ? api.put(`/snippets/${editing}`, f) : api.post(`/projects/${projectId}/snippets`, f)),
      editing ? "Élément modifié" : "Ajouté à la bibliothèque");
    if (r) { setF({ ...f, name: "", body: "" }); setEditing(null); load(); }
  };
  const remove = async (s) => { if (window.confirm(`Supprimer « ${s.name} » ?`) && await run(() => api.del(`/snippets/${s.id}`))) load(); };
  return (
    <Dialog title="Bibliothèque du projet" onClose={onClose}>
      <div className="stack">
        {!list ? <Loading /> : list.length === 0 ? <div className="empty small">Rien pour l'instant. Ajoutez vos hashtags habituels, une signature (« Téléchargez l'appli gratuitement ») ou un texte qui revient souvent.</div>
          : Object.keys(KIND_LABELS).filter((k) => list.some((s) => s.kind === k)).map((k) => (
            <div key={k} className="stack" style={{ gap: 6 }}>
              <span className="label">{KIND_LABELS[k]}</span>
              {list.filter((s) => s.kind === k).map((s) => (
                <div key={s.id} className="snippet row" style={{ gap: 8, flexWrap: "nowrap", alignItems: "flex-start" }}>
                  <div className="grow" style={{ minWidth: 0 }}><b className="small">{s.name}</b><div className="small muted snippet-body">{s.body}</div></div>
                  <button type="button" className="btn small primary snippet-insert" onClick={() => onInsert(s)}>Insérer</button>
                  <button type="button" className="btn small ghost" aria-label={`Modifier ${s.name}`} onClick={() => { setEditing(s.id); setF({ kind: s.kind, name: s.name, body: s.body }); }}><Icon name="edit" size={14} /></button>
                  <button type="button" className="btn small ghost" aria-label={`Supprimer ${s.name}`} onClick={() => remove(s)}><Icon name="trash" size={14} /></button>
                </div>
              ))}
            </div>
          ))}
        <div className="card stack" style={{ background: "var(--sunk)", boxShadow: "none" }}>
          <span className="label">{editing ? "Modifier" : "Ajouter"}</span>
          <Seg label="Type" value={f.kind} onChange={(kind) => setF({ ...f, kind })}
            options={Object.entries(KIND_LABELS).map(([value, label]) => ({ value, label: label.replace(/s$/, "") }))} />
          <input id="snippet-name" className="input" maxLength={80} placeholder="Nom (pour vous) : « Hashtags cuisine »" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
          <textarea id="snippet-body" className="textarea" style={{ minHeight: 70 }} maxLength={5000} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })}
            placeholder={f.kind === "hashtags" ? "recette cuisine #faitmaison (le # est ajouté si besoin)" : f.kind === "signature" ? "📲 Téléchargez Le Bon Plat gratuitement : lien en bio" : "Le texte à réutiliser"} />
          <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
            {editing && <button type="button" className="btn small" onClick={() => { setEditing(null); setF({ ...f, name: "", body: "" }); }}>Annuler</button>}
            <button type="button" id="snippet-save" className="btn small" disabled={!f.name.trim() || !f.body.trim()} onClick={save}>{editing ? "Enregistrer" : "Ajouter"}</button>
          </div>
        </div>
      </div>
    </Dialog>
  );
}

// Ajoute un élément de la bibliothèque à la fin du texte (sur une nouvelle ligne).
export function appendSnippet(text, s) {
  const t = text.replace(/\s+$/, "");
  if (!t) return s.body;
  return `${t}${s.kind === "text" ? "\n" : "\n\n"}${s.body}`;
}

// --- Traduction : comptes publiés dans une autre langue

export function TranslateBar({ projectId, accounts, body, hasLink, languages, onApply }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const foreign = accounts.filter((a) => a.language);
  if (foreign.length === 0) return null;
  const label = (code) => languages.find((l) => l.code === code)?.label || code;
  const go = async () => {
    setBusy(true); setNote("");
    try {
      const r = await api.post("/ai/translate", { project_id: projectId, has_link: hasLink,
        items: foreign.map((a) => ({ key: String(a.id), platform: a.platform, language: a.language, text: body })) });
      onApply(r.texts);
      setNote([r.note, r.too_long.length ? "Une traduction dépasse la limite de son réseau : raccourcissez-la." : ""].filter(Boolean).join(" "));
      toast("Traductions appliquées : relisez l'onglet de chaque compte");
    } catch (e) { toast(e.message, true); }
    setBusy(false);
  };
  return (
    <div className="notice info small translate-bar" style={{ alignItems: "center", flexWrap: "wrap" }}>
      <Icon name="chat" size={16} />
      <span className="grow">Publié dans une autre langue : {foreign.map((a) => <span key={a.id} className="row" style={{ display: "inline-flex", gap: 4, marginRight: 8 }}><Net platform={a.platform} size="s" />{NETWORKS[a.platform].label} ({label(a.language)})</span>)}
        {note && <><br />{note}</>}</span>
      <button type="button" id="btn-translate" className="btn small" disabled={busy || !body.trim()} onClick={go}><Icon name="sparkle" size={14} />{busy ? "Traduction…" : "Traduire le texte commun avec Claude"}</button>
    </div>
  );
}

// --- Visuels d'annonce

const TEMPLATES = [{ value: "annonce", label: "Annonce" }, { value: "clair", label: "Clair" }, { value: "citation", label: "Citation" }];
const FORMATS = [{ value: "carre", label: "Carré" }, { value: "portrait", label: "Portrait 4:5" }, { value: "story", label: "Story 9:16" }, { value: "paysage", label: "Paysage 16:9" }];

export function VisualDialog({ project, images, onCreated, onClose }) {
  const run = useRun();
  const [f, setF] = useState({ template: "annonce", format: "carre", title: "", subtitle: "", badge: "", footer: project.url.replace(/^https?:\/\//, "").replace(/\/$/, "") || project.name, color: project.color, media_id: null });
  const [lib, setLib] = useState(images);
  const [img, setImg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const timer = useRef();
  useEffect(() => {
    api.get(`/projects/${project.id}/media`).then((l) => setLib(l.filter((m) => m.kind === "image" && !m.filename.startsWith("visuel-")))).catch(() => {});
  }, [project.id]);
  useEffect(() => {
    clearTimeout(timer.current);
    if (!f.title.trim() && !f.media_id) { setImg(""); setErr(""); return undefined; }
    timer.current = setTimeout(async () => {
      try {
        const b = await api.blob(`/projects/${project.id}/visuals/preview`, f);
        setImg((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(b); });
        setErr("");
      } catch (e) { setErr(e.message); }
    }, 400);
    return () => clearTimeout(timer.current);
  }, [f, project.id]);
  const set = (p) => setF({ ...f, ...p });
  const create = async () => {
    setBusy(true);
    const m = await run(() => api.post(`/projects/${project.id}/visuals`, f), "Visuel ajouté au post et à la médiathèque");
    setBusy(false);
    if (m) onCreated(m);
  };
  const quote = f.template === "citation";
  return (
    <Dialog title="Créer un visuel" onClose={onClose} wide>
      <div className="visual-grid">
        <div className="stack">
          <Seg label="Modèle" value={f.template} onChange={(template) => set({ template })} options={TEMPLATES} />
          <Seg label="Format" value={f.format} onChange={(format) => set({ format })} options={FORMATS} />
          <label className="field">{quote ? "Citation" : "Titre"}<textarea id="vis-title" className="textarea" style={{ minHeight: 60 }} maxLength={200} value={f.title} onChange={(e) => set({ title: e.target.value })} placeholder={quote ? "« Enfin une appli qui… »" : "Le mode sombre arrive"} /></label>
          <label className="field">{quote ? "Auteur de la citation" : "Accroche (facultative)"}<input className="input" maxLength={300} value={f.subtitle} onChange={(e) => set({ subtitle: e.target.value })} placeholder={quote ? "Camille, sur l'App Store" : "Plus doux pour les yeux, le soir."} /></label>
          {!quote && <label className="field">Étiquette (facultative)<input className="input" maxLength={30} value={f.badge} onChange={(e) => set({ badge: e.target.value })} placeholder="Nouveau, Version 2.1, -30 %…" /></label>}
          <label className="field">Bas de l'image<input className="input" maxLength={60} value={f.footer} onChange={(e) => set({ footer: e.target.value })} /></label>
          <label className="field">Couleur<span className="row" style={{ gap: 8 }}><input type="color" value={f.color} onChange={(e) => set({ color: e.target.value })} aria-label="Couleur" />
            {f.color.toLowerCase() !== project.color.toLowerCase() && <button type="button" className="btn small ghost" onClick={() => set({ color: project.color })}>Couleur du projet</button>}</span></label>
          {!quote && (
            <div className="field"><span className="label">Capture d'écran (facultative)</span>
              {lib.length === 0 ? <span className="small muted">Ajoutez d'abord une capture à la médiathèque (zone Médias).</span> : (
                <div className="media-strip">
                  <button type="button" className="thumb vis-none" style={{ outline: !f.media_id ? "3px solid var(--accent)" : undefined }} onClick={() => set({ media_id: null })}><span className="small">Aucune</span></button>
                  {lib.slice(0, 12).map((m) => (
                    <button key={m.id} type="button" className="thumb vis-shot" style={{ padding: 0, outline: f.media_id === m.id ? "3px solid var(--accent)" : undefined }} onClick={() => set({ media_id: m.id })}><img src={m.url} alt={m.filename} /></button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        <div className="stack">
          <div className={`visual-preview f-${f.format}`}>{img ? <img id="vis-preview" src={img} alt="Aperçu du visuel" /> : <span className="small muted">{err || "Écrivez un titre pour voir l'aperçu."}</span>}</div>
          {err && img && <div className="notice danger small"><Icon name="alert" size={16} />{err}</div>}
        </div>
      </div>
      <div className="dialog-foot"><button type="button" className="btn" onClick={onClose}>Annuler</button>
        <button type="button" id="vis-create" className="btn primary" disabled={busy || !img} onClick={create}>{busy ? "Création…" : "Ajouter au post"}</button></div>
    </Dialog>
  );
}
