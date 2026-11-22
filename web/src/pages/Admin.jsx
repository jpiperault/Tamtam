import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Chip, Dialog, Field, Icon, Loading, useLoad, useRun, useToast } from "../ui.jsx";

const GUIDES = {
  meta: ["Facebook : une Page (pas un profil). Instagram : un compte professionnel relié à cette Page.",
    "developers.facebook.com → Mes apps → Créer une app, avec les cas d'utilisation « Gérer tout sur votre Page » et « Gérer les messages et le contenu sur Instagram » (une app à part si votre app a déjà « Facebook Login »).",
    "Personnaliser → Ajouter : pages_manage_posts et pages_read_engagement ; côté Instagram, configuration « API avec Facebook Login », puis instagram_basic et instagram_content_publish (pas les instagram_business_…).",
    "Paramètres de l'app → Général : le domaine de Tamtam dans « Domaines de l'app » et « Ajouter une plateforme » → Site web avec l'adresse de Tamtam. Enregistrer.",
    "Facebook Login for Business → Paramètres : collez l'adresse ci-dessous dans « URI de redirection OAuth valides », appuyez sur Entrée, puis Enregistrer.",
    "Copiez ici l'identifiant de l'app et la clé secrète (Paramètres de l'app → Général). Guide détaillé et messages d'erreur : page Aide, « Configurer Meta »."],
  x: ["Créez un projet et une app sur developer.x.com.",
    "Dans « User authentication settings » : OAuth 2.0, type « Web App, Automated App or Bot », droits Read and write.",
    "Collez l'adresse de retour ci-dessous comme Callback URI, puis copiez le Client ID et le Client Secret OAuth 2.0.",
    "Vérifiez que votre offre d'accès à l'API permet de publier."],
  tiktok: ["Créez une app sur developers.tiktok.com et ajoutez Login Kit et Content Posting API (Direct Post activé).",
    "Collez l'adresse de retour ci-dessous comme Redirect URI ; copiez le Client key et le Client secret.",
    "Pour les carrousels photo, vérifiez le domaine de Tamtam (URL properties) dans le portail.",
    "Soumettez l'app à l'audit TikTok pour publier en public ; avant l'audit, les posts sont privés."],
  threads: ["Threads : un compte Threads (relié à Instagram ou non). Pas besoin de Page Facebook.",
    "developers.facebook.com → Créer une app avec le cas d'utilisation « Accéder à l'API Threads » (une app à part de celle de Facebook/Instagram).",
    "Cas d'utilisation → Personnaliser : ajoutez threads_basic et threads_content_publish (et threads_manage_insights pour les statistiques).",
    "Paramètres de Threads : collez l'adresse ci-dessous dans « URL de rappel de redirection » (et dans les URL de désinstallation et de suppression si demandé).",
    "Copiez ici l'identifiant et la clé secrète de l'app Threads (Paramètres de l'app → Général : « ID de l'app Threads »). En mode développement, ajoutez votre compte Threads comme testeur."],
  linkedin: ["linkedin.com/developers → Create app (il faut une Page LinkedIn de l'entreprise pour créer l'app ; elle doit la vérifier).",
    "Onglet Products : ajoutez « Sign In with LinkedIn using OpenID Connect » et « Share on LinkedIn » (libre-service, immédiat).",
    "Onglet Auth : collez l'adresse ci-dessous dans « Authorized redirect URLs », puis copiez le Client ID et le Primary Client Secret.",
    "Publier sur une Page d'entreprise demande en plus la « Community Management API », validée par LinkedIn sur dossier ; puis cochez l'option « Pages LinkedIn » plus bas.",
    "LinkedIn ne renouvelle pas l'autorisation : reconnectez le compte tous les 60 jours (Tamtam prévient 7 jours avant)."],
  google: ["console.cloud.google.com → Créer un projet → API et services → Bibliothèque : activez « YouTube Data API v3 ».",
    "Écran de consentement OAuth : type Externe, ajoutez votre adresse comme utilisateur test (ou publiez l'app pour éviter une reconnexion chaque semaine).",
    "Identifiants → Créer un ID client OAuth → Application Web ; collez l'adresse ci-dessous dans « URI de redirection autorisés ».",
    "Copiez ici l'ID client et le code secret du client. Quota : 100 envois de vidéos par jour et par projet."],
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
      <Field label={app.provider === "tiktok" ? "Client key" : app.provider === "meta" ? "Identifiant de l'app (App ID)" : app.provider === "threads" ? "ID de l'app Threads" : "Client ID (OAuth 2.0)"}>
        <input id={`cid-${app.provider}`} className="input mono" value={cid} onChange={(e) => setCid(e.target.value)} autoComplete="off" />
      </Field>
      <Field label={`${app.provider === "meta" ? "Clé secrète (App Secret)" : app.provider === "threads" ? "Clé secrète de l'app Threads" : "Client secret"}${app.has_secret ? " · enregistré, laissez vide pour le garder" : ""}`}>
        <input id={`sec-${app.provider}`} className="input mono" type="password" value={secret} onChange={(e) => setSecret(e.target.value)} autoComplete="new-password" />
      </Field>
      <button className="btn primary" type="submit" style={{ alignSelf: "flex-start" }}>Enregistrer</button>
    </form>
  );
}

