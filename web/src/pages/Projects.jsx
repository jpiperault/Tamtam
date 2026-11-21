import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Chip, Dialog, Field, Icon, useRun } from "../ui.jsx";

function ProjectForm({ initial, onClose, onSaved }) {
  const run = useRun();
  const [f, setF] = useState(initial || { name: "", url: "", description: "", color: "#0E6E5C" });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    const body = { name: f.name, url: f.url, description: f.description, color: f.color };
    const r = await run(() => (initial ? api.patch(`/projects/${initial.id}`, body) : api.post("/projects", body)),
      initial ? "Projet enregistré" : "Projet créé");
    if (r) onSaved(r);
  };
  return (
    <Dialog title={initial ? "Modifier le projet" : "Nouveau projet"} onClose={onClose}>
      <form className="stack" onSubmit={save}>
        <Field label="Nom (appli, site, produit)"><input id="p-name" className="input" required maxLength={80} value={f.name} onChange={set("name")} /></Field>
        <Field label="Adresse principale (lien proposé par défaut dans les posts)">
          <input id="p-url" className="input" type="url" placeholder="https://" value={f.url} onChange={set("url")} />
        </Field>
        <Field label="Description (pour vous)"><textarea id="p-desc" className="textarea" style={{ minHeight: 80 }} value={f.description} onChange={set("description")} /></Field>
        <Field label="Couleur"><input id="p-color" type="color" value={f.color} onChange={set("color")} style={{ width: 60, height: 34, border: 0, background: "none" }} /></Field>
        <div className="dialog-foot"><button type="button" className="btn" onClick={onClose}>Annuler</button><button className="btn primary" type="submit">Enregistrer</button></div>
      </form>
    </Dialog>
  );
}

export default function Projects() {
  const { projects, refreshProjects, setProjectId, projectId } = useApp();
  const run = useRun();
  const [edit, setEdit] = useState(null);
  const saved = async (p) => {
    setEdit(null);
    await refreshProjects();
    if (!projectId) setProjectId(p.id);
  };
  const archive = async (p) => {
    if (await run(() => api.patch(`/projects/${p.id}`, { archived: !p.archived }), p.archived ? "Projet réactivé" : "Projet archivé")) refreshProjects();
  };
  return (
    <>
      <div className="page-head">
        <div><h1>Projets</h1><p>Une appli, un site ou un produit à faire connaître. Chaque projet a ses comptes, ses posts et ses statistiques.</p></div>
        <button type="button" className="btn primary" onClick={() => setEdit("new")}><Icon name="plus" size={16} />Nouveau projet</button>
      </div>
      {projects.length === 0 ? <div className="card empty">Aucun projet pour l'instant.</div> : (
        <div className="card flush">
          {projects.map((p) => (
            <div key={p.id} className="post-row" style={{ gridTemplateColumns: "14px minmax(0,1fr) auto", alignItems: "center" }}>
              <span style={{ width: 14, height: 14, borderRadius: 4, background: p.color }} aria-hidden="true" />
              <div style={{ minWidth: 0 }}>
                <b>{p.name}</b> {p.archived && <Chip>Archivé</Chip>}
                <div className="small muted">{p.url || "Pas d'adresse"} · {p.accounts} compte{p.accounts > 1 ? "s" : ""} · {p.upcoming} post{p.upcoming > 1 ? "s" : ""} à venir</div>
              </div>
              <div className="row">
                {!p.archived && <button type="button" className="btn small" onClick={() => { setProjectId(p.id); window.location.hash = "#/comptes"; }}>Ouvrir</button>}
                <button type="button" className="btn small" onClick={() => setEdit(p)}>Modifier</button>
                <button type="button" className="btn small" onClick={() => archive(p)}>{p.archived ? "Réactiver" : "Archiver"}</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {edit && <ProjectForm initial={edit === "new" ? null : edit} onClose={() => setEdit(null)} onSaved={saved} />}
    </>
  );
}
