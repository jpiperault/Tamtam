import React, { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { problems, textLength, toLocalInput, warnings, withUtm } from "../rules.js";
import { Chip, Dialog, Icon, Loading, NETWORKS, Net, ORDER, Seg, useRun, useToast } from "../ui.jsx";

const byNet = (a, b) => ORDER.indexOf(a.platform) - ORDER.indexOf(b.platform);

function MediaPicker({ projectId, chosen, onPick, onClose }) {
  const [list, setList] = useState(null);
  useEffect(() => {
    api.get(`/projects/${projectId}/media`).then(setList).catch(() => setList([]));
  }, [projectId]);
  return (
    <Dialog title="Médiathèque du projet" onClose={onClose}>
      {!list ? <Loading /> : list.length === 0 ? <div className="empty">Aucun média envoyé pour ce projet.</div> : (
        <div className="media-strip">
          {list.map((m) => (
            <button key={m.id} type="button" className="thumb" style={{ padding: 0, outline: chosen.some((c) => c.id === m.id) ? "3px solid var(--accent)" : undefined }}
              onClick={() => onPick(m)} title={m.filename}>
              {m.kind === "video" ? <video src={m.url} muted preload="metadata" /> : <img src={m.url} alt={m.filename} />}
              <span className="kind">{m.kind === "video" ? "vidéo" : "image"}</span>
            </button>
          ))}
        </div>
      )}
    </Dialog>
  );
}

function Preview({ account, text, media, link, project }) {
  const name = account.name || project.name;
  const handle = account.handle || name;
  const first = media[0];
  const img = (cls) => first && (first.kind === "video"
    ? <video className={`media ${cls}`} src={first.url} muted preload="metadata" />
    : <img className={`media ${cls}`} src={first.url} alt="" />);
  const cut = (t, n) => (t.length > n ? <>{t.slice(0, n)}<span className="more">… plus</span></> : t);
  const av = account.avatar_url ? <img className="av" src={account.avatar_url} alt="" /> : <div className="av" />;
  switch (account.platform) {
    case "instagram":
      return (<div className="mock"><div className="who">{av}{handle}</div>{img("")}
        {media.length > 1 && <div className="small muted" style={{ padding: "4px 10px 0" }}>Carrousel de {media.length} médias</div>}
        <div className="txt"><b>{handle}</b> {cut(text, 125)}</div></div>);
    case "facebook":
      return (<div className="mock"><div className="who">{av}<div>{name}<br /><span>Page</span></div></div>
        <div className="txt">{text}{link && media.length ? `\n${link}` : ""}</div>{img("wide")}
        {link && !media.length && <div className="lnk"><b>{project.url.replace(/^https?:\/\//, "") || "votre site"}</b><br />{link}</div>}</div>);
    case "x":
      return (<div className="mock"><div className="who">{av}<div>{name} <span>@{handle}</span></div></div>
        <div className="txt">{text}{link ? `\n${link}` : ""}</div>{img("wide")}</div>);
    default:
      return (<div className="mock">{img("tall")}<div className="txt"><b>@{handle}</b> {cut(text, 150)}</div></div>);
  }
}

export default function Composer({ editId, copyId, date }) {
  const { project, projectId, rules } = useApp();
  const run = useRun();
  const toast = useToast();
  const [accounts, setAccounts] = useState(null);
  const [selected, setSelected] = useState([]);
  const [body, setBody] = useState("");
  const [overrides, setOverrides] = useState({});
  const [tab, setTab] = useState("all");
  const [media, setMedia] = useState([]);
  const [link, setLink] = useState(project.url || "");
  const [campaign, setCampaign] = useState("");
  const [fbShort, setFbShort] = useState(false);
  const [mode, setMode] = useState(date ? "at" : "now");
  const [when, setWhen] = useState(() => {
    if (date) return `${date}T10:00`;
    const d = new Date(Date.now() + 3600e3);
    d.setMinutes(0);
    return toLocalInput(d);
  });
  const [picker, setPicker] = useState(false);
  const [uploading, setUploading] = useState(0);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loadedProject, setLoadedProject] = useState(projectId);
  const fileRef = useRef();

  useEffect(() => {
    let cancel = false;
    (async () => {
      const accs = await api.get(`/projects/${projectId}/accounts`).catch(() => []);
      if (cancel) return;
      accs.sort(byNet);
      setAccounts(accs);
      const src = editId || copyId;
      if (src) {
        const p = await api.get(`/posts/${src}`).catch((e) => { toast(e.message, true); return null; });
        if (!p || cancel) return;
        setBody(p.body);
        setLink(p.link_url);
        setCampaign(p.campaign);
        setFbShort(Boolean(p.facebook_short_link));
        setMedia(p.media);
        const ids = p.targets.map((t) => t.social_account_id).filter(Boolean);
        setSelected(ids);
        const ov = {};
        p.targets.forEach((t) => { if (t.body_override != null && t.social_account_id) ov[t.social_account_id] = t.body_override; });
        setOverrides(ov);
        if (editId) {
          if (p.status === "draft") setMode(p.scheduled_at ? "at" : "draft");
          else setMode("at");
          if (p.scheduled_at) setWhen(toLocalInput(new Date(p.scheduled_at)));
        }
        setLoadedProject(p.project_id);
      } else {
        setSelected(accs.filter((a) => a.status === "ok").map((a) => a.id));
        setLoadedProject(projectId);
        setMedia([]);
        setOverrides({});
        setTab("all");
      }
    })();
    return () => { cancel = true; };
  }, [projectId, editId, copyId, toast]);

  const chosen = useMemo(() => (accounts || []).filter((a) => selected.includes(a.id)), [accounts, selected]);
  const kinds = media.map((m) => m.kind);
  const textFor = (id) => (overrides[id] ?? body);
  const hasLink = Boolean(link.trim());
  const shortLink = `${rules.public_url}/l/…`;
  const hasFacebook = chosen.some((a) => a.platform === "facebook");
  const linkFor = (platform) => {
    if (!hasLink || !rules.rules[platform].link_in_text) return "";
    if (platform === "facebook" && !fbShort) return withUtm(link.trim(), "facebook", campaign.trim()) || link.trim();
    return shortLink;
  };
  const issues = useMemo(() => {
    const out = [];
    chosen.forEach((a) => out.push(...problems(rules, a.platform, textFor(a.id), kinds, hasLink)));
    return [...new Set(out)];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chosen, body, overrides, media, link, rules]);
  const notes = useMemo(() => [...new Set(chosen.flatMap((a) => warnings(a.platform, kinds, a, hasLink)))], [chosen, media]); // eslint-disable-line

  if (!accounts) return <Loading />;
  if (loadedProject !== projectId) {
    return <div className="notice warn">Ce post appartient à un autre projet. Choisissez ce projet dans la barre latérale pour le modifier.</div>;
  }

  const toggle = (a) => {
    setSelected((s) => (s.includes(a.id) ? s.filter((x) => x !== a.id) : [...s, a.id]));
    if (tab === a.id) setTab("all");
  };
  const upload = async (files) => {
    for (const f of files) {
      setUploading((n) => n + 1);
      const m = await run(() => api.upload(`/projects/${projectId}/media`, f));
      setUploading((n) => n - 1);
      if (m) setMedia((cur) => [...cur, m]);
    }
  };
  const editText = (v) => {
    if (tab === "all") setBody(v);
    else setOverrides((o) => ({ ...o, [tab]: v }));
  };
  const resetOverride = () => setOverrides((o) => {
    const n = { ...o };
    delete n[tab];
    return n;
  });

  const save = async (asDraft) => {
    const m = asDraft ? "draft" : mode;
    const payload = {
      project_id: projectId, body, account_ids: selected, media_ids: media.map((x) => x.id),
      overrides: Object.fromEntries(Object.entries(overrides).filter(([k]) => selected.includes(Number(k))).map(([k, v]) => [String(k), v])),
      link_url: link.trim(), campaign: campaign.trim(), facebook_short_link: fbShort, mode: m,
      scheduled_at: m === "at" || (m === "draft" && mode === "at") ? new Date(when).toISOString() : null,
    };
    setBusy(true);
    const r = await run(() => (editId ? api.put(`/posts/${editId}`, payload) : api.post("/posts", payload)),
      m === "draft" ? "Brouillon enregistré" : m === "now" ? "Envoi lancé : suivez-le dans Publications" : "Post programmé");
    setBusy(false);
    if (r) window.location.hash = m === "draft" ? "#/?status=draft" : "#/";
  };

  const tabs = [["all", "Texte commun"], ...chosen.map((a) => [a.id, `${NETWORKS[a.platform].label}${overrides[a.id] != null ? " •" : ""}`])];
  const tabAccount = chosen.find((a) => a.id === tab);
  return (
    <>
      <div className="page-head">
        <div>
          <h1>{editId ? "Modifier le post" : "Nouveau post"}</h1>
          <p>{project.name} · un message, chaque réseau dans son format.</p>
        </div>
      </div>
      {accounts.length === 0 && (
        <div className="notice warn" style={{ marginBottom: 16 }}>
          Aucun compte connecté pour ce projet. <a href="#/comptes">Connecter un compte</a>
        </div>
      )}
      <div className="compose">
        <div className="card stack">
          <div className="field">
            <span className="label">Publier sur</span>
            <div className="targets">
              {accounts.map((a) => (
                <button key={a.id} type="button" className="target" aria-pressed={selected.includes(a.id)} onClick={() => toggle(a)}
                  title={a.status !== "ok" ? "Ce compte doit être reconnecté" : undefined}>
                  <Net platform={a.platform} />
                  <span>{NETWORKS[a.platform].label} <span className="sub">{a.handle ? `@${a.handle}` : a.name}</span></span>
                  {a.status !== "ok" && <Chip tone="bad">à reconnecter</Chip>}
                </button>
              ))}
              <a className="target" href="#/comptes" style={{ textDecoration: "none", color: "var(--muted)", paddingLeft: 12 }}>
                <Icon name="plus" size={16} /> Ajouter
              </a>
            </div>
          </div>

          <div className="field">
            <div className="tabs" role="tablist">
              {tabs.map(([k, l]) => (
                <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{l}</button>
              ))}
            </div>
            <textarea id="post-text" className="textarea" aria-label="Texte du post" value={tab === "all" ? body : textFor(tab)}
              onChange={(e) => editText(e.target.value)} placeholder="Qu'avez-vous à annoncer ?" />
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div className="meters">
                {chosen.map((a) => {
                  const n = textLength(rules, a.platform, textFor(a.id), hasLink);
                  const lim = rules.rules[a.platform].text;
                  return (
                    <span key={a.id} className={`meter${n > lim ? " over" : ""}`} title={NETWORKS[a.platform].label}>
                      <Net platform={a.platform} size="s" /><i><b style={{ width: `${Math.min(100, (n / Math.min(lim, 2200)) * 100)}%` }} /></i>
                      <span className="mono">{n}/{lim > 9999 ? "∞" : lim}</span>
                    </span>
                  );
                })}
              </div>
              <span className="small muted" style={{ fontWeight: 400 }}>
                {tab === "all" ? "Ouvrez l'onglet d'un réseau pour adapter le texte à ce réseau seulement."
                  : overrides[tab] != null ? <>Texte adapté pour {NETWORKS[tabAccount?.platform]?.label}. <button type="button" className="btn ghost small" onClick={resetOverride}>Revenir au texte commun</button></>
                    : "Utilise le texte commun. Tapez pour l'adapter."}
              </span>
            </div>
          </div>

          <div className="field">
            <span className="label">Médias</span>
            <div className="media-strip"
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); upload([...e.dataTransfer.files]); }}>
              {media.map((m) => (
                <div key={m.id} className="thumb">
                  {m.kind === "video" ? <video src={m.url} muted preload="metadata" /> : <img src={m.url} alt={m.filename || ""} />}
                  <span className="kind">{m.kind === "video" ? "vidéo" : "image"}</span>
                  <button type="button" className="x" aria-label="Retirer ce média" onClick={() => setMedia((c) => c.filter((x) => x.id !== m.id))}>
                    <Icon name="close" size={12} stroke={3} />
                  </button>
                </div>
              ))}
              <button type="button" className={`drop${over ? " over" : ""}`} onClick={() => fileRef.current.click()}>
                {uploading ? "Envoi…" : <span><Icon name="upload" /><br />Ajouter ou déposer</span>}
              </button>
              <button type="button" className="drop" onClick={() => setPicker(true)}><span><Icon name="image" /><br />Médiathèque</span></button>
              <input ref={fileRef} type="file" accept="image/*,video/mp4,video/quicktime" multiple hidden
                onChange={(e) => { upload([...e.target.files]); e.target.value = ""; }} />
            </div>
            <span className="small muted" style={{ fontWeight: 400 }}>Images converties en JPEG (2048 px au plus) ; vidéos MP4 ou MOV. Instagram et TikTok exigent un média.</span>
          </div>

          <div className="grid2">
            <label className="field">Lien à promouvoir
              <input id="post-link" className="input" type="url" value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://" />
            </label>
            <label className="field">Campagne (pour les statistiques)
              <input id="post-campaign" className="input" value={campaign} onChange={(e) => setCampaign(e.target.value)} placeholder="lancement-v2" />
            </label>
          </div>
          {hasLink && (
            <div className="utm">
              Lien court ajouté au post sur X{fbShort ? " et Facebook" : ""} : <span className="mono">{shortLink}</span>, un par réseau, pour compter les clics.
              <br />Il redirige vers : <span className="mono">{withUtm(link.trim(), "RESEAU", campaign.trim()) || "adresse invalide"}</span>
              {hasFacebook && (
                <label className="check" style={{ marginTop: 8 }}>
                  <input id="post-fb-short" type="checkbox" checked={fbShort} onChange={(e) => setFbShort(e.target.checked)} />
                  <span>Facebook : utiliser aussi le lien court suivi (compte les clics). Sinon, le lien direct vers votre page est publié.</span>
                </label>
              )}
            </div>
          )}

          <div className="field">
            <span className="label">Quand</span>
            <div className="row">
              <Seg label="Moment de publication" value={mode} onChange={setMode}
                options={[{ value: "now", label: "Maintenant" }, { value: "at", label: "Programmer" }]} />
              {mode === "at" && <input id="post-when" className="input" type="datetime-local" style={{ width: "auto" }} value={when} onChange={(e) => setWhen(e.target.value)} />}
            </div>
          </div>

          {issues.length > 0 && <div className="stack" style={{ gap: 6 }}>{issues.map((t) => <div key={t} className="notice danger"><Icon name="alert" size={16} />{t}</div>)}</div>}
          {notes.length > 0 && <div className="stack" style={{ gap: 6 }}>{notes.map((t) => <div key={t} className="notice warn"><Icon name="alert" size={16} />{t}</div>)}</div>}

          <div className="actions">
            <button type="button" className="btn" disabled={busy} onClick={() => save(true)}>Enregistrer le brouillon</button>
            <button type="button" className="btn primary" disabled={busy || issues.length > 0 || chosen.length === 0 || uploading > 0}
              onClick={() => save(false)}>{mode === "now" ? `Publier sur ${chosen.length} compte${chosen.length > 1 ? "s" : ""}` : "Programmer"}</button>
          </div>
        </div>

        <div className="previews">
          {chosen.length === 0 ? <div className="card empty">Choisissez au moins un compte pour voir l'aperçu.</div>
            : chosen.map((a) => {
              const t = textFor(a.id);
              const bad = problems(rules, a.platform, t, kinds, hasLink).length > 0;
              return (
                <div key={a.id} className="card" style={{ padding: 14 }}>
                  <div className="pv-head"><Net platform={a.platform} />{NETWORKS[a.platform].label}
                    {bad ? <Chip tone="bad">À corriger</Chip> : <Chip tone="ok">Prêt</Chip>}</div>
                  <Preview account={a} text={t} media={media} project={project}
                    link={linkFor(a.platform)} />
                </div>
              );
            })}
        </div>
      </div>
      {picker && (
        <MediaPicker projectId={projectId} chosen={media} onClose={() => setPicker(false)}
          onPick={(m) => setMedia((c) => (c.some((x) => x.id === m.id) ? c.filter((x) => x.id !== m.id) : [...c, m]))} />
      )}
    </>
  );
}