function ClaudeCard() {
  const run = useRun();
  const toast = useToast();
  const { data, error, reload } = useLoad(() => api.get("/admin/ai"), []);
  const [key, setKey] = useState("");
  const [model, setModel] = useState(null);
  const [limit, setLimit] = useState(null);
  const [testing, setTesting] = useState(false);
  if (!data) return <Loading error={error} />;
  const m = model ?? data.model;
  const l = limit ?? data.daily_limit;
  const save = async (e) => {
    e.preventDefault();
    const body = { model: m, daily_limit: Number(l) || 0 };
    if (key.trim()) body.api_key = key.trim();
    if (await run(() => api.put("/admin/ai", body), "Réglages de Claude enregistrés")) { setKey(""); reload(); }
  };
  const remove = async () => { if (await run(() => api.put("/admin/ai", { model: m, daily_limit: Number(l) || 0, api_key: "" }), "Clé effacée")) reload(); };
  const test = async () => {
    setTesting(true);
    const r = await run(() => api.post("/admin/ai/test"));
    setTesting(false);
    if (r) toast(`Clé valide : ${r.model} a répondu`);
  };
  const models = data.models.some((x) => x.id === m) ? data.models : [...data.models, { id: m, label: m }];
  return (
    <form className="card stack" onSubmit={save} style={{ marginBottom: 20 }}>
      <div className="row"><h2 className="grow">Claude</h2>
        {data.has_key ? <Chip tone="ok">Configuré</Chip> : <Chip tone="warn">À configurer</Chip>}</div>
      <ol className="small" style={{ margin: 0, paddingLeft: 18 }}>
        <li>Sur console.anthropic.com : créez un compte, ajoutez du crédit (Billing), puis API Keys → Create Key.</li>
        <li>Collez la clé ci-dessous (elle commence par sk-ant-) et enregistrez, puis « Tester la clé ».</li>
        <li>Chaque rédaction est facturée par Anthropic sur ce compte (quelques centimes au plus avec Opus).</li>
      </ol>
      <Field label={`Clé API${data.has_key ? " · enregistrée, laissez vide pour la garder" : ""}`}>
        <input id="ai-key" className="input mono" type="password" value={key} onChange={(e) => setKey(e.target.value)} autoComplete="new-password" placeholder="sk-ant-…" />
      </Field>
      <div className="grid2">
        <Field label="Modèle">
          <select id="ai-model" className="input" value={m} onChange={(e) => setModel(e.target.value)}>
            {models.map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
          </select>
        </Field>
        <Field label="Rédactions par jour au plus (tous utilisateurs)">
          <input id="ai-limit" className="input" type="number" min={0} max={10000} value={l} onChange={(e) => setLimit(e.target.value)} />
        </Field>
      </div>
      <p className="small muted" style={{ margin: 0 }}>Aujourd'hui : {data.used_today} rédaction{data.used_today > 1 ? "s" : ""}. Ce mois-ci : {data.month.calls} rédaction{data.month.calls > 1 ? "s" : ""}, {Number(data.month.input_tokens).toLocaleString("fr-FR")} jetons envoyés et {Number(data.month.output_tokens).toLocaleString("fr-FR")} reçus.</p>
      <div className="row" style={{ gap: 8 }}>
        <button className="btn primary" type="submit">Enregistrer</button>
        {data.has_key && <button type="button" className="btn" disabled={testing} onClick={test}>{testing ? "Test en cours…" : "Tester la clé"}</button>}
        {data.has_key && <button type="button" className="btn" onClick={remove}>Effacer la clé</button>}
      </div>
    </form>
  );
}

function LegalCard() {
  const run = useRun();
  const { data, error, reload } = useLoad(() => api.get("/admin/legal"), []);
  const [f, setF] = useState(null);
  if (!data) return <Loading error={error} />;
  const v = f ?? { operator: data.operator, contact: data.contact };
  const save = async (e) => {
    e.preventDefault();
    if (await run(() => api.put("/admin/legal", v), "Pages légales mises à jour")) { setF(null); reload(); }
  };
  const done = data.operator && data.contact;
  return (
    <form className="card stack" onSubmit={save} style={{ marginBottom: 20 }}>
      <div className="row"><h2 className="grow">Pages légales</h2>{done ? <Chip tone="ok">Complètes</Chip> : <Chip tone="warn">À compléter</Chip>}</div>
      <p className="small muted" style={{ margin: 0 }}>Pages publiques demandées par TikTok, Meta, LinkedIn et Google lors de la validation des applications. Copiez leurs adresses dans les portails développeurs.</p>
      <div className="grid2">
        <Field label="Éditeur (votre nom ou celui de votre société)"><input id="legal-operator" className="input" maxLength={200} value={v.operator} onChange={(e) => setF({ ...v, operator: e.target.value })} /></Field>
        <Field label="Contact (adresse e-mail)"><input id="legal-contact" className="input" maxLength={200} value={v.contact} onChange={(e) => setF({ ...v, contact: e.target.value })} /></Field>
      </div>
      <div className="stack" style={{ gap: 6 }}>
        <span className="small">Politique de confidentialité (FR / EN)</span>
        <Copy text={data.urls.privacy_fr} /><Copy text={data.urls.privacy_en} />
        <span className="small">Conditions d'utilisation (FR / EN)</span>
        <Copy text={data.urls.terms_fr} /><Copy text={data.urls.terms_en} />
      </div>
      <button className="btn primary" type="submit" style={{ alignSelf: "flex-start" }}>Enregistrer</button>
    </form>
  );
}

function TelegramCard() {
  const run = useRun();
  const toast = useToast();
  const { data, error, reload } = useLoad(() => api.get("/admin/telegram"), []);
  const [token, setToken] = useState("");
  const [found, setFound] = useState(null);
  const [busy, setBusy] = useState(false);
  if (!data) return <Loading error={error} />;
  const prefs = { failures: data.failures, accounts: data.accounts, success: data.success, report: data.report, approval: data.approval, inbox: data.inbox };
  const put = async (body, msg) => { const r = await run(() => api.put("/admin/telegram", { ...prefs, ...body }), msg); if (r) reload(); return r; };
  const saveToken = async (e) => { e.preventDefault(); if (await put({ token: token.trim() }, "Bot enregistré")) setToken(""); };
  const discover = async () => {
    setBusy(true);
    const r = await run(() => api.post("/admin/telegram/discover"));
    setBusy(false);
    if (r) { setFound(r.chats); if (!r.chats.length) toast("Aucune conversation : envoyez d'abord /start au bot dans Telegram", true); }
  };
  const isOn = (c) => data.chats.some((x) => x.id === c.id);
  const toggleChat = (c) => put({ chats: isOn(c) ? data.chats.filter((x) => x.id !== c.id) : [...data.chats, c] }, isOn(c) ? "Destinataire retiré" : "Destinataire ajouté");
  const test = async () => { const r = await run(() => api.post("/admin/telegram/test")); if (r) toast(`Message de test envoyé (${r.sent})`); };
  const list = [...data.chats, ...(found || []).filter((c) => !isOn(c))];
  return (
    <div className="card stack" style={{ marginBottom: 20 }}>
      <div className="row"><h2 className="grow">Alertes Telegram</h2>
        {data.has_token && data.chats.length ? <Chip tone="ok">Actives</Chip> : <Chip tone="warn">À configurer</Chip>}</div>
      <ol className="small" style={{ margin: 0, paddingLeft: 18 }}>
        <li>Dans Telegram, ouvrez <b>@BotFather</b>, envoyez <span className="mono">/newbot</span> et choisissez un nom : il vous donne un jeton.</li>
        <li>Collez le jeton ci-dessous et enregistrez.</li>
        <li>Ouvrez votre bot{data.bot ? <> (<a href={`https://t.me/${data.bot}`} target="_blank" rel="noreferrer">@{data.bot}</a>)</> : ""} et envoyez-lui <span className="mono">/start</span>, ou ajoutez-le à un groupe.</li>
        <li>« Chercher les conversations », cochez les destinataires, puis « Envoyer un test ».</li>
      </ol>
      <form className="row" style={{ gap: 8, alignItems: "flex-end" }} onSubmit={saveToken}>
        <Field label={`Jeton du bot${data.has_token ? ` · @${data.bot} enregistré, laissez vide pour le garder` : ""}`} className="grow">
          <input id="tg-token" className="input mono" type="password" autoComplete="new-password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="123456:ABC…" />
        </Field>
        <button className="btn primary" type="submit" disabled={!token.trim()}>Enregistrer</button>
        {data.has_token && <button type="button" className="btn" onClick={() => put({ token: "" }, "Bot retiré")}>Retirer</button>}
      </form>
      {data.has_token && <>
        <div className="row" style={{ gap: 8 }}>
          <button type="button" className="btn" disabled={busy} onClick={discover}><Icon name="search" size={14} />{busy ? "Recherche…" : "Chercher les conversations"}</button>
          {data.chats.length > 0 && <button type="button" className="btn" onClick={test}><Icon name="share" size={14} />Envoyer un test</button>}
        </div>
        {list.length > 0 && (
          <div className="stack" style={{ gap: 4 }}>
            <span className="label">Destinataires</span>
            {list.map((c) => <label key={c.id} className="check"><input type="checkbox" checked={isOn(c)} onChange={() => toggleChat(c)} /><span>{c.name} <span className="muted mono small">{c.id}</span></span></label>)}
          </div>
        )}
        <div className="stack" style={{ gap: 4 }}>
          <span className="label">Prévenir quand</span>
          <label className="check"><input id="tg-failures" type="checkbox" checked={data.failures} onChange={(e) => put({ failures: e.target.checked }, "Préférence enregistrée")} /><span>un post échoue (après les nouveaux essais automatiques)</span></label>
          <label className="check"><input type="checkbox" checked={data.accounts} onChange={(e) => put({ accounts: e.target.checked }, "Préférence enregistrée")} /><span>un compte doit être reconnecté (vérifié aussi chaque jour)</span></label>
          <label className="check"><input type="checkbox" checked={data.success} onChange={(e) => put({ success: e.target.checked }, "Préférence enregistrée")} /><span>un post est publié</span></label>
          <label className="check"><input type="checkbox" checked={data.report} onChange={(e) => put({ report: e.target.checked }, "Préférence enregistrée")} /><span>le rapport du lundi est prêt (si activé dans Statistiques des réseaux)</span></label>
          <label className="check"><input type="checkbox" checked={data.approval} onChange={(e) => put({ approval: e.target.checked }, "Préférence enregistrée")} /><span>un membre propose un post à valider (validation à deux)</span></label>
          <label className="check"><input type="checkbox" checked={data.inbox} onChange={(e) => put({ inbox: e.target.checked }, "Préférence enregistrée")} /><span>un nouveau commentaire arrive dans la boîte de réception</span></label>
        </div>
      </>}
    </div>
  );
}

function StatsCard() {
  const run = useRun();
  const { data: loaded, error } = useLoad(() => api.get("/admin/stats"), []);
  const [local, setLocal] = useState(null);
  const data = local || loaded;
  if (!data) return <Loading error={error} />;
  const save = async (patch) => {
    setLocal({ ...data, ...patch });   // la case change tout de suite ; annulée si l'enregistrement échoue
    const r = await run(() => api.put("/admin/stats", { scopes_meta: data.scopes_meta, scopes_tiktok: data.scopes_tiktok, scopes_threads: data.scopes_threads, linkedin_pages: data.linkedin_pages, report_weekly: data.report_weekly, ...patch }), "Réglage enregistré");
    setLocal(r || data);
  };
  return (
    <div className="card stack" id="stats-card" style={{ marginBottom: 20 }}>
      <h2>Statistiques des réseaux</h2>
      <p className="small muted" style={{ margin: 0 }}>Tamtam relit toutes les 6 heures les chiffres des posts publiés depuis moins de 30 jours. Sans réglage, il lit ce que les permissions actuelles autorisent : J'aime, commentaires et partages sur Facebook et Instagram. Les vues et la portée demandent des permissions en plus.</p>
      <label className="check"><input id="stats-meta" type="checkbox" checked={data.scopes_meta} onChange={(e) => save({ scopes_meta: e.target.checked })} />
        <span><b>Meta : demander aussi la lecture des statistiques</b> (<span className="mono">{data.scopes.meta.join(", ")}</span>)<br />
          <span className="small muted">Ajoutez d'abord ces permissions à votre app Meta (cas d'utilisation Page et Instagram → Personnaliser), sinon la connexion échouera avec « Invalid Scopes ». Puis reconnectez les comptes Facebook et Instagram.</span></span></label>
      <label className="check"><input id="stats-tiktok" type="checkbox" checked={data.scopes_tiktok} onChange={(e) => save({ scopes_tiktok: e.target.checked })} />
        <span><b>TikTok : demander aussi la lecture des vidéos</b> (<span className="mono">{data.scopes.tiktok.join(", ")}</span>)<br />
          <span className="small muted">Ajoutez d'abord le produit « Display API » et la permission video.list à votre app TikTok (soumis à validation), puis reconnectez le compte. Les posts privés n'ont pas de statistiques.</span></span></label>
      <label className="check"><input id="stats-threads" type="checkbox" checked={data.scopes_threads} onChange={(e) => save({ scopes_threads: e.target.checked })} />
        <span><b>Threads : demander aussi la lecture des statistiques</b> (<span className="mono">{data.scopes.threads.join(", ")}</span>)<br />
          <span className="small muted">Ajoutez d'abord cette permission au cas d'utilisation Threads de l'app, puis reconnectez le compte.</span></span></label>
      <label className="check"><input id="opt-linkedin-pages" type="checkbox" checked={data.linkedin_pages} onChange={(e) => save({ linkedin_pages: e.target.checked })} />
        <span><b>LinkedIn : publier aussi sur les Pages d'entreprise</b> (<span className="mono">w_organization_social, r_organization_admin</span>)<br />
          <span className="small muted">Seulement si LinkedIn a validé votre app pour la Community Management API, sinon la connexion échouera. Puis reconnectez le compte : vos Pages apparaîtront à côté du profil.</span></span></label>
      <p className="small muted" style={{ margin: 0 }}>X : les chiffres sont lus avec la permission actuelle, mais X facture chaque lecture (quelques dixièmes de centime par post et par jour) : il faut des crédits sur votre compte développeur X.</p>
      <label className="check"><input id="stats-report" type="checkbox" checked={data.report_weekly} onChange={(e) => save({ report_weekly: e.target.checked })} />
        <span><b>Rapport de la semaine rédigé par Claude, chaque lundi matin</b><br />
          <span className="small muted">Pour chaque projet qui a publié dans la semaine. Visible dans Statistiques, envoyé aussi par Telegram si les alertes sont configurées. Compte pour une rédaction par projet.</span></span></label>
    </div>
  );
}

