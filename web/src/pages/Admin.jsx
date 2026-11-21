import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Chip, Dialog, Field, Icon, Loading, useLoad, useRun, useToast } from "../ui.jsx";

const GUIDES = {
  meta: ["Créez une app de type « Entreprise » sur developers.facebook.com.",
    "Ajoutez les produits « Facebook Login for Business » et « Instagram » (API Graph).",
    "Collez l'adresse de retour ci-dessous dans les URI de redirection OAuth valides.",
    "Demandez l'accès avancé aux autorisations pages_manage_posts, instagram_content_publish… (App Review) pour publier sur des comptes qui ne sont pas administrateurs de l'app."],
  x: ["Créez un projet et une app sur developer.x.com.",
    "Dans « User authentication settings » : OAuth 2.0, type « Web App, Automated App or Bot », droits Read and write.",
    "Collez l'adresse de retour ci-dessous comme Callback URI, puis copiez le Client ID et le Client Secret OAuth 2.0.",
    "Vérifiez que votre offre d'accès à l'API permet de publier."],
  tiktok: ["Créez une app sur developers.tiktok.com et ajoutez Login Kit et Content Posting API (Direct Post activé).",
    "Collez l'adresse de retour ci-dessous comme Redirect URI ; copiez le Client key et le Client secret.",
    "Pour les carrousels photo, vérifiez le domaine de Tamtam (URL properties) dans le portail.",
    "Soumettez l'app à l'audit TikTok pour publier en public ; avant l'audit, les posts sont privés."],
};

function Copy({ text }) {
  const toast = useToast();
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copié");
    } catch {
      toast("Copie impossible : sélectionnez le texte à la main", true);
    }
  };
  return <div className="copybox"><code>{text}</code><button type="button" className="btn small" onClick={copy}><Icon name="copy" size={14} />Copier</button></div>;
}

function AppCard({ app, onSaved }) {
  const run = useRun();
  const [cid, setCid] = useState(app.client_id);
  const [secret, setSecret] = useState("");
  const save = async (e) => {
    e.preventDefault();
    const body = { client_id: cid };
    if (secret) body.client_secret = secret;
    if (await run(() => api.put(`/admin/apps/${app.provider}`, body), "Identifiants enregistrés")) { setSecret(""); onSaved(); }
  };
  return (
    <form className="card stack" onSubmit={save}>
      <div className="row"><h2 className="grow">{app.label}</h2>{app.client_id && app.has_secret ? <Chip tone="ok">Configurée</Chip> : <Chip tone="warn">À configurer</Chip>}</div>
      <ol className="small" style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4 }}>
        {GUIDES[app.provider].map((g) => <li key={g}>{g}</li>)}
      </ol>
      <div className="field">Adresse de retour à déclarer<Copy text={app.redirect_uri} /><span className="small muted" style={{ fontWeight: 400 }}>{app.where}</span></div>
      <Field label={app.provider === "tiktok" ? "Client key" : app.provider === "meta" ? "Identifiant de l'app (App ID)" : "Client ID (OAuth 2.0)"}>
        <input id={`cid-${app.provider}`} className="input mono" value={cid} onChange={(e) => setCid(e.target.value)} autoComplete="off" />
      </Field>
      <Field label={`${app.provider === "meta" ? "Clé secrète (App Secret)" : "Client secret"}${app.has_secret ? " · enregistré, laissez vide pour le garder" : ""}`}>
        <input id={`sec-${app.provider}`} className="input mono" type="password" value={secret} onChange={(e) => setSecret(e.target.value)} autoComplete="new-password" />
      </Field>
      <button className="btn primary" type="submit" style={{ alignSelf: "flex-start" }}>Enregistrer</button>
    </form>
  );
}

