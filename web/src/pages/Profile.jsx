import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Field, useRun } from "../ui.jsx";

export default function Profile() {
  const { me, setMe } = useApp();
  const run = useRun();
  const [name, setName] = useState(me.name || "");
  const logout = async () => {
    await run(() => api.post("/auth/logout"));
    window.dispatchEvent(new Event("tamtam:logout"));
  };
  const logoutAll = async () => {
    if (!window.confirm("Fermer toutes vos sessions, sur tous vos appareils (y compris celui-ci) ?")) return;
    await run(() => api.post("/auth/logout-all"));
    window.dispatchEvent(new Event("tamtam:logout"));
  };
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });

  const saveProfile = async (e) => {
    e.preventDefault();
    const r = await run(() => api.patch("/auth/me", { name }), "Profil enregistré");
    if (r) setMe(r);
  };
  const savePassword = async (e) => {
    e.preventDefault();
    if (pw.next !== pw.confirm) return run(() => Promise.reject(new Error("les deux mots de passe diffèrent")));
    const r = await run(() => api.patch("/auth/me", { current_password: pw.current, new_password: pw.next }),
      "Mot de passe changé : vos autres appareils sont déconnectés");
    if (r) setPw({ current: "", next: "", confirm: "" });
  };
  return (
    <>
      <div className="page-head">
        <div>
          <p className="muted" style={{ margin: 0 }}>{me.email}{me.is_admin ? " · administrateur" : ""}</p>
          <h1>Mon profil</h1>
        </div>
        <div className="row">
          <button type="button" className="btn" onClick={logout}>Se déconnecter</button>
          <button type="button" className="btn" onClick={logoutAll} title="Utile si vous avez perdu un téléphone ou utilisé un poste partagé">Déconnecter tous mes appareils</button>
        </div>
      </div>
      <div className="grid2">
        <form className="card stack" onSubmit={saveProfile}>
          <h2>Informations</h2>
          <Field label="Nom affiché"><input className="input" value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <button className="btn primary" type="submit" style={{ alignSelf: "flex-start" }}>Enregistrer</button>
        </form>
        <form className="card stack" onSubmit={savePassword}>
          <h2>Changer de mot de passe</h2>
          <Field label="Mot de passe actuel">
            <input className="input" type="password" autoComplete="current-password" required value={pw.current}
              onChange={(e) => setPw({ ...pw, current: e.target.value })} />
          </Field>
          <Field label="Nouveau mot de passe (10 caractères minimum)">
            <input className="input" type="password" autoComplete="new-password" required minLength={10} value={pw.next}
              onChange={(e) => setPw({ ...pw, next: e.target.value })} />
          </Field>
          <Field label="Confirmer le nouveau mot de passe">
            <input className="input" type="password" autoComplete="new-password" required value={pw.confirm}
              onChange={(e) => setPw({ ...pw, confirm: e.target.value })} />
          </Field>
          <button className="btn primary" type="submit" style={{ alignSelf: "flex-start" }}>Changer le mot de passe</button>
        </form>
      </div>
    </>
  );
}
