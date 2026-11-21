import React, { useMemo, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Icon, Loading, Net, useLoad } from "../ui.jsx";

function monday(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
  return x;
}
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export default function Calendar() {
  const { projectId, project } = useApp();
  const [start, setStart] = useState(() => monday(new Date()));
  const end = useMemo(() => new Date(start.getTime() + 7 * 864e5), [start]);
  const { data, error } = useLoad(
    () => api.get(`/posts?project_id=${projectId}&start=${start.toISOString()}&end=${end.toISOString()}&limit=300`),
    [projectId, start.getTime()]);
  const days = [...Array(7)].map((_, i) => new Date(start.getTime() + i * 864e5));
  const today = iso(new Date());
  const shift = (n) => setStart(new Date(start.getTime() + n * 7 * 864e5));
  const title = `Semaine du ${start.toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}`;
  return (
    <>
      <div className="page-head">
        <div><h1>{title}</h1><p>{project.name} · posts programmés, publiés et brouillons datés.</p></div>
        <div className="row">
          <button type="button" className="btn" onClick={() => shift(-1)}><Icon name="left" size={16} />Préc.</button>
          <button type="button" className="btn" onClick={() => setStart(monday(new Date()))}>Aujourd'hui</button>
          <button type="button" className="btn" onClick={() => shift(1)}>Suiv.<Icon name="right" size={16} /></button>
        </div>
      </div>
      {!data ? <Loading error={error} /> : (
        <div className="cal-wrap">
          <div className="cal">
            {days.map((d) => {
              const key = iso(d);
              const items = data.filter((p) => p.scheduled_at && iso(new Date(p.scheduled_at)) === key)
                .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at));
              const past = key < today;
              return (
                <div key={key} className={`day${key === today ? " today" : ""}`}>
                  <h4>{d.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric" })}{key === today && <span>auj.</span>}</h4>
                  {items.map((p) => (
                    <a key={p.id} className="slot" href={p.status === "draft" || p.status === "scheduled" ? `#/nouveau/${p.id}` : "#/"}
                      style={p.status === "draft" ? { borderStyle: "dashed" } : undefined}>
                      <div className="pfs">
                        {p.targets.map((t) => <Net key={t.id} platform={t.platform} size="s" />)}
                        <time style={{ marginLeft: "auto" }}>{new Date(p.scheduled_at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}</time>
                      </div>
                      <span className="t">{p.status === "draft" ? "Brouillon · " : p.status === "failed" ? "Échec · " : ""}{p.body || "(texte par réseau)"}</span>
                    </a>
                  ))}
                  {!past && <a className="add-day" href={`#/nouveau?date=${key}`}>+ Programmer</a>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
