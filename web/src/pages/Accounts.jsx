import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Chip, Dialog, Icon, Loading, NETWORKS, Net, useLoad, useRun, useToast } from "../ui.jsx";

const CARDS = [
  { platform: "instagram", provider: "meta", req: "Compte Instagram Professionnel (Business ou Créateur) relié à une Page Facebook. La connexion passe par Facebook." },
  { platform: "facebook", provider: "meta", req: "Publie sur une Page Facebook, pas sur un profil personnel. Une connexion Meta couvre Facebook et Instagram." },
  { platform: "x", provider: "x", req: "Tout compte X. L'accès à l'API X en écriture peut être payant selon l'offre de l'application développeur." },
  { platform: "tiktok", provider: "tiktok", req: "Tout compte TikTok. Tant que l'application n'a pas passé l'audit TikTok, les posts ne sont visibles que par vous." },
  { platform: "threads", provider: "threads", req: "Tout compte Threads. Se connecte avec l'application Threads (distincte de celle de Facebook et Instagram)." },
  { platform: "bluesky", provider: "bluesky", req: "Tout compte Bluesky, avec un « mot de passe d'application » (pas votre mot de passe habituel). Aucune application développeur à créer." },
  { platform: "linkedin", provider: "linkedin", req: "Publie sur votre profil LinkedIn ; sur une Page d'entreprise si l'option est activée dans Administration. À reconnecter tous les 60 jours." },
  { platform: "youtube", provider: "google", req: "Une chaîne YouTube. Publie des Shorts : vidéo verticale ou carrée de 3 minutes au plus." },
];

function BlueskyDialog({ projectId, onClose, onChoose }) {
  const [ident, setIdent] = useState("");
  const [pwd, setPwd] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const r = await api.post("/connect/bluesky/password", { project_id: projectId, identifier: ident, app_password: pwd });
      onChoose(r.choose);
    } catch (ex) {
      setErr(ex.message);
    }
    setBusy(false);
  };
  return (
    <Dialog title="Connecter Bluesky" onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <ol className="small" style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4 }}>
          <li>Dans Bluesky : <b>Réglages → Confidentialité et sécurité → Mots de passe d'application → Ajouter</b>. Nommez-le « Tamtam ». Laissez décochée l'option « messages privés ».</li>
          <li>Copiez le mot de passe affiché (de la forme <span className="mono">abcd-efgh-ijkl-mnop</span>) et collez-le ci-dessous.</li>
        </ol>
        <label className="field">Pseudo Bluesky
          <input id="bsky-id" className="input" required value={ident} onChange={(e) => setIdent(e.target.value)} placeholder="nom.bsky.social" autoComplete="off" />
        </label>
        <label className="field">Mot de passe d'application
          <input id="bsky-pwd" className="input mono" type="password" required value={pwd} onChange={(e) => setPwd(e.target.value)} autoComplete="new-password" />
        </label>
        <p className="small muted" style={{ margin: 0 }}>Tamtam ne garde pas ce mot de passe : il ouvre une session puis ne conserve que les jetons, chiffrés. Pour couper l'accès, supprimez le mot de passe d'application dans Bluesky.</p>
        {err && <div className="notice danger small"><Icon name="alert" size={16} />{err}</div>}
        <div className="dialog-foot"><button type="button" className="btn" onClick={onClose}>Annuler</button>
          <button type="submit" id="bsky-go" className="btn primary" disabled={busy}>{busy ? "Connexion…" : "Connecter"}</button></div>
      </form>
    </Dialog>
  );
}

function Chooser({ id, onDone }) {
  const run = useRun();
  const [data, setData] = useState(null);
  const [keys, setKeys] = useState([]);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get(`/connect/pending/${id}`).then((d) => { setData(d); setKeys(d.candidates.map((c) => c.key)); }).catch((e) => setErr(e.message));
  }, [id]);
  const close = () => onDone(false);
  const save = async () => {
    const r = await run(() => api.post(`/connect/pending/${id}`, { keys }));
    if (r) onDone(r.added);
  };
  return (
    <Dialog title="Comptes à rattacher" onClose={close}
      footer={data && <><button type="button" className="btn" onClick={close}>Annuler</button>
        <button type="button" className="btn primary" disabled={!keys.length} onClick={save}>Rattacher {keys.length} compte{keys.length > 1 ? "s" : ""}</button></>}>
      {err ? <div className="notice danger">{err}</div> : !data ? <Loading /> : (
        <>
          <p style={{ margin: 0 }}>Comptes trouvés pour le projet <b>{data.project.name}</b>. Décochez ceux qui ne le concernent pas.</p>
          <div className="acc-list">
            {data.candidates.map((c) => (
              <label key={c.key} className="acc-item" style={{ cursor: "pointer" }}>
                <input type="checkbox" checked={keys.includes(c.key)} style={{ accentColor: "var(--accent)" }}
                  onChange={(e) => setKeys((k) => (e.target.checked ? [...k, c.key] : k.filter((x) => x !== c.key)))} />
                <Net platform={c.platform} />
                <span className="grow"><b>{c.name || c.handle}</b>{c.handle && <span className="muted"> @{c.handle}</span>}
                  {c.detail && <span className="small muted"><br />Relié à la Page {c.detail}</span>}
                  {c.kind && <span className="small muted"><br />{c.kind === "page" ? "Page d'entreprise" : "Profil personnel"}</span>}</span>
                {c.simulated && <Chip tone="warn">démo</Chip>}
              </label>
            ))}
          </div>
        </>
      )}
    </Dialog>
  );
}

