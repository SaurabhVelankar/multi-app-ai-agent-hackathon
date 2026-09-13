"use client";

import { useMemo, useState } from "react";
import type { TriggerType } from "@/lib/types";

const SAMPLE_EMAIL = `{
  "fixture_id": "fixture-meeting-001",
  "subject": "Re: Q4 planning sync — can we meet?",
  "from": "sarah@example.com",
  "to": "me@example.com",
  "date": "2026-09-13T09:00:00Z",
  "body": "Hey! Can we get 30 minutes this week for Q4 roadmap? Monday or Tuesday afternoon works. Also send the project brief? — Sarah"
}`;

const SAMPLE_GOAL =
  "Schedule a 30m sync with Alex next Tuesday afternoon, write a Notion brief, and draft a confirmation email.";

type Props = {
  adminId: string;
  busy: boolean;
  onSubmit: (input: {
    trigger_type: TriggerType;
    trigger_payload: string | Record<string, unknown>;
    admin_id: string;
    source_id?: string;
  }) => Promise<void>;
};

export function TriggerPanel({ adminId, busy, onSubmit }: Props) {
  const [mode, setMode] = useState<TriggerType>("goal");
  const [goal, setGoal] = useState(SAMPLE_GOAL);
  const [emailJson, setEmailJson] = useState(SAMPLE_EMAIL);
  const [error, setError] = useState<string | null>(null);

  const canStart = useMemo(() => adminId.trim().length > 0, [adminId]);

  async function handleStart() {
    setError(null);
    if (!canStart) {
      setError("Pick or enter an admin id first.");
      return;
    }

    try {
      if (mode === "goal") {
        await onSubmit({
          trigger_type: "goal",
          trigger_payload: goal.trim(),
          admin_id: adminId.trim(),
          source_id: `goal-${Date.now()}`,
        });
        return;
      }

      const parsed = JSON.parse(emailJson) as Record<string, unknown>;
      await onSubmit({
        trigger_type: "email",
        trigger_payload: parsed,
        admin_id: adminId.trim(),
        source_id:
          typeof parsed.fixture_id === "string"
            ? parsed.fixture_id
            : `email-${Date.now()}`,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start run");
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Start a run</h2>
        <p>Outcome in → multi-app actions out.</p>
      </div>

      <div className="seg">
        <button
          type="button"
          className={mode === "goal" ? "seg-on" : ""}
          onClick={() => setMode("goal")}
        >
          Goal
        </button>
        <button
          type="button"
          className={mode === "email" ? "seg-on" : ""}
          onClick={() => setMode("email")}
        >
          Email fixture
        </button>
      </div>

      {mode === "goal" ? (
        <textarea
          className="field mono"
          rows={5}
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Describe the life outcome…"
        />
      ) : (
        <textarea
          className="field mono"
          rows={10}
          value={emailJson}
          onChange={(e) => setEmailJson(e.target.value)}
          spellCheck={false}
        />
      )}

      {error && <p className="err">{error}</p>}

      <button
        type="button"
        className="btn-primary"
        disabled={busy || !canStart}
        onClick={handleStart}
      >
        {busy ? "Running…" : "Start run"}
      </button>
    </section>
  );
}
