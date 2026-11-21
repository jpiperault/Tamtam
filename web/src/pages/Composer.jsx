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
const TONE_OPTIONS = [
  { value: "", label: "Selon le projet" }, { value: "enthousiaste", label: "Enthousiaste" },
  { value: "pro", label: "Pro" }, { value: "decontracte", label: "Décontracté" }, { value: "humour", label: "Humour" },
];

function ClaudeDialog({ projectId, project, platforms, currentText, kinds, mediaIds, hasLink, status, isAdmin, onApply, onClose }) {
  const [instructions, setInstructions] = useState("");
  const [showMedia, setShowMedia] = useState(true);
  const [tone, setTone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const ask = async () => {
    setBusy(true); setError("");
    try {
      setResult(await api.post("/ai/draft", { project_id: projectId, instructions, current_text: currentText, tone,
        platforms, media_kinds: kinds, has_link: hasLink, media_ids: showMedia ? mediaIds : [] }));
    } catch (e) {
      setError(e.message);
    }
    setBusy(false);
  };
  if (!status?.enabled) {
    return (
      <Dialog title="Rédiger avec Claude" onClose={onClose}>
        <p>Claude n'est pas encore configuré pour Tamtam : il faut une clé API Anthropic.</p>
        {isAdmin ? <a className="btn primary" href="#/admin" onClick={onClose}>Configurer dans Administration</a>
          : <p className="muted">Demandez à un administrateur de la saisir dans Administration.</p>}
      </Dialog>
    );
  }
  return (
    <Dialog title="Rédiger avec Claude" onClose={onClose}>
      {!result ? (
        <div className="stack">
          <label className="field">Que voulez-vous annoncer ?
            <textarea id="ai-instructions" className="textarea" style={{ minHeight: 110 }} maxLength={4000} value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Ex. : la version 2 sort aujourd'hui, avec le mode sombre et l'export PDF. Public : les étudiants." />
          </label>
          {currentText.trim() && <p className="small muted" style={{ margin: 0 }}>Votre texte actuel sera pris en compte : Claude l'améliore ou le réécrit selon la consigne.</p>}
          {!project.description?.trim() && <div className="notice warn small"><Icon name="alert" size={16} />Le projet n'a pas de présentation : Claude rédigera mieux si vous en ajoutez une (page Projets → Modifier).</div>}
          {mediaIds.length > 0 && (
            <label className="check small">
              <input id="ai-show-media" type="checkbox" checked={showMedia} onChange={(e) => setShowMedia(e.target.checked)} />
              <span>Montrer {mediaIds.length > 1 ? `les ${mediaIds.length} médias` : (kinds[0] === "video" ? "la vidéo" : "l'image")} à Claude pour que le texte colle à ce qu'on y voit{kinds.includes("video") ? " (quelques images extraites de la vidéo, sans le son)" : ""}.</span>
            </label>
          )}
          <div className="field"><span className="label">Ton</span><Seg label="Ton" value={tone} onChange={setTone} options={TONE_OPTIONS} /></div>
          <p className="small muted" style={{ margin: 0 }}>Réseaux : {platforms.map((p) => NETWORKS[p].label).join(", ")}.
            {status.simulated ? " Mode simulation : texte factice, sans appel à Claude." : ` ${status.used_today}/${status.daily_limit} rédactions aujourd'hui.`}</p>
          {error && <div className="notice danger"><Icon name="alert" size={16} />{error}</div>}
          <div className="dialog-foot">
            <button type="button" className="btn" onClick={onClose}>Annuler</button>
            <button type="button" className="btn primary" disabled={busy || (!instructions.trim() && !currentText.trim())} onClick={ask}>
              <Icon name="sparkle" size={16} />{busy ? "Claude rédige… (jusqu'à une minute)" : "Proposer un texte"}</button>
          </div>
        </div>
      ) : (
        <div className="stack">
          {result.note && <div className="notice warn small"><Icon name="alert" size={16} />{result.note}</div>}
          <div className="ai-out"><span className="label">Texte commun</span><div className="ai-text">{result.common}</div></div>
          {platforms.filter((p) => result.versions[p]).map((p) => (
            <div key={p} className="ai-out">
              <span className="label"><Net platform={p} size="s" /> {NETWORKS[p].label}
                {result.too_long.includes(p) && <Chip tone="bad">trop long</Chip>}</span>
              <div className="ai-text">{result.versions[p]}</div>
            </div>
          ))}
          <p className="small muted" style={{ margin: 0 }}>Relisez avant de publier : Claude peut se tromper. Vous pourrez tout modifier dans l'éditeur.</p>
          <div className="dialog-foot">
            <button type="button" className="btn" onClick={() => setResult(null)}><Icon name="refresh" size={16} />Recommencer</button>
            <button type="button" className="btn" onClick={() => onApply(result, false)}>Texte commun seulement</button>
            <button type="button" className="btn primary" onClick={() => onApply(result, true)}><Icon name="check" size={16} />Utiliser ces textes</button>
          </div>
        </div>
      )}
    </Dialog>
  );
}


export default function Composer({ editId, copyId, date }) {
  const { project, projectId, rules, me } = useApp();
  const run = useRun();
  const toast = useToast();
  const [accounts, setAccounts] = useState(null);
  const [selected, setSelected] = useState([]);
  const [body, setBody] = useState("");
  const [overrides, setOverrides] = useState({});
  const [tab, setTab] = useState("all");
  const [media, setMedia] = useState([]);
  const [claude, setClaude] = useState(false);
  const [aiStatus, setAiStatus] = useState(null);
  const [link, setLink] = useState("");
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

  const openClaude = async () => {
    setAiStatus(await api.get("/ai/status").catch(() => ({ enabled: false })));
    setClaude(true);
  };
  const applyClaude = (r, perNetwork) => {
    setBody(r.common);
    const ov = {};
    if (perNetwork) chosen.forEach((a) => { const v = r.versions[a.platform]; if (v && v !== r.common) ov[a.id] = v; });
    setOverrides(ov);
    setTab("all");
    setClaude(false);
    toast(perNetwork ? "Textes de Claude appliqués : relisez chaque onglet" : "Texte de Claude appliqué");
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
            <div className="row" style={{ alignItems: "flex-end", gap: 8 }}>
              <div className="tabs grow" role="tablist">
                {tabs.map(([k, l]) => (
                  <button key={k} type="button" role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{l}</button>
                ))}
              </div>
              <button type="button" id="btn-claude" className="btn small" disabled={chosen.length === 0}
                title={chosen.length === 0 ? "Choisissez d'abord un compte" : "Proposer un texte avec Claude"} onClick={openClaude}>
                <Icon name="sparkle" size={14} />Rédiger avec Claude</button>
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
            <label className="field">Lien à promouvoir (facultatif)
              <input id="post-link" className="input" type="url" value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://" />
              {!link.trim() && project.url && (
                <button type="button" className="btn ghost small" style={{ alignSelf: "flex-start" }} onClick={() => setLink(project.url)}>
                  <Icon name="link" size={14} />Ajouter l'adresse du projet</button>
              )}
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
      {claude && <ClaudeDialog projectId={projectId} project={project} platforms={[...new Set(chosen.map((a) => a.platform))]}
        currentText={body} kinds={kinds} mediaIds={media.map((m) => m.id)} hasLink={hasLink} status={aiStatus} isAdmin={me?.is_admin}
        onApply={applyClaude} onClose={() => setClaude(false)} />}
      {picker && (
        <MediaPicker projectId={projectId} chosen={media} onClose={() => setPicker(false)}
          onPick={(m) => setMedia((c) => (c.some((x) => x.id === m.id) ? c.filter((x) => x.id !== m.id) : [...c, m]))} />
      )}
    </>
  );
}