function AccountItem({ a, onChange }) {
  const run = useRun();
  const toast = useToast();
  const [confirm, setConfirm] = useState(false);
  const test = async () => {
    const r = await run(() => api.post(`/accounts/${a.id}/test`));
    if (r) {
      toast(r.message, !r.ok);
      onChange();
    }
  };
  const del = async () => { if (await run(() => api.del(`/accounts/${a.id}`), "Compte retiré de Tamtam")) onChange(); };
  return (
    <div className="acc-item">
      {a.avatar_url ? <img className="av" src={a.avatar_url} alt="" /> : <div className="av" />}
      <span className="grow"><b>{a.name || a.handle}</b>{a.handle && <span className="muted"> @{a.handle}</span>}
        {a.meta?.page_name && a.meta?.kind !== "page" && <span className="small muted"><br />Page {a.meta.page_name}</span>}
        {a.platform === "linkedin" && a.meta?.kind && <span className="small muted"><br />{a.meta.kind === "page" ? "Page d'entreprise" : "Profil personnel"}</span>}
        {a.expires_at && a.platform === "linkedin" && <span className="small muted"><br />Autorisation valable jusqu'au {new Date(a.expires_at).toLocaleDateString("fr-FR")}</span>}
        {a.last_error && <span className="err"><br />{a.last_error}</span>}</span>
      {a.simulated && <Chip tone="warn">démo</Chip>}
      {a.status === "ok" ? <Chip tone="ok">Connecté</Chip> : <Chip tone="bad">{a.status === "expired" ? "À reconnecter" : "Erreur"}</Chip>}
      <div className="row" style={{ width: "100%", justifyContent: "flex-end", gap: 6 }}>
        <button type="button" className="btn small" onClick={test}>Vérifier</button>
        {confirm ? <>
          <button type="button" className="btn small danger" onClick={del}>Confirmer le retrait</button>
          <button type="button" className="btn small" onClick={() => setConfirm(false)}>Annuler</button>
        </> : <button type="button" className="btn small" onClick={() => setConfirm(true)}>Retirer</button>}
      </div>
    </div>
  );
}

export default function Accounts({ params }) {
  const { projectId, project, me, refreshProjects } = useApp();
  const run = useRun();
  const toast = useToast();
  const { data, error, reload } = useLoad(() => api.get(`/projects/${projectId}/accounts`), [projectId]);
  const providers = useLoad(() => api.get("/connect/providers"), []);
  const [choose, setChoose] = useState(params.get("choose"));
  const [bsky, setBsky] = useState(false);
  const ok = params.get("ok");
  const err = params.get("err");

  const connect = async (provider, demo = false) => {
    if (provider === "bluesky" && !demo) { setBsky(true); return; }
    const r = await run(() => api.post(`/connect/${provider}/start`, { project_id: projectId, demo }));
    if (!r) return;
    if (r.url) window.location.href = r.url;
    else if (r.choose) setChoose(r.choose);
  };
  const done = (added) => {
    setChoose(null);
    window.history.replaceState(null, "", "#/comptes");
    if (added) toast(`${added} compte${added > 1 ? "s" : ""} rattaché${added > 1 ? "s" : ""}`);
    reload();
    refreshProjects();
  };
  if (!data || !providers.data) return <Loading error={error || providers.error} />;
  const prov = providers.data.providers;
  return (
    <>
      <div className="page-head">
        <div><h1>Comptes connectés</h1><p>{project.name} · la connexion se fait sur la page officielle de chaque réseau ; Tamtam ne voit jamais vos mots de passe.</p></div>
      </div>
      {ok && <div className="notice ok" style={{ marginBottom: 14 }}>{ok}</div>}
      {err && <div className="notice danger" style={{ marginBottom: 14 }}><Icon name="alert" size={16} />{err}</div>}
      <div className="accounts">
        {CARDS.map((c) => {
          const list = data.filter((a) => a.platform === c.platform);
          const configured = prov[c.provider].configured;
          return (
            <div key={c.platform} className="card stack">
              <div className="acc-top">
                <Net platform={c.platform} size="l" />
                <div className="grow"><h2>{NETWORKS[c.platform].label}</h2>
                  <span className="small muted">{list.length ? `${list.length} compte${list.length > 1 ? "s" : ""}` : "Aucun compte"}</span></div>
              </div>
              {list.length > 0 && <div className="acc-list">{list.map((a) => <AccountItem key={a.id} a={a} onChange={reload} />)}</div>}
              <div className="req">{c.req}</div>
              <div className="row">
                <button type="button" className="btn primary" disabled={!configured} onClick={() => connect(c.provider)}>
                  <Icon name="link" size={16} />{list.length ? "Connecter un autre compte" : `Connecter ${NETWORKS[c.platform].label}`}
                </button>
                {providers.data.simulation && <button type="button" className="btn" onClick={() => connect(c.provider, true)}>Compte de démonstration</button>}
              </div>
              {!configured && (
                <div className="notice info">
                  L'application {prov[c.provider].label} n'est pas encore configurée.
                  {me.is_admin ? <> <a href="#/admin">La configurer dans Administration</a></> : " Demandez à un administrateur de la configurer."}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {choose && <Chooser id={choose} onDone={done} />}
      {bsky && <BlueskyDialog projectId={projectId} onClose={() => setBsky(false)} onChoose={(id) => { setBsky(false); setChoose(id); }} />}
    </>
  );
}
