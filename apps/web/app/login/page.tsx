"use client";

import { apiLoginUrl } from "../../lib/api";

export default function LoginPage() {
  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="eyebrow">SENTELLENT ASSESSMENT</p>
        <h1>Indian equity research, grounded in evidence.</h1>
        <p className="muted">
          Follow NSE/BSE tickers, ingest sources, and ask research questions with traceable citations in INR.
        </p>
        <a className="button button-primary full-width" href={apiLoginUrl()}>
          Continue with Google
        </a>
        <p className="fine-print">
          Uses OpenID Connect only: email, profile, and identity. No Gmail or Calendar access.
        </p>
      </section>
    </main>
  );
}
