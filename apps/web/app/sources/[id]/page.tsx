"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "../../../lib/api";
import type { SourceDetail } from "../../../lib/types";

export default function SourceDetailPage() {
  const params = useParams();
  const sourceId = params.id as string;
  const [source, setSource] = useState<SourceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sourceId) return;
    api
      .getSource(sourceId)
      .then(setSource)
      .catch((reason) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [sourceId]);

  if (loading) {
    return (
      <main className="app-shell">
        <header className="topbar">
          <Link href="/" className="brand">Sentellent <span>Equity Analyst</span></Link>
          <Link className="text-link" href="/">Back to research</Link>
        </header>
        <main className="loading-shell">Loading source...</main>
      </main>
    );
  }

  if (error || !source) {
    return (
      <main className="app-shell">
        <header className="topbar">
          <Link href="/" className="brand">Sentellent <span>Equity Analyst</span></Link>
          <Link className="text-link" href="/">Back to research</Link>
        </header>
        <section className="page-heading">
          <p className="eyebrow">SOURCE NOT FOUND</p>
          <h1>Could not load source</h1>
          <p className="muted">{error || "Source document not found or you do not have access."}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <Link href="/" className="brand">Sentellent <span>Equity Analyst</span></Link>
        <Link className="text-link" href="/">Back to research</Link>
      </header>
      <section className="page-heading">
        <p className="eyebrow">SOURCE PROVENANCE</p>
        <h1>{source.title}</h1>
      </section>
      <section className="source-detail panel">
        <div className="source-meta">
          <div className="source-meta-item">
            <strong>Publisher</strong>
            <span>{source.publisher}</span>
          </div>
          <div className="source-meta-item">
            <strong>Type</strong>
            <span>{source.type}</span>
          </div>
          {source.published_at && (
            <div className="source-meta-item">
              <strong>Published</strong>
              <span>{new Date(source.published_at).toLocaleString()}</span>
            </div>
          )}
          {source.retrieved_at && (
            <div className="source-meta-item">
              <strong>Retrieved</strong>
              <span>{new Date(source.retrieved_at).toLocaleString()}</span>
            </div>
          )}
        </div>

        {source.excerpt && (
          <div className="source-section">
            <h2>Excerpt</h2>
            <p className="source-excerpt">{source.excerpt}</p>
          </div>
        )}

        {source.content && (
          <div className="source-section">
            <h2>Full Content</h2>
            <div className="source-content">
              {source.content.split("\n").map((paragraph, i) => (
                <p key={i}>{paragraph || "\u00a0"}</p>
              ))}
            </div>
          </div>
        )}

        <div className="source-link">
          <a href={source.url} target="_blank" rel="noreferrer">
            Open original source in new tab
          </a>
        </div>
      </section>
    </main>
  );
}