function Users() {
  const run = useRun();
  const { me } = useApp();
  const { data, error, reload } = useLoad(() => api.get("/admin/users"), []);
  const [form, setForm] = useState(null);
  const [pw, setPw] = useState(null);
  const create = async (e) => {
    e.preventDefault();
    if (await run(() => api.post("/admin/users", form), "Utilisateur créé")) { setForm(null); reload(); }
  };
  const patch = async (u, body, msg) => { if (await run(() => api.patch(`/admin/users/${u.id}`, body), msg)) reload(); };
  if (!data) return <Loading error={error} />;
  return (
    <div className="card stack">
      <div className="row"><h2 className="grow">Utilisateurs</h2><button type="button" className="btn small" onClick={() => setForm({ email: "", name: "", password: "", is_admin: false })}><Icon name="plus" size={14} />Ajouter</button></div>
      <p className="small muted" style={{ margin: 0 }}>Tous les utilisateurs voient tous les projets et peuvent publier. Seuls les administrateurs configurent les applications des réseaux.</p>
      <div className="table-wrap"><table>
        <thead><tr><th>Nom</th><th>Adresse</th><th>Rôle</th><th /></tr></thead>
        <tbody>{data.map((u) => (
          <tr key={u.id} style={{ opacity: u.active ? 1 : 0.55 }}>
            <td>{u.name || "—"}</td><td>{u.email}</td><td>{u.is_admin ? "Administrateur" : "Membre"}{!u.active && " (désactivé)"}</td>
            <td><div className="row" style={{ justifyContent: "flex-end", gap: 6 }}>
              {u.id !== me.id && <button type="button" className="btn small" onClick={() => patch(u, { is_admin: !u.is_admin }, "Rôle changé")}>{u.is_admin ? "Rendre membre" : "Rendre admin"}</button>}
              {u.id !== me.id && <button type="button" className="btn small" onClick={() => patch(u, { active: !u.active }, u.active ? "Compte désactivé" : "Compte réactivé")}>{u.active ? "Désactiver" : "Réactiver"}</button>}
              <button type="button" className="btn small" onClick={() => setPw({ u, password: "" })}>Mot de passe</button>
            </div></td>
          </tr>
        ))}</tbody>
      </table></div>
      {form && (
        <Dialog title="Nouvel utilisateur" onClose={() => setForm(null)}>
          <form className="stack" onSubmit={create}>
            <Field label="Nom"><input id="u-name" className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Adresse e-mail"><input id="u-email" className="input" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="Mot de passe provisoire (10 caractères minimum)"><input id="u-pw" className="input" type="password" required minLength={10} autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
            <label className="row small"><input type="checkbox" checked={form.is_admin} onChange={(e) => setForm({ ...form, is_admin: e.target.checked })} />Administrateur</label>
            <div className="dialog-foot"><button type="button" className="btn" onClick={() => setForm(null)}>Annuler</button><button className="btn primary" type="submit">Créer</button></div>
          </form>
        </Dialog>
      )}
      {pw && (
        <Dialog title={`Nouveau mot de passe pour ${pw.u.email}`} onClose={() => setPw(null)}>
          <form className="stack" onSubmit={async (e) => { e.preventDefault(); await patch(pw.u, { password: pw.password }, "Mot de passe changé ; ses sessions sont fermées"); setPw(null); }}>
            <Field label="Mot de passe (10 caractères minimum)"><input id="u-newpw" className="input" type="password" required minLength={10} autoComplete="new-password" value={pw.password} onChange={(e) => setPw({ ...pw, password: e.target.value })} /></Field>
            <div className="dialog-foot"><button type="button" className="btn" onClick={() => setPw(null)}>Annuler</button><button className="btn primary" type="submit">Enregistrer</button></div>
          </form>
        </Dialog>
      )}
    </div>
  );
}

export default function Admin() {
  const apps = useLoad(() => api.get("/admin/apps"), []);
  const status = useLoad(() => api.get("/admin/status"), []);
  if (!apps.data || !status.data) return <Loading error={apps.error || status.error} />;
  const s = status.data;
  return (
    <>
      <div className="page-head">
        <div><h1>Administration</h1><p>Tamtam {s.version} · adresse publique <span className="mono">{s.public_url}</span></p></div>
      </div>
      {s.simulation && <div className="notice warn" style={{ marginBottom: 14 }}>Mode simulation actif (variable SIMULATION) : les comptes de démonstration publient pour de faux. À désactiver en production.</div>}
      <div className="kpis" style={{ marginBottom: 16 }}>
        <div className="card kpi"><b className="mono">{s.projects}</b><span>projets</span></div>
        <div className="card kpi"><b className="mono">{s.accounts}</b><span>comptes connectés{s.accounts_problem ? ` (${s.accounts_problem} à reconnecter)` : ""}</span></div>
        <div className="card kpi"><b className="mono">{s.posts}</b><span>posts</span></div>
        <div className="card kpi"><b className="mono">{(s.media_bytes / 1048576).toFixed(0)} Mo</b><span>{s.media} médias stockés</span></div>
      </div>
      <h2 style={{ margin: "8px 0 4px" }}>Applications des réseaux</h2>
      <p className="muted" style={{ margin: "0 0 12px", maxWidth: "75ch" }}>Pour publier, Tamtam a besoin d'une « application développeur » sur chaque réseau. Créez-la une fois, puis saisissez ici ses identifiants : ils sont chiffrés en base et ne réapparaissent jamais en clair.</p>
      <div className="accounts" style={{ marginBottom: 20 }}>
        {apps.data.apps.map((a) => <AppCard key={a.provider} app={a} onSaved={apps.reload} />)}
      </div>
      <Users />
    </>
  );
}
