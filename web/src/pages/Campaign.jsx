import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { fmtDateTime, problems, toLocalInput } from "../rules.js";
import { Chip, Icon, Loading, NETWORKS, Net, ORDER, Seg, useToast } from "../ui.jsx";

// Campagne de lancement : Claude rédige une série de posts à partir d'une seule consigne ; on relit, on ajuste,
// puis Tamtam les programme (créneaux du projet ou intervalle régulier). Les posts qui ne peuvent pas partir
// tels quels (média manquant, réglages TikTok) sont créés en brouillons datés, à compléter.

const TONES = [
  { value: "", label: "Selon le projet" }, { value: "enthousiaste", label: "Enthousiaste" },
  { value: "pro", label: "Pro" }, { value: "decontracte", label: "Décontracté" }, { value: "humour", label: "Humour" },
];

function slug(t) {
  const words = t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  let out = "";
  for (const w of words) {
    if ((out ? out.length + 1 : 0) + w.length > 32) break;
    out = out ? `${out}-${w}` : w;
  }
  return out;
}

export default function Campaign() {
  const { project, projectId, rules } = useApp();
  const toast = useToast();
  const [accounts, setAccounts] = useState(null);
  const [selected, setSelected] = useState([]);
  const [brief, setBrief] = useState("");
  const [count, setCount] = useState(5);
  const [tone, setTone] = useState("");
  const [link, setLink] = useState("");
  const [name, setName] = useState("");
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);   // { posts: [{title, common, versions, keep}], note }
  const slotCount = (project?.slots || []).length;
  const [plan, setPlan] = useState(slotCount ? "slots" : "every");
  const [start, setStart] = useState(() => {
    const d = new Date(Date.now() + 24 * 3600e3);
    d.setHours(10, 0, 0, 0);
    return toLocalInput(d);
  });
  const [every, setEvery] = useState(2);
  const [slotDates, setSlotDates] = useState([]);
  const [done, setDone] = useState(null);

  useEffect(() => {
    api.get(`/projects/${projectId}/accounts`).then((accs) => {
      accs.sort((a, b) => ORDER.indexOf(a.platform) - ORDER.indexOf(b.platform));
      setAccounts(accs);
      setSelected(accs.filter((a) => a.status === "ok").map((a) => a.id));
    }).catch(() => setAccounts([]));
    api.get("/ai/status").then(setStatus).catch(() => setStatus({ enabled: false }));
    setResult(null);
    setDone(null);
  }, [projectId]);

  const chosen = useMemo(() => (accounts || []).filter((a) => selected.includes(a.id)), [accounts, selected]);
  const platforms = [...new Set(chosen.map((a) => a.platform))];
  const kept = (result?.posts || []).filter((p) => p.keep);

  useEffect(() => {
    if (plan !== "slots" || !kept.length) return;
    api.get(`/projects/${projectId}/slots/next?count=${kept.length}`).then((r) => setSlotDates(r.next)).catch(() => setSlotDates([]));
  }, [plan, kept.length, projectId]);

  const dates = kept.map((_, i) => (plan === "slots" ? slotDates[i] || null
    : new Date(new Date(start).getTime() + i * every * 24 * 3600e3).toISOString()));

  if (!accounts || !status) return <Loading />;

  const ask = async () => {
    setBusy(true); setError(""); setDone(null);
    try {
      const r = await api.post("/ai/campaign", { project_id: projectId, brief, count, tone, platforms, has_link: Boolean(link.trim()) });
      setResult({ ...r, posts: r.posts.map((p) => ({ ...p, keep: true })) });
      if (!name.trim()) setName(slug(brief.split("\n")[0]) || "campagne");
    } catch (e) {
      setError(e.message);
    }
    setBusy(false);
  };
  const edit = (i, patch) => setResult((r) => ({ ...r, posts: r.posts.map((p, j) => (j === i ? { ...p, ...patch } : p)) }));

  const create = async () => {
    setBusy(true);
    const out = { scheduled: 0, drafts: [], failed: [] };
    for (let i = 0; i < kept.length; i += 1) {
      const p = kept[i];
      const overrides = {};
      chosen.forEach((a) => { const v = p.versions[a.platform]; if (v && v !== p.common) overrides[String(a.id)] = v; });
      const payload = { project_id: projectId, body: p.common, account_ids: selected, overrides, media_ids: [],
        link_url: link.trim(), campaign: name.trim(), mode: "at", scheduled_at: dates[i] };
      try {
        await api.post("/posts", payload);
        out.scheduled += 1;
      } catch (e) {
        try {
          await api.post("/posts", { ...payload, mode: "draft" });
          out.drafts.push({ title: p.title, reason: e.message });
        } catch (e2) {
          out.failed.push({ title: p.title, reason: e2.message });
        }
      }
    }
    setBusy(false);
    setDone(out);
    if (out.failed.length === 0) setResult(null);
    toast(`${out.scheduled} post(s) programmé(s), ${out.drafts.length} brouillon(s) à compléter`);
  };

  const needsMedia = chosen.some((a) => rules.rules[a.platform].media_required);
  const datesOk = dates.every(Boolean) && (plan === "slots" || !Number.isNaN(new Date(start).getTime()));
  return (
    <>
      <div className="page-head">
        <div><h1>Campagne de lancement</h1><p>{project.name} · une consigne, Claude rédige une série de posts à programmer.</p></div>
      </div>

      {done && (
        <div className="card stack" style={{ marginBottom: 16 }} id="campaign-done">
          <h2>Campagne « {name} » créée</h2>
          <p style={{ margin: 0 }}><b>{done.scheduled}</b> post(s) programmé(s), <b>{done.drafts.length}</b> brouillon(s) daté(s) à compléter.</p>
          {done.drafts.length > 0 && (
            <div className="stack" style={{ gap: 4 }}>
              <span className="small muted">Ces brouillons ne partiront pas tant que vous ne les aurez pas ouverts et programmés (ajout d'un média, réglages TikTok…) :</span>
              {done.drafts.map((d) => <div key={d.title} className="small">• <b>{d.title}</b> : {d.reason}</div>)}
            </div>
          )}
          {done.failed.map((d) => <div key={d.title} className="notice danger small"><Icon name="alert" size={16} />{d.title} : {d.reason}</div>)}
          <div className="row"><a className="btn" href="#/calendrier"><Icon name="calendar" size={16} />Voir le calendrier</a>
            {done.drafts.length > 0 && <a className="btn" href="#/?status=draft">Compléter les brouillons</a>}</div>
        </div>
      )}

      {!status.enabled ? (
        <div className="notice warn">Claude n'est pas configuré : un administrateur doit saisir la clé API dans Administration.</div>
      ) : !result ? (
        <div className="card stack" style={{ maxWidth: 820 }}>
          <div className="field">
            <span className="label">Publier sur</span>
            <div className="targets">
              {accounts.map((a) => (
                <button key={a.id} type="button" className="target" aria-pressed={selected.includes(a.id)}
                  onClick={() => setSelected((s) => (s.includes(a.id) ? s.filter((x) => x !== a.id) : [...s, a.id]))}>
                  <Net platform={a.platform} />
                  <span>{NETWORKS[a.platform].label} <span className="sub">{a.handle ? `@${a.handle}` : a.name}</span></span>
                </button>
              ))}
              {accounts.length === 0 && <a href="#/comptes">Connecter un compte</a>}
            </div>
          </div>
          <label className="field">Que lancez-vous ?
            <textarea id="campaign-brief" className="textarea" style={{ minHeight: 130 }} maxLength={4000} value={brief} onChange={(e) => setBrief(e.target.value)}
              placeholder="Ex. : la version 2 sort le 3 décembre. Nouveautés : mode sombre, export PDF, synchronisation. Public : les indépendants." />
          </label>
          {!project.description?.trim() && <div className="notice warn small"><Icon name="alert" size={16} />Le projet n'a pas de présentation : Claude aura peu de matière pour varier les posts (page Projets → Modifier).</div>}
          <div className="grid2">
            <label className="field">Nombre de posts
              <select id="campaign-count" className="select" value={count} onChange={(e) => setCount(Number(e.target.value))}>
                {[2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            <label className="field">Lien à promouvoir (facultatif)
              <input className="input" type="url" value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://" />
            </label>
          </div>
          <div className="field"><span className="label">Ton</span><Seg label="Ton" value={tone} onChange={setTone} options={TONES} /></div>
          <p className="small muted" style={{ margin: 0 }}>Rien n'est publié à cette étape : vous relirez chaque post avant de les programmer.
            {status.simulated ? " Mode simulation : textes factices, sans appel à Claude." : ` Compte pour une rédaction (${status.used_today}/${status.daily_limit} aujourd'hui).`}</p>
          {error && <div className="notice danger"><Icon name="alert" size={16} />{error}</div>}
          <div className="actions">
            <button type="button" id="campaign-ask" className="btn primary" disabled={busy || !brief.trim() || chosen.length === 0} onClick={ask}>
              <Icon name="sparkle" size={16} />{busy ? "Claude rédige la campagne… (jusqu'à deux minutes)" : `Proposer ${count} posts`}</button>
          </div>
        </div>
      ) : (
        <div className="stack">
          {result.note && <div className="notice warn small"><Icon name="alert" size={16} />{result.note}</div>}
          {result.posts.map((p, i) => {
            const idx = kept.indexOf(p);
            // Texte seulement : le média manquant (Instagram, TikTok) est signalé une fois plus bas.
            const issues = p.keep ? [...new Set(chosen.flatMap((a) => problems(rules, a.platform, p.versions[a.platform] ?? p.common, ["image"], Boolean(link.trim()))))] : [];
            return (
              <div key={i} className={`card stack campaign-post${p.keep ? "" : " off"}`}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="row" style={{ gap: 8 }}>
                    <Chip>{i + 1}</Chip><b>{p.title || `Post ${i + 1}`}</b>
                    {p.keep && <span className="small muted">{dates[idx] ? fmtDateTime(dates[idx]) : "pas de créneau libre"}</span>}
                  </div>
                  <label className="check small"><input type="checkbox" checked={p.keep} onChange={(e) => edit(i, { keep: e.target.checked })} /><span>Garder</span></label>
                </div>
                {p.keep && <>
                  <label className="field">Texte commun
                    <textarea className="textarea" style={{ minHeight: 90 }} value={p.common} onChange={(e) => edit(i, { common: e.target.value })} />
                  </label>
                  <details>
                    <summary className="small">Versions par réseau ({platforms.filter((x) => p.versions[x]).length})</summary>
                    <div className="stack" style={{ marginTop: 8 }}>
                      {platforms.filter((x) => p.versions[x] !== undefined).map((x) => (
                        <label key={x} className="field"><span className="row" style={{ gap: 6 }}><Net platform={x} size="s" />{NETWORKS[x].label}</span>
                          <textarea className="textarea" style={{ minHeight: 70 }} value={p.versions[x]}
                            onChange={(e) => edit(i, { versions: { ...p.versions, [x]: e.target.value } })} />
                        </label>
                      ))}
                    </div>
                  </details>
                  {issues.map((t) => <div key={t} className="notice danger small"><Icon name="alert" size={16} />{t}</div>)}
                </>}
              </div>
            );
          })}

          <div className="card stack">
            <h2>Programmation</h2>
            <label className="field">Nom de la campagne (pour les statistiques)
              <input id="campaign-name" className="input" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
            </label>
            <Seg label="Rythme" value={plan} onChange={setPlan} options={[
              { value: "slots", label: "Créneaux du projet" }, { value: "every", label: "Intervalle régulier" }]} />
            {plan === "slots" ? (slotCount === 0
              ? <div className="notice warn small"><Icon name="alert" size={16} />Ce projet n'a pas de créneaux. <a href="#/projets">Les définir dans Projets</a>, ou choisissez un intervalle régulier.</div>
              : <span className="small muted">Chaque post prend le prochain créneau libre du projet, dans l'ordre.</span>)
              : (
                <div className="row">
                  <label className="field">Premier post
                    <input id="campaign-start" className="input" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
                  </label>
                  <label className="field">Puis tous les
                    <select id="campaign-every" className="select" value={every} onChange={(e) => setEvery(Number(e.target.value))}>
                      {[1, 2, 3, 4, 7, 14].map((n) => <option key={n} value={n}>{n} jour{n > 1 ? "s" : ""}</option>)}
                    </select>
                  </label>
                </div>
              )}
            {needsMedia && <div className="notice warn small"><Icon name="alert" size={16} />Instagram et TikTok exigent un média : les posts qui les visent seront créés en brouillons datés, à compléter avec une image ou une vidéo.</div>}
            {chosen.some((a) => a.platform === "tiktok") && <div className="small muted">TikTok : les réglages (visibilité, divulgation…) se choisissent sur chaque post, en ouvrant le brouillon.</div>}
            <div className="actions">
              <button type="button" className="btn" disabled={busy} onClick={() => setResult(null)}><Icon name="refresh" size={16} />Recommencer</button>
              <button type="button" id="campaign-create" className="btn primary" disabled={busy || kept.length === 0 || !datesOk || !name.trim()} onClick={create}>
                <Icon name="calendar" size={16} />{busy ? "Création…" : `Programmer ${kept.length} post${kept.length > 1 ? "s" : ""}`}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
