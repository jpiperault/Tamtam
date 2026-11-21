import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Chip, Dialog, Icon, Loading, NETWORKS, Net, useLoad, useRun, useToast } from "../ui.jsx";

const CARDS = [
  { platform: "instagram", provider: "meta", req: "Compte Instagram Professionnel (Business ou Créateur) relié à une Page Facebook. La connexion passe par Facebook." },
  { platform: "facebook", provider: "meta", req: "Publie sur une Page Facebook, pas sur un profil personnel. Une connexion Meta couvre Facebook et Instagram." },
  { platform: "x", provider: "x", req: "Tout compte X. L'accès à l'API X en écriture peut être payant selon l'offre de l'application développeur." },
  { platform: "tiktok", provider: "tiktok", req: "Tout compte TikTok. Tant que l'application n'a pas passé l'audit TikTok, les posts ne sont visibles que par vous." },
];
const PRIVACY = {
  PUBLIC_TO_EVERYONE: "Tout le monde",
  MUTUAL_FOLLOW_FRIENDS: "Amis",
  FOLLOWER_OF_CREATOR: "Abonnés",
  SELF_ONLY: "Moi uniquement",
};

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
                  {c.detail && <span className="small muted"><br />Relié à la Page {c.detail}</span>}</span>
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
  const privacy = async (v) => { if (await run(() => api.patch(`/accounts/${a.id}`, { privacy: v }), "Visibilité enregistrée")) onChange(); };
  return (
    <div className="acc-item">
      {a.avatar_url ? <img className="av" src={a.avatar_url} alt="" /> : <div className="av" />}
      <span className="grow"><b>{a.name || a.handle}</b>{a.handle && <span className="muted"> @{a.handle}</span>}
        {a.meta?.page_name && <span className="small muted"><br />Page {a.meta.page_name}</span>}
        {a.last_error && <span className="err"><br />{a.last_error}</span>}</span>
      {a.simulated && <Chip tone="warn">démo</Chip>}
      {a.status === "ok" ? <Chip tone="ok">Connecté</Chip> : <Chip tone="bad">{a.status === "expired" ? "À reconnecter" : "Erreur"}</Chip>}
      <div className="row" style={{ width: "100%", justifyContent: "flex-end", gap: 6 }}>
        {a.platform === "tiktok" && (
          <label className="small muted row" style={{ gap: 6 }}>Visibilité
            <select className="select" style={{ width: "auto", padding: "4px 8px" }} value={a.meta?.privacy || "PUBLIC_TO_EVERYONE"} onChange={(e) => privacy(e.target.value)}>
              {Object.entries(PRIVACY).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </label>
        )}
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
  const ok = params.get("ok");
  const err = params.get("err");

  const connect = async (provider, demo = false) => {
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
    </>
  );
}
