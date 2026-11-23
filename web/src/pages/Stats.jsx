import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { DAYS, fmtDateTime } from "../rules.js";
import { Chip, Icon, Loading, NETWORKS, Net, ORDER, Seg, useLoad, useRun } from "../ui.jsx";

const METRICS = [["views", "Vues"], ["likes", "J'aime"], ["comments", "Commentaires"], ["shares", "Partages"]];
const fmt = (n) => (n == null ? "–" : Number(n).toLocaleString("fr-FR"));
const fmtDay = (d) => new Date(`${d}T12:00:00`).toLocaleDateString("fr-FR", { day: "numeric", month: "long" });

function NetworkStats({ projectId, days }) {
  const run = useRun();
  const [busy, setBusy] = useState(false);
  const { data, error, reload } = useLoad(() => api.get(`/insights?project_id=${projectId}&days=${days}`), [projectId, days]);
  if (!data) return <Loading error={error} />;
  const refresh = async () => {
    setBusy(true);
    const r = await run(() => api.post(`/insights/refresh?project_id=${projectId}`));
    setBusy(false);
    if (r) reload();
  };
  const nets = ORDER.map((p) => data.by_platform.find((r) => r.platform === p)).filter(Boolean);
  const last = nets.map((n) => n.fetched_at).filter(Boolean).sort().pop();
  const errors = [...new Set(data.posts.flatMap((p) => p.networks.filter((n) => n.error).map((n) => `${NETWORKS[n.platform].label} : ${n.error}`)))];
  return (
    <div className="card stack" style={{ marginBottom: 16 }} id="network-stats">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>Chiffres des réseaux</h2>
        <div className="row" style={{ gap: 8 }}>
          {last && <span className="small muted">Relus le {fmtDateTime(last)}</span>}
          <button type="button" id="stats-refresh" className="btn small" disabled={busy} onClick={refresh}><Icon name="refresh" size={14} />{busy ? "Lecture…" : "Actualiser"}</button>
        </div>
      </div>
      {nets.length === 0 ? <p className="muted" style={{ margin: 0 }}>Aucun post publié sur la période.</p> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Réseau</th><th style={{ textAlign: "right" }}>Posts</th>{METRICS.map(([k, l]) => <th key={k} style={{ textAlign: "right" }}>{l}</th>)}</tr></thead>
          <tbody>{nets.map((n) => (
            <tr key={n.platform}><td><span className="row" style={{ gap: 6 }}><Net platform={n.platform} size="s" />{NETWORKS[n.platform].label}</span></td>
              <td className="mono" style={{ textAlign: "right" }}>{n.posts}</td>
              {METRICS.map(([k]) => <td key={k} className="mono" style={{ textAlign: "right" }}>{fmt(n[k])}</td>)}</tr>
          ))}</tbody>
        </table></div>
      )}
      {data.posts.length > 0 && (
        <details>
          <summary className="small">Détail par post ({data.posts.length})</summary>
          <div className="table-wrap" style={{ marginTop: 8 }}><table>
            <thead><tr><th>Post</th><th>Réseau</th>{METRICS.map(([k, l]) => <th key={k} style={{ textAlign: "right" }}>{l}</th>)}<th style={{ textAlign: "right" }}>Clics</th><th /></tr></thead>
            <tbody>{data.posts.flatMap((p) => p.networks.map((n, i) => (
              <tr key={`${p.id}-${n.platform}`}>
                {i === 0 && <td rowSpan={p.networks.length} style={{ whiteSpace: "normal", maxWidth: 320 }}>{p.body}<div className="small muted">{fmtDateTime(p.published_at)}</div></td>}
                <td>{n.external_url ? <a href={n.external_url} target="_blank" rel="noreferrer">{NETWORKS[n.platform].label}</a> : NETWORKS[n.platform].label}</td>
                {METRICS.map(([k]) => <td key={k} className="mono" style={{ textAlign: "right" }}>{fmt(n[k])}</td>)}
                <td className="mono" style={{ textAlign: "right" }}>{n.clicks}</td>
                {i === 0 && <td rowSpan={p.networks.length}><a className="btn small" href={`#/nouveau?recycle=${p.id}`}><Icon name="sparkle" size={14} />Recycler</a></td>}
              </tr>
            )))}</tbody>
          </table></div>
        </details>
      )}
      {errors.length > 0 && <div className="stack" style={{ gap: 4 }}>{errors.slice(0, 4).map((e) => <div key={e} className="notice warn small"><Icon name="alert" size={16} />{e}</div>)}</div>}
      <p className="small muted" style={{ margin: 0 }}>« – » : chiffre que le réseau ne fournit pas avec les permissions actuelles (voir Administration → Statistiques des réseaux).</p>
    </div>
  );
}

