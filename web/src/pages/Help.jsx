import React from "react";
import { api } from "../api.js";
import { renderMarkdown } from "../markdown.jsx";
import { Loading, useLoad } from "../ui.jsx";

export default function Help() {
  const { data, error } = useLoad(() => api.get("/docs/guide"), []);
  if (!data) return <Loading error={error} />;
  return <article className="card guide">{renderMarkdown(data.markdown)}</article>;
}
