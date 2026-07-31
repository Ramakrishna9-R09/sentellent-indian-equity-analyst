"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { api } from "../../lib/api";
import type { Profile } from "../../lib/types";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.profile().then(setProfile).catch((reason) => setError(reason.message));
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError("");
    try {
      const next = await api.patchProfile({
        risk_tolerance: form.get("risk_tolerance") || null,
        horizon: form.get("horizon") || null,
        avoid_high_debt: form.get("avoid_high_debt") === "on",
        max_debt_to_equity: form.get("max_debt_to_equity")
          ? Number(form.get("max_debt_to_equity"))
          : null,
        objectives: String(form.get("objectives") || "")
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        excluded_sectors: String(form.get("excluded_sectors") || "")
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean)
      });
      setProfile(next);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update profile.");
    } finally {
      setSaving(false);
    }
  }

  const saved = profile?.profile || {};
  return (
    <main className="app-shell">
      <header className="topbar">
        <Link href="/" className="brand">Sentellent <span>Equity Analyst</span></Link>
        <Link className="text-link" href="/">Back to research</Link>
      </header>
      <section className="page-heading">
        <p className="eyebrow">DURABLE INVESTOR MEMORY</p>
        <h1>Your investor profile</h1>
        <p className="muted">Profile rules are applied as deterministic filters before recommendations are explained.</p>
      </section>
      {error && <p className="error-banner">{error}</p>}
      <section className="profile-grid">
        <form className="panel form-grid" onSubmit={save}>
          <label>
            Risk tolerance
            <select name="risk_tolerance" defaultValue={saved.risk_tolerance || ""}>
              <option value="">Not set</option>
              <option value="conservative">Conservative</option>
              <option value="moderate">Moderate</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </label>
          <label>
            Horizon
            <select name="horizon" defaultValue={saved.horizon || ""}>
              <option value="">Not set</option>
              <option value="short_term">Short term</option>
              <option value="long_term">Long term</option>
            </select>
          </label>
          <label>
            Objectives (comma separated)
            <input name="objectives" defaultValue={(saved.objectives || []).join(", ")} placeholder="income, growth" />
          </label>
          <label>
            Maximum debt/equity
            <input
              name="max_debt_to_equity"
              inputMode="decimal"
              defaultValue={saved.max_debt_to_equity ?? ""}
              placeholder="Example: 1.0"
            />
          </label>
          <label className="checkbox-label">
            <input name="avoid_high_debt" type="checkbox" defaultChecked={Boolean(saved.avoid_high_debt)} />
            Exclude high-debt companies
          </label>
          <label className="full-width-field">
            Excluded sectors (comma separated)
            <input name="excluded_sectors" defaultValue={(saved.excluded_sectors || []).join(", ")} placeholder="e.g. Tobacco, Gambling" />
          </label>
          <button className="button button-primary" disabled={saving}>{saving ? "Saving..." : "Save profile"}</button>
        </form>
        <aside className="panel">
          <p className="eyebrow">MEMORY PROVENANCE</p>
          <h2>Active facts</h2>
          <div className="fact-list">
            {profile?.facts.length ? profile.facts.map((fact) => (
              <div className="fact" key={fact.id}>
                <strong>{fact.key.replaceAll("_", " ")}</strong>
                <span>{String(fact.value.value)}</span>
                <small>Recorded from {fact.value.source || "profile editor"}</small>
              </div>
            )) : <p className="muted">No durable preferences yet. State one in research chat or add it here.</p>}
          </div>
        </aside>
      </section>
    </main>
  );
}
