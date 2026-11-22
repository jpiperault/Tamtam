import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Icon, Loading, NETWORKS, Net, ORDER, Seg, useLoad } from "../ui.jsx";

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
        <div><h1>Statistiques</h1><p>{project.name} · clics sur les liens suivis que Tamtam ajoute à vos posts.</p></div>
        <Seg label="Période" value={days} onChange={setDays}
          options={[{ value: 7, label: "7 jours" }, { value: 30, label: "30 jours" }, { value: 90, label: "90 jours" }]} />
      </div>
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
