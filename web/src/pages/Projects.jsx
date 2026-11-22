import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { DAYS } from "../rules.js";
import { Chip, Dialog, Field, Icon, useRun } from "../ui.jsx";

const sortSlots = (l) => [...l].sort((a, b) => a.day - b.day || a.time.localeCompare(b.time));

function SlotsDialog({ project, onClose, onSaved }) {
  const run = useRun();
  const [list, setList] = useState(sortSlots(project.slots || []));
  const [day, setDay] = useState(1);
  const [time, setTime] = useState("18:00");
  const add = () => {
    if (!time || list.some((s) => s.day === Number(day) && s.time === time)) return;
    setList(sortSlots([...list, { day: Number(day), time }]));
  };
  const save = async () => {
    if (await run(() => api.patch(`/projects/${project.id}`, { slots: list }), "Créneaux enregistrés")) onSaved();
  };
  return (
    <Dialog title={`Créneaux de publication · ${project.name}`} onClose={onClose}>
      <div className="stack">
        <p className="small muted" style={{ margin: 0 }}>Les jours et heures où vos posts partent quand vous choisissez « Prochain créneau ».
          Chaque post prend le premier créneau libre ; une campagne en occupe plusieurs à la suite.</p>
        {list.length === 0 ? <div className="empty small">Aucun créneau pour l'instant.</div> : (
          <div className="row" style={{ gap: 8 }}>
            {list.map((s) => (
              <span key={`${s.day}-${s.time}`} className="chip slot">{DAYS[s.day]} {s.time}
                <button type="button" className="btn ghost small" aria-label={`Retirer ${DAYS[s.day]} ${s.time}`}
                  onClick={() => setList(list.filter((x) => x !== s))}><Icon name="close" size={12} /></button></span>
            ))}
          </div>
        )}
        <div className="row" style={{ gap: 8 }}>
          <select id="slot-day" className="select" style={{ width: "auto" }} value={day} onChange={(e) => setDay(e.target.value)}>
            {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
          </select>
          <input id="slot-time" className="input" type="time" style={{ width: "auto" }} value={time} onChange={(e) => setTime(e.target.value)} />
          <button type="button" id="slot-add" className="btn small" onClick={add}><Icon name="plus" size={14} />Ajouter</button>
        </div>
        <div className="dialog-foot"><button type="button" className="btn" onClick={onClose}>Annuler</button>
          <button type="button" id="slots-save" className="btn primary" onClick={save}>Enregistrer</button></div>
      </div>
    </Dialog>
  );
}

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
        <Field label="Présentation (sert aussi à Claude pour rédiger)"><textarea id="p-desc" className="textarea" style={{ minHeight: 110 }} maxLength={3000} value={f.description} onChange={set("description")}
          placeholder="Ce que fait l'app, pour qui, ses points forts, où la télécharger, le ton de la marque…" /></Field>
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
  const [slotsOf, setSlotsOf] = useState(null);
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
                {!p.archived && <button type="button" className="btn small" onClick={() => setSlotsOf(p)}><Icon name="clock" size={14} />Créneaux{p.slots?.length ? ` (${p.slots.length})` : ""}</button>}
                <button type="button" className="btn small" onClick={() => archive(p)}>{p.archived ? "Réactiver" : "Archiver"}</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {slotsOf && <SlotsDialog project={slotsOf} onClose={() => setSlotsOf(null)} onSaved={() => { setSlotsOf(null); refreshProjects(); }} />}
      {edit && <ProjectForm initial={edit === "new" ? null : edit} onClose={() => setEdit(null)} onSaved={saved} />}
    </>
  );
}
