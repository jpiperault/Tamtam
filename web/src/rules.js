// Règles des réseaux côté interface (mêmes calculs que le serveur, pour prévenir avant d'envoyer).

export function textLength(rules, platform, text, hasLink) {
  const r = rules.rules[platform];
  const n = [...text].length;
  if (!hasLink) return n;
  if (platform === "x") return n + 1 + rules.x_url_length;
  if (r.link_in_text) return n + 1 + linkLength(rules);
  return n;
}

export function linkLength(rules) {
  return `${rules.public_url}/l/abcdefg`.length;
}

export function problems(rules, platform, text, kinds, hasLink) {
  const r = rules.rules[platform];
  const label = rules.labels[platform];
  const out = [];
  const n = textLength(rules, platform, text, hasLink);
  if (n > r.text) out.push(`${label} : ${n - r.text} caractère(s) de trop.`);
  const images = kinds.filter((k) => k === "image").length;
  const videos = kinds.filter((k) => k === "video").length;
  if (r.media_required && !kinds.length) out.push(`${label} : une image ou une vidéo est obligatoire.`);
  if (images > r.max_images) out.push(`${label} : ${r.max_images} image(s) au plus.`);
  if (videos > r.max_videos) out.push(`${label} : une seule vidéo par post.`);
  if (images && videos && !r.mix) out.push(`${label} : impossible de mélanger images et vidéo.`);
  if (platform === "x" && !text.trim() && !kinds.length) out.push("X : le texte est vide.");
  return out;
}

export function warnings(platform, kinds, account, hasLink) {
  const out = [];
  if (platform === "tiktok" && kinds.length && !kinds.includes("video"))
    out.push("TikTok : les photos sont récupérées par TikTok à l'adresse publique de Tamtam, qui doit être vérifiée dans le portail développeur TikTok.");
  if (platform === "tiktok" && !account?.simulated)
    out.push("TikTok : tant que l'application n'a pas passé l'audit TikTok, le post n'est visible que par vous.");
  if (hasLink && (platform === "instagram" || platform === "tiktok"))
    out.push(`${platform === "instagram" ? "Instagram" : "TikTok"} : les liens ne sont pas cliquables dans les posts. Mettez le lien dans la bio du compte.`);
  return out;
}

export function withUtm(url, platform, campaign) {
  try {
    const u = new URL(url);
    [...u.searchParams.keys()].filter((k) => k.startsWith("utm_")).forEach((k) => u.searchParams.delete(k));
    u.searchParams.set("utm_source", platform);
    u.searchParams.set("utm_medium", "social");
    u.searchParams.set("utm_campaign", campaign || "tamtam");
    u.searchParams.set("utm_content", "post-ID");
    return u.toString().replace("utm_source=RESEAU", "utm_source={réseau}").replace("post-ID", "post-{n°}");
  } catch {
    return "";
  }
}

export function fmtDateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("fr-FR", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function toLocalInput(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}
