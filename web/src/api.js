// Petit client pour l'API : renvoie le JSON, lève une erreur lisible sinon.
export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, body, isForm = false) {
  const opts = { method, credentials: "same-origin", headers: {} };
  if (body !== undefined) {
    if (isForm) opts.body = body;
    else {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
  }
  const res = await fetch(`/api/v1${path}`, opts);
  let data = null;
  const text = await res.text();
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const msg = (data && data.detail) || `erreur ${res.status}`;
    if (res.status === 401) window.dispatchEvent(new Event("tamtam:logout"));
    throw new ApiError(res.status, typeof msg === "string" ? msg : "requête refusée");
  }
  return data;
}

export const api = {
  get: (p) => request("GET", p),
  post: (p, b) => request("POST", p, b ?? {}),
  put: (p, b) => request("PUT", p, b),
  patch: (p, b) => request("PATCH", p, b),
  del: (p) => request("DELETE", p),
  upload: (p, file) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("POST", p, fd, true);
  },
};