const INBOX_OPTS = [
  ["meta", "Facebook et Instagram", "Ajoutez d'abord ces permissions aux cas d'utilisation Page et Instagram de l'app Meta (validation Meta requise pour d'autres comptes que les testeurs)."],
  ["threads", "Threads", "Ajoutez-les au cas d'utilisation Threads de l'app."],
  ["google", "YouTube", "Rien à ajouter dans Google : la permission est demandée à la reconnexion. Répondre coûte 50 unités du quota quotidien (10 000)."],
  ["x", "X", "Aucune permission en plus, mais X facture chaque commentaire lu, ne remonte que les 7 derniers jours, et peut refuser les réponses automatiques (seulement si l'auteur vous a mentionné)."],
];

function InboxCard() {
  const run = useRun();
  const { data: loaded, error } = useLoad(() => api.get("/admin/inbox"), []);
  const [local, setLocal] = useState(null);
  const data = local || loaded;
  if (!data) return <Loading error={error} />;
  const save = async (patch) => {
    const next = { meta: data.meta, threads: data.threads, google: data.google, x: data.x, ...patch };
    setLocal({ ...data, ...patch });
    const r = await run(() => api.put("/admin/inbox", next), "Réglage enregistré");
    setLocal(r || data);
  };
  return (
    <div className="card stack" id="inbox-card" style={{ marginBottom: 20 }}>
      <h2>Boîte de réception (commentaires)</h2>
      <p className="small muted" style={{ margin: 0 }}>Bluesky est toujours relevé. Pour les autres réseaux, il faut des permissions de lecture et de réponse aux commentaires : cochez le réseau, puis reconnectez ses comptes. Si la permission n'est pas ajoutée à l'application développeur, la connexion échouera (« Invalid Scopes ») : décochez pour revenir en arrière. TikTok et LinkedIn ne permettent pas de lire les commentaires.</p>
      {INBOX_OPTS.map(([k, label, help]) => (
        <label key={k} className="check"><input id={`inbox-${k}`} type="checkbox" checked={data[k]} onChange={(e) => save({ [k]: e.target.checked })} />
          <span><b>{label}</b>{data.scopes[k]?.length ? <> (<span className="mono">{data.scopes[k].map((s) => s.replace("https://www.googleapis.com/auth/", "")).join(", ")}</span>)</> : null}<br />
            <span className="small muted">{help}</span></span></label>
      ))}
    </div>
  );
}

