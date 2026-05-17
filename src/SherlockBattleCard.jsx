import React, { useState } from "react";

// Sherlock markdown summary (for "More Info" section)
const SHERLOCK_MARKDOWN = `
# Sherlock — Competitive Intelligence Platform

**What it does**: Sherlock is an internal platform for enterprise sales teams, monitoring market signals (calls, deals, reviews, competitor launches). It uses AI to detect changes, proposes updates to battle cards (with evidence), and instantly updates them on approval—keeping all downstream tools in sync.

---

## How Sherlock Works
1. **Signal Captured**  
   E.g., "Deel offered $499 for volume pricing."
2. **AI-Detected Change**  
   Sherlock compares this claim to the current battle card, proposes a diff, and gives a confidence score.
3. **One-Click Approve**  
   Analyst reviews & approves the update. Battle card is changed and synced in real time.

---

## Technical Highlights
- **AI-powered CDC pipeline**
- **Integrations**: CRM, Gong, G2, web monitoring
- **Realtime update/sync**: Battle cards, Seismic, Highspot, Redis cache
- **Stack**: React, Express, PostgreSQL, Drizzle ORM, Redis

---

## Example Scenario
>"Deel offered us $499 for volume — prices drop at 10+ employees."  
AI proposes: "Update Deel battle card section 'Pricing' from `$599` to `$499–$599` based on employee count (Confidence: 98%)"

---

## Outcomes (on approve)
- Battle card updated instantly
- Seismic sync triggered
- Redis cache refreshed
`;

export default function SherlockBattleCard() {
  const [showMore, setShowMore] = useState(false);

  return (
    <div style={{
      maxWidth: 680,
      margin: "2rem auto",
      background: "linear-gradient(120deg, #0b1526 80%, #1e293b 100%)",
      borderRadius: 18,
      boxShadow: "0 4px 42px #0006",
      color: "#eef0f6",
      fontFamily: "'Inter', sans-serif",
      border: "2px solid #2361f3",
      overflow: "hidden",
      letterSpacing: "0.01em"
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        padding: "1.5rem 2rem",
        borderBottom: "1px solid #26314c",
        background: "rgba(35,97,243,0.13)"
      }}>
        <div style={{
          width: 72, height: 72, borderRadius: "50%", background: "#2563eb", color: "#fff",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 36, fontWeight: 800, marginRight: 24
        }}>
          S
        </div>
        <div>
          <div style={{ fontSize: 25, fontWeight: 700, color: "#fff", lineHeight: 1.2 }}>
            Sherlock
          </div>
          <div style={{
            fontSize: 15, color: "#a2aacc", marginTop: 3, fontWeight: 500,
            letterSpacing: 0.1
          }}>
            Competitive Intelligence, Always Up-To-Date
          </div>
        </div>
      </div>

      {/* Value Prop / 3-step overview */}
      <div style={{padding: "2rem", paddingBottom: "1.5rem"}}>
        <div style={{
          background: "linear-gradient(90deg,rgba(35,97,243,.22),rgba(76,204,112,.10))",
          color: "#fff",
          fontWeight: 600,
          fontSize: 24,
          padding: "12px 22px",
          marginBottom: 30,
          borderRadius: 11,
          textAlign: "center"
        }}>
          AI-driven battle cards. Market changes\u00a0\u2192\u00a0approved in one click.
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 38px 1fr 38px 1fr",
          gap: 0,
          marginBottom: 18,
          alignItems: "center"
        }}>
          <div style={{textAlign: "center"}}>
            <div style={{fontSize: 17, fontWeight: 700, marginBottom: 6, color: "#dcfce7"}}>Signal Captured</div>
            <div style={{fontSize: 14, color: "#b0bbd6", minHeight: 40}}>E.g., new CRM, Gong, or G2 signal lands in real-time</div>
          </div>
          <div style={{ textAlign: "center", fontSize: 34, color: "#38bdf8", fontWeight: 600 }}>→</div>
          <div style={{textAlign: "center"}}>
            <div style={{fontSize: 17, fontWeight: 700, marginBottom: 6, color: "#a5b4fc"}}>AI Detects Delta</div>
            <div style={{fontSize: 14, color: "#b0bbd6", minHeight: 40}}>LLM proposes changes to battle card with confidence score</div>
          </div>
          <div style={{ textAlign: "center", fontSize: 34, color: "#38bdf8", fontWeight: 600 }}>→</div>
          <div style={{textAlign: "center"}}>
            <div style={{fontSize: 17, fontWeight: 700, marginBottom: 6, color: "#7ff09b"}}>1-Click Update</div>
            <div style={{fontSize: 14, color: "#b0bbd6", minHeight: 40}}>Approve & sync instantly across platforms and cache</div>
          </div>
        </div>

        {/* Example */}
        <div style={{
          background: "#101828",
          borderRadius: 8,
          border: "1.2px solid #38bdf863",
          padding: "18px 20px",
          margin: "16px 0 0 0"
        }}>
          <div style={{fontSize: 13, color: "#68d198", fontWeight: 600, marginBottom: 6}}>Example Update</div>
          <div style={{fontWeight: 600, color: "#fff", marginBottom: 2}}>
            "Deel offered us $499 for volume — prices drop at 10+ employees."
          </div>
          <div style={{color: "#fed7aa", fontSize: 13, marginTop: 2}}>AI proposes: <span style={{color:'#bef264'}}>Update ‘Pricing’ from <b>$599</b> to <b>$499–$599</b></span> (Confidence: 98%)</div>
        </div>

        {/* Outcomes */}
        <div style={{marginTop: 20}}>
          <div style={{fontWeight: 600, color: "#38bdf8", marginBottom: 6}}>On Approve:</div>
          <ul style={{margin: 0, padding: 0, marginLeft: 13, color:"#facc15", fontSize: 14, lineHeight:1.7}}>
            <li>Battle card updated instantly</li>
            <li>Seismic/Highspot sync triggered</li>
            <li>Redis cache refreshed</li>
          </ul>
        </div>

        {/* More Info button */}
        <div style={{marginTop: 32, textAlign: "center"}}>
          <button
            onClick={() => setShowMore(x => !x)}
            style={{
              background: showMore ? "#1e293b" : "linear-gradient(90deg,#2563eb 80%,#22c55e 130%)",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "12px 38px",
              fontWeight: 700,
              fontSize: 16,
              boxShadow: showMore ? "none" : "0 2px 14px #0003",
              letterSpacing: "0.04em",
              outline: "none",
              cursor: "pointer",
              transition: "all .15s"
            }}
            aria-expanded={showMore}
          >
            {showMore ? "Hide Details" : "More Info"}
          </button>
        </div>
      </div>

      {/* Expanded markdown details - rendered simply as preformatted block for now */}
      {showMore && (
        <div
          style={{
            background: "#23272f",
            borderTop: "1.5px solid #2563eb55",
            padding: "2.1rem 2rem 2.1rem 2rem",
            fontFamily: "JetBrains Mono,monospace",
            fontSize: 15,
            color: "#d1cbdd",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            maxHeight: 410,
            overflowY: "auto"
          }}
        >
          {SHERLOCK_MARKDOWN}
        </div>
      )}
    </div>
  );
}
