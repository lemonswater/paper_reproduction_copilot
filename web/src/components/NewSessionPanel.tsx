import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import type { JobView, UiConfig } from "../api/types";
import {
  ResourceWizard,
  type PublishedResourcePair,
} from "./ResourceWizard";

type Props = {
  onClose: () => void;
  onCreated: (job: JobView) => void;
};

export function NewSessionPanel({ onClose, onCreated }: Props) {
  const [config, setConfig] = useState<UiConfig | null>(null);
  const [resources, setResources] = useState<PublishedResourcePair | null>(null);
  const [goal, setGoal] = useState("复现论文 main result");
  const [profileId, setProfileId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.config()
      .then((value) => {
        setConfig(value);
        setProfileId(value.default_execution_profile);
      })
      .catch((caught) => {
        setError(caught instanceof Error ? caught.message : "配置加载失败");
      });
  }, []);

  async function createJob(event: FormEvent) {
    event.preventDefault();
    if (!resources || !profileId) return;
    setBusy(true);
    setError(null);
    try {
      const job = await api.createJob({
        paperResourceId: resources.paper.resource_id,
        repoResourceId: resources.repository.resource_id,
        experimentGoal: goal.trim(),
        executionProfileId: profileId,
      });
      onCreated(job);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Job 创建失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section className="new-session-panel" role="dialog" aria-modal="true">
        <header>
          <div>
            <p className="eyebrow">New reproduction session</p>
            <h2>Fix inputs before the agent starts</h2>
          </div>
          <button aria-label="Close" onClick={onClose}>Close</button>
        </header>

        {!resources ? (
          <ResourceWizard onReady={setResources} />
        ) : (
          <form onSubmit={createJob}>
            <p>
              Inputs published: {resources.paper.resource_id} / {resources.repository.resource_id}
            </p>
            <label>
              Experiment goal
              <textarea
                required
                maxLength={4000}
                value={goal}
                onChange={(event) => setGoal(event.currentTarget.value)}
              />
            </label>
            <label>
              Execution profile
              <select
                required
                value={profileId}
                onChange={(event) => setProfileId(event.currentTarget.value)}
              >
                {config?.execution_profiles.map((profile) => (
                  <option key={profile.profile_id} value={profile.profile_id}>
                    {profile.profile_id} / {profile.backend} / {profile.network_policy}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary-action" disabled={busy || !config} type="submit">
              Create session
            </button>
          </form>
        )}
        {error && <p className="inline-error" role="alert">{error}</p>}
      </section>
    </div>
  );
}