function ReportView({ r }) {
  const c = r.content;
  return (
    <div className="stack report" style={{ gap: 8 }}>
      <p style={{ margin: 0 }}>{c.resume}</p>
      {[["points_forts", "Points forts"], ["a_ameliorer", "À améliorer"], ["idees", "Idées pour la semaine"]].map(([k, l]) => (c[k] || []).length > 0 && (
        <div key={k}><span className="label">{l}</span><ul style={{ margin: "4px 0 0", paddingLeft: 20 }}>{c[k].map((x) => <li key={x}>{x}</li>)}</ul></div>
      ))}
    </div>
  );
}

function Reports({ projectId }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const { data, error, reload } = useLoad(() => api.get(`/reports?project_id=${projectId}`), [projectId]);
  if (!data) return <Loading error={error} />;
  const make = async () => {
    setBusy(true); setErr("");
    try { await api.post(`/reports?project_id=${projectId}`); reload(); } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const [latest, ...older] = data;
  return (
    <div className="card stack" style={{ marginBottom: 16 }} id="reports">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>Bilan rédigé par Claude</h2>
        <button type="button" id="report-make" className="btn small" disabled={busy} onClick={make}><Icon name="sparkle" size={14} />{busy ? "Claude analyse… (jusqu'à une minute)" : "Bilan des 7 derniers jours"}</button>
      </div>
      {err && <div className="notice danger small"><Icon name="alert" size={16} />{err}</div>}
      {!latest ? <p className="muted" style={{ margin: 0 }}>Pas encore de bilan. Claude lit les chiffres de la semaine, repère ce qui a marché et propose des idées pour la suivante.</p> : <>
        <span className="small muted">Du {fmtDay(latest.period_start)} au {fmtDay(latest.period_end)}{latest.automatic ? " · rapport automatique du lundi" : ""}</span>
        <ReportView r={latest} />
      </>}
      {older.length > 0 && (
        <details><summary className="small">Bilans précédents ({older.length})</summary>
          <div className="stack" style={{ marginTop: 8 }}>{older.map((r) => (
            <div key={r.id} className="stack" style={{ gap: 4, borderTop: "1px solid var(--line)", paddingTop: 8 }}>
              <span className="small muted">Du {fmtDay(r.period_start)} au {fmtDay(r.period_end)}</span><ReportView r={r} />
            </div>))}</div>
        </details>
      )}
    </div>
  );
}

const pct = (s) => (s == null ? "–" : `${s >= 1 ? "+" : ""}${Math.round((s - 1) * 100)} %`);

function BestTimes({ projectId }) {
  const { project, refreshProjects } = useApp();
  const run = useRun();
  const [platform, setPlatform] = useState("");
  const { data, error, reload } = useLoad(() => api.get(`/insights/best-times?project_id=${projectId}&days=90&platform=${platform}`), [projectId, platform]);
  if (!data) return <Loading error={error} />;
  const add = async (s) => {
    const slots = [...(project.slots || []), { day: s.day, time: s.time }];
    if (await run(() => api.patch(`/projects/${projectId}`, { slots }), `Créneau ${DAYS[s.day].toLowerCase()} ${s.time} ajouté`)) { refreshProjects(); reload(); }
  };
  const maxDay = Math.max(1, ...data.by_day.map((d) => d.score || 0));
  const hours = data.by_hour.filter((h) => h.posts > 0);
  const maxHour = Math.max(1, ...hours.map((h) => h.score || 0));
  return (
    <div className="card stack" style={{ marginBottom: 16 }} id="best-times">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>Meilleurs moments pour publier</h2>
        <select className="select" style={{ width: "auto" }} aria-label="Réseau" value={platform} onChange={(e) => setPlatform(e.target.value)}>
          <option value="">Tous les réseaux</option>
          {ORDER.map((p) => <option key={p} value={p}>{NETWORKS[p].label}</option>)}
        </select>
      </div>
      <p className="small muted" style={{ margin: 0 }}>D'après les {data.measured} post(s) mesuré(s) des 90 derniers jours. Chaque post est comparé à la moyenne de son réseau (vues et réactions) : « +40 % » veut dire 40 % de mieux que d'habitude.</p>
      {!data.enough && <div className="notice warn small"><Icon name="alert" size={16} />Encore trop peu de chiffres pour conclure : il faut au moins {data.enough_at} posts mesurés{data.measured ? `, il y en a ${data.measured}` : ""}. Publiez à des moments variés pour comparer.</div>}
      {data.best.length > 0 && (
        <div className="table-wrap"><table>
          <thead><tr><th>Moment</th><th style={{ textAlign: "right" }}>Résultat</th><th style={{ textAlign: "right" }}>Posts</th><th /></tr></thead>
          <tbody>{data.best.map((s) => (
            <tr key={`${s.day}-${s.hour}`}><td>{DAYS[s.day]} vers {s.time}</td>
              <td className="mono" style={{ textAlign: "right" }}>{pct(s.score)}</td>
              <td className="mono" style={{ textAlign: "right" }}>{s.posts}</td>
              <td style={{ textAlign: "right" }}>{s.in_slots ? <Chip tone="ok">dans vos créneaux</Chip>
                : <button type="button" className="btn small best-add" onClick={() => add(s)}><Icon name="plus" size={14} />Ajouter aux créneaux</button>}</td></tr>
          ))}</tbody>
        </table></div>
      )}
      {data.enough && data.best.length === 0 && <p className="muted small" style={{ margin: 0 }}>Aucun moment ne se détache : il faut au moins {data.min_posts} posts publiés au même jour et à la même heure pour les comparer.</p>}
      {data.worst.length > 0 && <p className="small" style={{ margin: 0 }}>Moins bons : {data.worst.map((s) => `${DAYS[s.day].toLowerCase()} vers ${s.time} (${pct(s.score)})`).join(", ")}.</p>}
      {data.measured > 0 && (
        <div className="grid2">
          <div><span className="label">Par jour</span>
            {data.by_day.map((d) => (
              <div key={d.day} className="hbar"><span>{DAYS[d.day]}</span>
                <span className="track"><b style={{ width: `${((d.score || 0) / maxDay) * 100}%` }} /></span>
                <span className="mono small" style={{ textAlign: "right" }}>{d.posts ? pct(d.score) : "–"}</span></div>
            ))}</div>
          <div><span className="label">Par heure de publication</span>
            {hours.map((h) => (
              <div key={h.hour} className="hbar"><span>{String(h.hour).padStart(2, "0")} h</span>
                <span className="track"><b style={{ width: `${((h.score || 0) / maxHour) * 100}%` }} /></span>
                <span className="mono small" style={{ textAlign: "right" }}>{pct(h.score)}</span></div>
            ))}</div>
        </div>
      )}
    </div>
  );
}

export default function Stats() {
  const { projectId, project } = useApp();
  const [days, setDays] = useState(30);
  const { data, error } = useLoad(() => api.get(`/stats?project_id=${projectId}&days=${days}`), [projectId, days]);
  if (!data) return <Loading error={error} />;
  const clicks = Object.fromEntries(data.by_platform.map((r) => [r.platform, r.clicks]));
  const total = Object.values(clicks).reduce((a, b) => a + b, 0);
  const max = Math.max(1, ...Object.values(clicks));
  return (
    <>
      <div className="page-head">
        <div><h1>Statistiques</h1><p>{project.name} · chiffres lus sur chaque réseau et clics sur vos liens suivis.</p></div>
        <Seg label="Période" value={days} onChange={setDays}
          options={[{ value: 7, label: "7 jours" }, { value: 30, label: "30 jours" }, { value: 90, label: "90 jours" }]} />
      </div>
      <Reports projectId={projectId} />
      <NetworkStats projectId={projectId} days={days} />
      <BestTimes projectId={projectId} />
      <div className="kpis" style={{ marginBottom: 16 }}>
        <div className="card kpi"><b className="mono">{total}</b><span>clics sur vos liens</span></div>
        <div className="card kpi"><b className="mono">{data.counts.published}</b><span>publications réussies</span></div>
        <div className="card kpi"><b className="mono">{data.counts.upcoming}</b><span>publications à venir</span></div>
        <div className="card kpi"><b className="mono">{data.counts.failed}</b><span>échecs sur la période</span></div>
      </div>
      <div className="grid2">
        <div className="card stack">
          <h2>Clics par réseau</h2>
          {total === 0 ? <p className="muted" style={{ margin: 0 }}>Pas encore de clic. Ajoutez un lien à vos posts : Tamtam le remplace sur Facebook et X par un lien court qui compte les visites.</p>
            : ORDER.filter((p) => p in clicks).map((p) => (
              <div key={p} className="hbar">
                <span className="row" style={{ gap: 6 }}><Net platform={p} size="s" />{NETWORKS[p].label}</span>
                <span className="track"><b className={p} style={{ width: `${(clicks[p] / max) * 100}%` }} /></span>
                <span className="mono" style={{ textAlign: "right" }}>{clicks[p]}</span>
              </div>
            ))}
          <p className="small muted" style={{ margin: 0 }}>Instagram et TikTok ne permettent pas de lien cliquable dans un post : leurs visites arrivent par le lien de la bio et se voient dans vos propres statistiques de site (paramètre utm_source).</p>
        </div>
        <div className="card stack">
          <h2>Posts qui ont ramené le plus de visites</h2>
          {data.top.length === 0 ? <p className="muted" style={{ margin: 0 }}>Rien à classer pour cette période.</p> : (
            <div className="table-wrap"><table>
              <thead><tr><th>Post</th><th style={{ textAlign: "right" }}>Clics</th><th /></tr></thead>
              <tbody>{data.top.map((p) => (
                <tr key={p.id}><td style={{ whiteSpace: "normal" }}>{p.body}</td><td className="mono" style={{ textAlign: "right" }}>{p.clicks}</td>
                  <td style={{ textAlign: "right" }}><a className="btn small" href={`#/nouveau?recycle=${p.id}`} title="Republier ce post dans une nouvelle version rédigée par Claude"><Icon name="sparkle" size={14} />Recycler</a></td></tr>
              ))}</tbody>
            </table></div>
          )}
        </div>
      </div>
    </>
  );
}
