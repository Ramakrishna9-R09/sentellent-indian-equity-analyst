"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "../lib/api";
import type { ChatReply, Follow, Profile, Stock, User } from "../lib/types";

type ChatEntry = {
  id: string;
  role: "user" | "assistant";
  text: string;
  reply?: ChatReply;
};

function statusLabel(status?: string): string {
  if (!status) return "Not ingested";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [follows, setFollows] = useState<Follow[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [threadId, setThreadId] = useState("");
  const [search, setSearch] = useState("");
  const [matches, setMatches] = useState<Stock[]>([]);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.me(), api.follows(), api.profile(), api.createThread()])
      .then(([nextUser, nextFollows, nextProfile, thread]) => {
        setUser(nextUser);
        setFollows(nextFollows);
        setProfile(nextProfile);
        setThreadId(thread.id);
      })
      .catch((reason) => {
        if (String(reason.message).toLowerCase().includes("authentication")) {
          window.location.assign("/login");
          return;
        }
        setError(reason instanceof Error ? reason.message : "Could not load the research workspace.");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (search.trim().length < 1) {
      setMatches([]);
      return;
    }
    const timer = window.setTimeout(() => {
      api.searchStocks(search).then(setMatches).catch(() => setMatches([]));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [search]);

  const activeProfile = useMemo(() => profile?.profile || {}, [profile]);

  async function addFollow(stock: Stock) {
    setError("");
    setNotice("");
    try {
      const follow = await api.follow(stock.symbol, stock.exchange, stock.company_name);
      setFollows((current) => {
        const exists = current.some((item) => item.stock.id === follow.stock.id);
        return exists ? current : [follow, ...current];
      });
      setSearch("");
      setMatches([]);
      setNotice(stock.symbol + " is followed. The ingestion worker has been queued.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not follow that stock.");
    }
  }

  async function refresh(symbol: string) {
    setError("");
    try {
      const job = await api.refresh(symbol);
      setFollows((current) =>
        current.map((follow) =>
          follow.stock.symbol === symbol ? { ...follow, latest_job: job } : follow
        )
      );
      setNotice(symbol + " refresh is queued.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not refresh the ticker.");
    }
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || sending) return;
    setQuestion("");
    setSending(true);
    setError("");
    const userEntry: ChatEntry = { id: crypto.randomUUID(), role: "user", text: trimmed };
    setEntries((current) => [...current, userEntry]);
    try {
      let activeThread = threadId;
      if (!activeThread) {
        const thread = await api.createThread();
        activeThread = thread.id;
        setThreadId(thread.id);
      }
      const reply = await api.sendMessage(activeThread, trimmed);
      setEntries((current) => [
        ...current,
        { id: reply.request_id, role: "assistant", text: reply.answer_markdown, reply }
      ]);
      if (reply.profile_updates.length) {
        setProfile(await api.profile());
        setNotice("Your explicit investor preference was saved to durable memory.");
      }
    } catch (reason) {
      setEntries((current) => current.filter((item) => item.id !== userEntry.id));
      setQuestion(trimmed);
      setError(reason instanceof Error ? reason.message : "Research request failed.");
    } finally {
      setSending(false);
    }
  }

  async function logout() {
    await api.logout().catch(() => undefined);
    window.location.assign("/login");
  }

  if (loading) {
    return <main className="loading-shell">Preparing your research workspace...</main>;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <Link href="/" className="brand">Sentellent <span>Equity Analyst</span></Link>
        <nav>
          <Link href="/profile">Investor profile</Link>
          <button className="quiet-button" onClick={logout}>Sign out</button>
        </nav>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">GROUNDED RESEARCH FOR NSE / BSE</p>
          <h1>Your context-aware Indian equity research chief of staff.</h1>
          <p className="muted">
            {user?.display_name || user?.email || "Investor"}, answers are retrieved from your ingested
            sources, cited inline, and presented in INR.
          </p>
        </div>
        <aside className="safety-card">
          <span className="safety-dot" />
          <div>
            <strong>Evidence-first mode</strong>
            <p>Unsupported facts are refused; profile rules are hard filters.</p>
          </div>
        </aside>
      </section>

      {error && <p className="error-banner">{error}</p>}
      {notice && <p className="notice-banner">{notice}</p>}

      <section className="workspace">
        <aside className="sidebar">
          <div className="panel">
            <p className="eyebrow">YOUR UNIVERSE</p>
            <h2>Follow a ticker</h2>
            <label className="search-field">
              <span>Search NSE/BSE company</span>
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="RELIANCE, TCS, HDFCBANK..." />
            </label>
            {matches.length > 0 && (
              <div className="search-results">
                {matches.map((stock) => (
                  <button key={stock.id} onClick={() => addFollow(stock)}>
                    <strong>{stock.symbol}</strong>
                    <span>{stock.company_name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="follow-list">
            {follows.length ? follows.map((follow) => (
              <article className="follow-card" key={follow.id}>
                <div>
                  <strong>{follow.stock.symbol}</strong>
                  <span>{follow.stock.company_name}</span>
                </div>
                <span className={"status status-" + (follow.latest_job?.status || "idle")}>
                  {statusLabel(follow.latest_job?.status)}
                </span>
                <button className="text-link compact" onClick={() => refresh(follow.stock.symbol)}>Refresh</button>
              </article>
            )) : (
              <div className="empty-state">
                <strong>Start with one ticker.</strong>
                <span>Follow it to enqueue fundamentals, recent news, and price ingestion.</span>
              </div>
            )}
          </div>

          <div className="panel profile-summary">
            <p className="eyebrow">INVESTOR MEMORY</p>
            <h3>{activeProfile.risk_tolerance || "Risk not set"}</h3>
            <p>{(activeProfile.objectives || []).join(" · ") || "No objectives saved yet"}</p>
            {activeProfile.avoid_high_debt && <small>High-debt companies excluded</small>}
            <Link href="/profile" className="text-link">Edit profile</Link>
          </div>
        </aside>

        <section className="chat-panel panel">
          <div className="chat-header">
            <div>
              <p className="eyebrow">RESEARCH CHAT</p>
              <h2>Ask a grounded question</h2>
            </div>
            <span className="inr-chip">All money in INR</span>
          </div>

          <div className="suggestions">
            {[
              "What is the sentiment on TCS this week?",
              "I am a conservative, dividend-focused investor and avoid high-debt companies.",
              "Recommend stocks for my profile."
            ].map((example) => (
              <button key={example} onClick={() => setQuestion(example)}>{example}</button>
            ))}
          </div>

          <div className="chat-log" aria-live="polite">
            {entries.length === 0 && (
              <div className="empty-chat">
                <h3>Evidence before opinion.</h3>
                <p>Follow and ingest a ticker, then ask a question. Citations and source excerpts appear with every grounded answer.</p>
              </div>
            )}
            {entries.map((entry) => (
              <article className={"message " + entry.role} key={entry.id}>
                <span className="message-role">{entry.role === "user" ? "You" : "Analyst"}</span>
                <div className="message-body">
                  {entry.text.split("\n").map((line, index) => <p key={entry.id + index}>{line || "\u00a0"}</p>)}
                  {entry.reply?.recommendations.map((item) => (
                    <div className="recommendation" key={item.stock.id}>
                      <strong>{item.stock.symbol}</strong>
                      <span>{item.score}/100</span>
                      <p>{item.reasons.join(" ")}</p>
                    </div>
                  ))}
                  {entry.reply?.data_gaps.map((gap) => <p className="data-gap" key={gap}>Data gap: {gap}</p>)}
                  {entry.reply?.citations.length ? (
                    <div className="citations">
                      <strong>Sources</strong>
                      {entry.reply.citations.map((citation) => (
                        <a href={citation.url} key={citation.id} target="_blank" rel="noreferrer">
                          <span>[{citation.id}]</span>
                          <div>
                            <b>{citation.title}</b>
                            <small>{citation.publisher} · {citation.excerpt}</small>
                          </div>
                        </a>
                      ))}
                    </div>
                  ) : null}
                </div>
              </article>
            ))}
            {sending && <div className="assistant-thinking">Retrieving evidence, applying your profile rules, and validating citations...</div>}
          </div>

          <form className="chat-composer" onSubmit={ask}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about a followed ticker or state an investor preference..."
              rows={3}
            />
            <button className="button button-primary" type="submit" disabled={sending || !question.trim()}>
              {sending ? "Researching..." : "Ask analyst"}
            </button>
          </form>
          <p className="fine-print">Research information only, not investment advice. Sources can be incomplete or stale.</p>
        </section>
      </section>
    </main>
  );
}
