import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api.js";
import { Icon, ToastProvider, useRun } from "./ui.jsx";
import Login from "./pages/Login.jsx";
import Composer from "./pages/Composer.jsx";
import Campaign from "./pages/Campaign.jsx";
import Inbox from "./pages/Inbox.jsx";
import Bio from "./pages/Bio.jsx";
import Health from "./pages/Health.jsx";
import Posts from "./pages/Posts.jsx";
import Calendar from "./pages/Calendar.jsx";
import Accounts from "./pages/Accounts.jsx";
import Stats from "./pages/Stats.jsx";
import Projects from "./pages/Projects.jsx";
import Admin from "./pages/Admin.jsx";
import Profile from "./pages/Profile.jsx";
import Help from "./pages/Help.jsx";

// Données partagées : utilisateur, projets, projet actif, règles des réseaux.
const AppCtx = createContext(null);
export const useApp = () => useContext(AppCtx);

function readStored() {
  try {
    return Number(localStorage.getItem("tamtam:project")) || null;
  } catch {
    return null;
  }
}

function useHash() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const on = () => {
      setHash(window.location.hash || "#/");
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return hash;
}

export function parseHash(hash) {
  const raw = hash.replace(/^#\/?/, "");
  const [path, query = ""] = raw.split("?");
  const parts = path.split("/");
  return { section: parts[0], id: parts[1], params: new URLSearchParams(query) };
}

const NAV = [
  { href: "#/nouveau", key: "nouveau", label: "Nouveau post", icon: "edit" },
  { href: "#/campagne", key: "campagne", label: "Campagne", icon: "sparkle" },
  { href: "#/", key: "", label: "Publications", icon: "list" },
  { href: "#/boite", key: "boite", label: "Boîte de réception", icon: "chat" },
  { href: "#/calendrier", key: "calendrier", label: "Calendrier", icon: "calendar" },
  { href: "#/bio", key: "bio", label: "Lien en bio", icon: "link" },
  { href: "#/comptes", key: "comptes", label: "Comptes", icon: "user" },
  { href: "#/stats", key: "stats", label: "Statistiques", icon: "chart" },
  { href: "#/projets", key: "projets", label: "Projets", icon: "folder" },
];

function Mark() {
  return (
    <span className="brand-mark">
      <svg viewBox="0 0 24 24" fill="none" stroke="var(--accent-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <ellipse cx="8.5" cy="8" rx="5.5" ry="2.4" /><path d="M3 8v8a5.5 2.4 0 0 0 11 0V8M17 9.5a4 4 0 0 1 0 5M20 7a8 8 0 0 1 0 10" />
      </svg>
    </span>
  );
}

function Shell({ section, children }) {
  const { me, projects, projectId, setProjectId, simulation, problems, toReview, inboxNew } = useApp();
  const run = useRun();
  const logout = async () => {
    await run(() => api.post("/auth/logout"));
    window.dispatchEvent(new Event("tamtam:logout"));
  };
  const active = projects.filter((p) => !p.archived);
  return (
    <div className="shell">
      <nav className="sidebar" aria-label="Navigation principale">
        <a className="brand" href="#/"><Mark /><b>Tamtam</b></a>
        {simulation && <div className="sim-banner">Mode simulation : rien n'est publié pour de vrai.</div>}
        <div className="project-pick">
          <label className="label" htmlFor="project-pick">Projet actif</label>
          <select id="project-pick" className="select" value={projectId ?? ""} onChange={(e) => setProjectId(Number(e.target.value))}>
            {active.length === 0 && <option value="">Aucun projet</option>}
            {active.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        {NAV.map((n) => (
          <a key={n.key} href={n.href} className={`nav-link${section === n.key ? " active" : ""}`}
            aria-current={section === n.key ? "page" : undefined}>
            <Icon name={n.icon} />
            {n.label}
            {n.key === "" && problems > 0 && <span className="nav-count" aria-label={`${problems} posts en échec`}>{problems}</span>}
            {n.key === "boite" && inboxNew > 0 && <span className="nav-count info" aria-label={`${inboxNew} commentaires à traiter`}>{inboxNew}</span>}
            {n.key === "" && toReview > 0 && <span className="nav-count review" aria-label={`${toReview} posts à valider`} title="Posts à valider">{toReview}</span>}
          </a>
        ))}
        <div className="nav-foot">
          {me.is_admin && (
            <a href="#/etat" className={`nav-link${section === "etat" ? " active" : ""}`}><Icon name="check" />État des connexions</a>
          )}
          {me.is_admin && (
            <a href="#/admin" className={`nav-link${section === "admin" ? " active" : ""}`}><Icon name="settings" />Administration</a>
          )}
          <a href="#/aide" className={`nav-link${section === "aide" ? " active" : ""}`}><Icon name="file" />Aide</a>
          <a href="#/profil" className={`nav-link${section === "profil" ? " active" : ""}`}>
            <Icon name="user" />
            <span className="grow" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{me.name || me.email}</span>
          </a>
          <button type="button" className="nav-link" style={{ border: 0, background: "none" }} onClick={logout}>
            <Icon name="logout" />Se déconnecter
          </button>
        </div>
      </nav>
      <main className="main">{children}</main>
    </div>
  );
}

function Router({ route }) {
  const { section, id, params } = route;
  switch (section) {
    case "nouveau":
      return <Composer key={(id || "") + params.toString()} editId={id ? Number(id) : null}
        copyId={params.get("copy") ? Number(params.get("copy")) : null}
        recycleId={params.get("recycle") ? Number(params.get("recycle")) : null} date={params.get("date")} />;
    case "campagne":
      return <Campaign />;
    case "boite":
      return <Inbox />;
    case "bio":
      return <Bio />;
    case "etat":
      return <Health />;
    case "calendrier":
      return <Calendar />;
    case "comptes":
      return <Accounts params={params} />;
    case "stats":
      return <Stats />;
    case "projets":
      return <Projects />;
    case "admin":
      return <Admin />;
    case "profil":
      return <Profile />;
    case "aide":
      return <Help />;
    default:
      return <Posts />;
  }
}

function Authed({ me, setMe }) {
  const hash = useHash();
  const route = parseHash(hash);
  const [projects, setProjects] = useState(null);
  const [projectId, setProjectIdRaw] = useState(readStored);
  const [rules, setRules] = useState(null);
  const [simulation, setSimulation] = useState(false);
  const [problems, setProblems] = useState(0);
  const [toReview, setToReview] = useState(0);
  const [inboxNew, setInboxNew] = useState(0);

  const refreshProjects = useCallback(() => api.get("/projects").then((list) => {
    setProjects(list);
    setProjectIdRaw((cur) => {
      const act = list.filter((p) => !p.archived);
      return act.some((p) => p.id === cur) ? cur : act[0]?.id ?? null;
    });
    return list;
  }).catch(() => setProjects([])), []);
  const setProjectId = useCallback((id) => {
    setProjectIdRaw(id);
    try {
      localStorage.setItem("tamtam:project", String(id));
    } catch {
      /* stockage indisponible : le choix vaut pour cette page seulement */
    }
  }, []);
  useEffect(() => {
    refreshProjects();
    api.get("/rules").then(setRules).catch(() => {});
    api.get("/connect/providers").then((r) => setSimulation(r.simulation)).catch(() => {});
  }, [refreshProjects]);
  useEffect(() => {
    if (projectId) api.get(`/posts?project_id=${projectId}&status=problems&limit=50`).then((r) => setProblems(r.length)).catch(() => {});
    if (projectId) api.get(`/inbox?project_id=${projectId}&status=new`).then((r) => setInboxNew(r.new)).catch(() => {});
    if (projectId && me.is_admin) api.get(`/posts?project_id=${projectId}&status=review&limit=50`).then((r) => setToReview(r.length)).catch(() => {});
  }, [projectId, hash]);

  if (projects === null || rules === null) return <div className="empty">Chargement…</div>;
  const project = projects.find((p) => p.id === projectId) || null;
  const ctx = { me, setMe, projects, project, projectId, setProjectId, refreshProjects, rules, simulation, problems, toReview, inboxNew };
  const needsProject = !project && !["projets", "admin", "profil", "aide", "etat"].includes(route.section);
  return (
    <AppCtx.Provider value={ctx}>
      <Shell section={route.section}>
        {(route.section === "admin" || route.section === "etat") && !me.is_admin ? <div className="notice danger">Page réservée aux administrateurs.</div>
          : needsProject ? (
            <div className="card stack" style={{ maxWidth: 560 }}>
              <h1>Bienvenue sur Tamtam</h1>
              <p className="muted" style={{ margin: 0 }}>Commencez par créer un projet : une appli, un site ou un produit à faire connaître.
                Chaque projet a ses propres comptes Instagram, Facebook, X, TikTok, Threads, Bluesky, LinkedIn et YouTube.</p>
              <div><a className="btn primary" href="#/projets">Créer un projet</a></div>
            </div>
          ) : <Router route={route} />}
      </Shell>
    </AppCtx.Provider>
  );
}

export default function App() {
  const [me, setMe] = useState(undefined);
  useEffect(() => {
    api.get("/auth/me").then(setMe).catch(() => setMe(null));
    const out = () => setMe(null);
    window.addEventListener("tamtam:logout", out);
    return () => window.removeEventListener("tamtam:logout", out);
  }, []);
  return (
    <ToastProvider>
      {me === undefined ? <div className="empty">Chargement…</div>
        : me === null ? <Login onLogin={setMe} />
          : <Authed me={me} setMe={setMe} />}
    </ToastProvider>
  );
}
