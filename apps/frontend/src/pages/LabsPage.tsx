import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useShellBootstrap } from "../shell/context";
import {
  type LabCatalogItem,
  type LabDifficulty,
  loadLabCatalog,
} from "./labCatalogApi";

export type { LabCatalogItem, LabDifficulty } from "./labCatalogApi";

type DifficultyChoice = LabDifficulty | "hard";

type LabCatalogProps = {
  apiBaseUrl: string;
  learnerLabel: string;
  mode?: "demo" | "debug";
  loadLabs?: (apiBaseUrl: string) => Promise<LabCatalogItem[]>;
  onOpenPreLab: (selection: {
    labId: string;
    labName: string;
    labSlug: string;
    labSummary: string;
    labDifficulty: LabDifficulty;
  }) => void;
};

function getCardDifficulty(
  selectedByLab: Record<string, DifficultyChoice>,
  labId: string,
): DifficultyChoice {
  return selectedByLab[labId] ?? "medium";
}

export function LabCatalog({
  apiBaseUrl,
  learnerLabel,
  mode = "demo",
  loadLabs = loadLabCatalog,
  onOpenPreLab,
}: LabCatalogProps) {
  const [labs, setLabs] = useState<LabCatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [launchingLabId, setLaunchingLabId] = useState<string | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [selectedDifficulty, setSelectedDifficulty] =
    useState<DifficultyChoice>("medium");
  const [selectedDifficultyByLab, setSelectedDifficultyByLab] = useState<
    Record<string, DifficultyChoice>
  >({});

  const refreshLabs = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const loadedLabs = await loadLabs(apiBaseUrl);
      setLabs(loadedLabs);
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Failed to load lab catalog",
      );
      setLabs([]);
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl, loadLabs]);

  useEffect(() => {
    void refreshLabs();
  }, [refreshLabs]);

  const launchLab = (labId: string) => {
    const chosenDifficulty =
      mode === "debug"
        ? selectedDifficulty
        : getCardDifficulty(selectedDifficultyByLab, labId);
    if (chosenDifficulty === "easy" || chosenDifficulty === "hard") {
      setLaunchError("Easy and Hard difficulties are not available yet.");
      return;
    }
    const selectedLab = labs.find((lab) => lab.id === labId);
    if (!selectedLab) {
      setLaunchError("Selected lab could not be loaded.");
      return;
    }
    setLaunchingLabId(labId);
    setLaunchError(null);
    onOpenPreLab({
      labId: selectedLab.id,
      labName: selectedLab.name,
      labSlug: selectedLab.slug,
      labSummary: selectedLab.summary,
      labDifficulty: chosenDifficulty,
    });
  };

  if (mode === "debug") {
    return (
      <section>
        <h1 style={{ margin: "0 0 12px" }}>Labs</h1>
        <p style={{ margin: "0 0 14px" }}>
          Demo shell is active for <strong>{learnerLabel}</strong>.
        </p>
        <label
          htmlFor="lab-difficulty"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            margin: "0 0 14px",
          }}
        >
          Difficulty
          <select
            id="lab-difficulty"
            value={selectedDifficulty}
            onChange={(event) =>
              setSelectedDifficulty(event.target.value as DifficultyChoice)
            }
            disabled={launchingLabId !== null}
          >
            <option value="medium">Medium</option>
            <option value="easy" disabled>
              Easy (Coming soon)
            </option>
            <option value="hard">Hard (Coming soon)</option>
          </select>
        </label>

        {isLoading && (
          <p style={{ margin: "0 0 12px" }}>Loading lab catalog...</p>
        )}

        {loadError && (
          <div
            style={{
              border: "1px solid #fecaca",
              background: "#fff1f2",
              borderRadius: 10,
              padding: 12,
              marginBottom: 12,
              maxWidth: 800,
            }}
          >
            <p style={{ margin: "0 0 8px", color: "#9f1239" }}>
              Error: {loadError}
            </p>
            <button type="button" onClick={() => void refreshLabs()}>
              Retry
            </button>
          </div>
        )}

        {!isLoading && !loadError && labs.length === 0 && (
          <div
            style={{
              border: "1px solid #cdd5e2",
              borderRadius: 10,
              background: "#fff",
              padding: 16,
              maxWidth: 800,
            }}
          >
            <p style={{ margin: 0 }}>
              No launchable labs are currently available.
            </p>
          </div>
        )}

        {!isLoading && !loadError && labs.length > 0 && (
          <div
            style={{
              display: "grid",
              gap: 12,
              maxWidth: 900,
              margin: "0 auto",
            }}
          >
            {labs.map((lab) => {
              const isLaunchingThisLab = launchingLabId === lab.id;
              return (
                <article
                  key={lab.id}
                  style={{
                    border: "1px solid #cdd5e2",
                    borderRadius: 10,
                    background: "#fff",
                    padding: 16,
                    textAlign: "left",
                  }}
                >
                  <h2 style={{ margin: "0 0 8px", fontSize: 20 }}>
                    {lab.name}
                  </h2>
                  <p style={{ margin: "0 0 8px", opacity: 0.9 }}>
                    {lab.summary}
                  </p>
                  <p style={{ margin: "0 0 10px", fontSize: 13, opacity: 0.8 }}>
                    slug: <code>{lab.slug}</code>
                  </p>
                  <p style={{ margin: "0 0 12px", fontSize: 13 }}>
                    resume: {lab.capabilities.supports_resume ? "yes" : "no"} |
                    uploads: {lab.capabilities.supports_uploads ? "yes" : "no"}
                  </p>
                  <button
                    type="button"
                    onClick={() => launchLab(lab.id)}
                    disabled={launchingLabId !== null}
                  >
                    {isLaunchingThisLab ? "Opening briefing..." : "Launch lab"}
                  </button>
                </article>
              );
            })}
          </div>
        )}

        {launchError && (
          <p style={{ margin: "12px 0 0", color: "#9f1239" }}>
            Session launch error: {launchError}
          </p>
        )}
      </section>
    );
  }

  return (
    <section
      style={{
        color: "#d8f7ff",
        background:
          "radial-gradient(circle at 12% -10%, rgba(0, 255, 200, 0.18), transparent 38%), radial-gradient(circle at 88% 2%, rgba(0, 140, 255, 0.25), transparent 42%), #07111b",
        border: "1px solid #14324a",
        borderRadius: 16,
        padding: 20,
      }}
    >
      <h1
        style={{
          margin: "0 0 8px",
          fontSize: 34,
          letterSpacing: 0.8,
          textAlign: "center",
          color: "#f0fdff",
          textShadow: "0 0 14px rgba(62, 224, 255, 0.45)",
        }}
      >
        Labs
      </h1>
      {isLoading && (
        <p style={{ margin: "0 0 12px", color: "#9bcde0" }}>
          Loading lab catalog...
        </p>
      )}

      {loadError && (
        <div
          style={{
            border: "1px solid #7a2541",
            background: "rgba(110, 22, 49, 0.3)",
            borderRadius: 10,
            padding: 12,
            marginBottom: 12,
            maxWidth: 800,
          }}
        >
          <p style={{ margin: "0 0 8px", color: "#ffc6d8" }}>
            Error: {loadError}
          </p>
          <button type="button" onClick={() => void refreshLabs()}>
            Retry
          </button>
        </div>
      )}

      {!isLoading && !loadError && labs.length === 0 && (
        <div
          style={{
            border: "1px solid #204760",
            borderRadius: 10,
            background: "rgba(7, 20, 31, 0.85)",
            padding: 16,
            maxWidth: 800,
          }}
        >
          <p style={{ margin: 0, color: "#a7d2e3" }}>
            No launchable labs are currently available.
          </p>
        </div>
      )}

      {!isLoading && !loadError && labs.length > 0 && (
        <div
          style={{
            display: "grid",
            gap: 12,
            maxWidth: 900,
            margin: "0 auto",
          }}
        >
          {labs.map((lab) => {
            const isLaunchingThisLab = launchingLabId === lab.id;
            const cardDifficulty = getCardDifficulty(
              selectedDifficultyByLab,
              lab.id,
            );
            return (
              <article
                key={lab.id}
                style={{
                  border: "1px solid #1f4460",
                  borderRadius: 12,
                  background:
                    "linear-gradient(160deg, rgba(11,27,42,0.98), rgba(8,18,31,0.95))",
                  padding: 16,
                  textAlign: "left",
                }}
              >
                <h2
                  style={{ margin: "0 0 8px", fontSize: 22, color: "#f3feff" }}
                >
                  {lab.name}
                </h2>
                <p style={{ margin: "0 0 14px", color: "#9bcde0" }}>
                  {lab.summary}
                </p>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                    flexWrap: "wrap",
                  }}
                >
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {(["easy", "medium", "hard"] as const).map((difficulty) => {
                      const selected = cardDifficulty === difficulty;
                      const disabled =
                        difficulty === "easy" ||
                        difficulty === "hard" ||
                        launchingLabId !== null;
                      const accent =
                        difficulty === "easy"
                          ? "#25f2a2"
                          : difficulty === "medium"
                            ? "#31a7ff"
                            : "#c67dff";
                      return (
                        <button
                          key={difficulty}
                          type="button"
                          onClick={() =>
                            setSelectedDifficultyByLab((previous) => ({
                              ...previous,
                              [lab.id]: difficulty,
                            }))
                          }
                          disabled={disabled}
                          style={{
                            border: selected
                              ? `1px solid ${accent}`
                              : "1px solid #204760",
                            background: selected
                              ? "rgba(10, 33, 49, 0.95)"
                              : "#0b1a29",
                            color: selected ? "#f2fdff" : "#8fb7cb",
                            padding: "8px 10px",
                            borderRadius: 10,
                            fontWeight: 700,
                            textTransform: "capitalize",
                            cursor: disabled ? "not-allowed" : "pointer",
                            opacity: disabled ? 0.55 : 1,
                            boxShadow: selected
                              ? `0 0 0 2px ${accent}30`
                              : "none",
                          }}
                        >
                          {difficulty === "easy"
                            ? "Easy (Soon)"
                            : difficulty === "hard"
                              ? "Hard (Soon)"
                              : difficulty}
                        </button>
                      );
                    })}
                  </div>
                  <button
                    type="button"
                    onClick={() => launchLab(lab.id)}
                    disabled={launchingLabId !== null}
                    style={{
                      background: isLaunchingThisLab ? "#123652" : "#1a8fff",
                      color: "#02101a",
                      border: 0,
                      padding: "10px 14px",
                      borderRadius: 10,
                      fontWeight: 800,
                      cursor: launchingLabId !== null ? "wait" : "pointer",
                    }}
                  >
                    {isLaunchingThisLab ? "Opening briefing..." : "Launch lab"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {launchError && (
        <p style={{ margin: "12px 0 0", color: "#ffd0df" }}>
          Session launch error: {launchError}
        </p>
      )}
    </section>
  );
}

export default function LabsPage() {
  const bootstrap = useShellBootstrap();
  const navigate = useNavigate();

  return (
    <LabCatalog
      apiBaseUrl={bootstrap.apiBaseUrl}
      learnerLabel={bootstrap.learnerLabel}
      mode={bootstrap.mode}
      onOpenPreLab={(selection) => {
        navigate(`/labs/${selection.labId}/pre-lab`, { state: selection });
      }}
    />
  );
}