function Users() {
  const run = useRun();
  const { me } = useApp();
  const { data, error, reload } = useLoad(() => api.get("/admin/users"), []);
  const approval = useLoad(() => api.get("/admin/approval"), []);
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
      <p className="small muted" style={{ margin: 0 }}>Tous les utilisateurs voient tous les projets. Seuls les administrateurs configurent les applications des réseaux.</p>
      {approval.data && (
        <label className="check"><input id="opt-approval" type="checkbox" checked={approval.data.required}
          onChange={async (e) => { if (await run(() => api.put("/admin/approval", { required: e.target.checked }), "Réglage enregistré")) approval.reload(); }} />
          <span><b>Validation à deux</b> : les posts des membres attendent l'accord d'un administrateur avant de partir<br />
            <span className="small muted">Le membre écrit et programme comme d'habitude, puis « Envoyer pour validation ». Un administrateur valide (le post part à l'heure prévue, ou tout de suite si elle est passée) ou refuse avec un commentaire (le post redevient un brouillon). Les posts des administrateurs partent directement.</span></span></label>
      )}
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
      <LegalCard />
      <h2 style={{ margin: "8px 0 4px" }}>Rédaction avec Claude</h2>
      <p className="muted" style={{ margin: "0 0 12px", maxWidth: "75ch" }}>Dans « Nouveau post », le bouton « Rédiger avec Claude » propose un texte commun et une version par réseau, à partir de votre consigne et de la présentation du projet. Rien n'est publié sans votre validation.</p>
      <ClaudeCard />
      <StatsCard />
      <InboxCard />
      <TelegramCard />
      <Users />
    </>
  );
}
