import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useShellBootstrap } from "../shell/context";

const LAB_CATALOG_SOURCE = (
	import.meta.env.VITE_LAB_CATALOG_SOURCE ?? "stub"
).toLowerCase();

export type LabDifficulty = "easy" | "medium";
type DifficultyChoice = LabDifficulty | "hard";

export type LabCatalogItem = {
	id: string;
	slug: string;
	name: string;
	summary: string;
	capabilities: {
		supports_resume: boolean;
		supports_uploads: boolean;
	};
};

const STUB_LABS: LabCatalogItem[] = [
	{
		id: "11111111-1111-1111-1111-111111111111",
		slug: "prompt-injection",
		name: "Indirect Prompt Injection",
		summary:
			"Practice indirect prompt-injection attack patterns against a baseline runtime.",
		capabilities: {
			supports_resume: true,
			supports_uploads: false,
		},
	},
	{
		id: "22222222-2222-2222-2222-222222222222",
		slug: "rag-poisoning",
		name: "RAG Poisoning",
		summary: "Explore retrieval poisoning behaviors and mitigation workflows.",
		capabilities: {
			supports_resume: true,
			supports_uploads: false,
		},
	},
	{
		id: "33333333-3333-3333-3333-333333333333",
		slug: "tool-misuse",
		name: "Tool Misuse",
		summary: "Identify unsafe tool invocation paths and guardrail failures.",
		capabilities: {
			supports_resume: true,
			supports_uploads: false,
		},
	},
];

async function fetchLabsFromApi(apiBaseUrl: string): Promise<LabCatalogItem[]> {
	const response = await fetch(`${apiBaseUrl}/api/v1/labs`, {
		method: "GET",
		headers: {
			Authorization: "Bearer local:kane:learner",
			"Content-Type": "application/json",
		},
	});

	if (!response.ok) {
		throw new Error(`Lab catalog request failed (HTTP ${response.status})`);
	}

	const payload = (await response.json()) as unknown;
	if (typeof payload !== "object" || payload === null || !("labs" in payload)) {
		throw new Error("Lab catalog response did not include labs[]");
	}

	const rawLabs = payload.labs;
	if (!Array.isArray(rawLabs)) {
		throw new Error("Lab catalog response has invalid labs[] shape");
	}

	return rawLabs
		.filter((item): item is LabCatalogItem => {
			if (typeof item !== "object" || item === null) {
				return false;
			}
			if (
				!("id" in item) ||
				!("slug" in item) ||
				!("name" in item) ||
				!("summary" in item) ||
				!("capabilities" in item)
			) {
				return false;
			}

			const capabilities = item.capabilities;
			return (
				typeof item.id === "string" &&
				typeof item.slug === "string" &&
				typeof item.name === "string" &&
				typeof item.summary === "string" &&
				typeof capabilities === "object" &&
				capabilities !== null &&
				"supports_resume" in capabilities &&
				"supports_uploads" in capabilities &&
				typeof capabilities.supports_resume === "boolean" &&
				typeof capabilities.supports_uploads === "boolean"
			);
		})
		.map((item) => ({
			id: item.id,
			slug: item.slug,
			name: item.name,
			summary: item.summary,
			capabilities: {
				supports_resume: item.capabilities.supports_resume,
				supports_uploads: item.capabilities.supports_uploads,
			},
		}));
}

export async function loadLabCatalog(
	apiBaseUrl: string,
): Promise<LabCatalogItem[]> {
	if (LAB_CATALOG_SOURCE === "empty") {
		return [];
	}

	if (LAB_CATALOG_SOURCE === "api") {
		return fetchLabsFromApi(apiBaseUrl);
	}

	return STUB_LABS;
}

function extractSessionId(payload: unknown): string | undefined {
	if (
		typeof payload === "object" &&
		payload !== null &&
		"session" in payload &&
		typeof payload.session === "object" &&
		payload.session !== null &&
		"id" in payload.session &&
		typeof payload.session.id === "string"
	) {
		return payload.session.id;
	}
	if (
		typeof payload === "object" &&
		payload !== null &&
		"id" in payload &&
		typeof payload.id === "string"
	) {
		return payload.id;
	}
	return undefined;
}

export async function createSessionForLab(
	apiBaseUrl: string,
	labId: string,
	labDifficulty: LabDifficulty = "medium",
): Promise<string> {
	const response = await fetch(`${apiBaseUrl}/api/v1/sessions`, {
		method: "POST",
		headers: {
			Authorization: "Bearer local:kane:learner",
			"Idempotency-Key": `frontend-create-session-${crypto.randomUUID()}`,
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			lab_id: labId,
			lab_difficulty: labDifficulty,
		}),
	});

	if (!response.ok) {
		throw new Error(`Session create failed (HTTP ${response.status})`);
	}

	const payload = (await response.json()) as unknown;
	const sessionId = extractSessionId(payload);
	if (!sessionId) {
		throw new Error(
			"Session create succeeded but response did not include session id",
		);
	}

	return sessionId;
}

type LabCatalogProps = {
	apiBaseUrl: string;
	learnerLabel: string;
	mode?: "demo" | "debug";
	loadLabs?: (apiBaseUrl: string) => Promise<LabCatalogItem[]>;
	createSession?: (
		apiBaseUrl: string,
		labId: string,
		labDifficulty: LabDifficulty,
	) => Promise<string>;
	onOpenSession: (sessionId: string, labName?: string) => void;
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
	createSession = createSessionForLab,
	onOpenSession,
}: LabCatalogProps) {
	const [labs, setLabs] = useState<LabCatalogItem[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [loadError, setLoadError] = useState<string | null>(null);
	const [creatingLabId, setCreatingLabId] = useState<string | null>(null);
	const [createError, setCreateError] = useState<string | null>(null);
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

	const launchLab = async (labId: string) => {
		const chosenDifficulty =
			mode === "debug"
				? selectedDifficulty
				: getCardDifficulty(selectedDifficultyByLab, labId);
		if (chosenDifficulty === "hard") {
			setCreateError("Hard difficulty is not available yet.");
			return;
		}
		setCreatingLabId(labId);
		setCreateError(null);
		try {
			const sessionId = await createSession(
				apiBaseUrl,
				labId,
				chosenDifficulty,
			);
			const selectedLab = labs.find((lab) => lab.id === labId);
			onOpenSession(sessionId, selectedLab?.name);
		} catch (error) {
			setCreateError(
				error instanceof Error ? error.message : "Session create failed",
			);
		} finally {
			setCreatingLabId(null);
		}
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
						disabled={creatingLabId !== null}
					>
						<option value="medium">Medium</option>
						<option value="easy">Easy</option>
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
							const isCreatingThisLab = creatingLabId === lab.id;
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
										onClick={() => void launchLab(lab.id)}
										disabled={creatingLabId !== null}
									>
										{isCreatingThisLab ? "Creating session..." : "Launch lab"}
									</button>
								</article>
							);
						})}
					</div>
				)}

				{createError && (
					<p style={{ margin: "12px 0 0", color: "#9f1239" }}>
						Session launch error: {createError}
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
						const isCreatingThisLab = creatingLabId === lab.id;
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
												difficulty === "hard" || creatingLabId !== null;
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
													{difficulty === "hard" ? "Hard (Soon)" : difficulty}
												</button>
											);
										})}
									</div>
									<button
										type="button"
										onClick={() => void launchLab(lab.id)}
										disabled={creatingLabId !== null}
										style={{
											background: isCreatingThisLab ? "#123652" : "#1a8fff",
											color: "#02101a",
											border: 0,
											padding: "10px 14px",
											borderRadius: 10,
											fontWeight: 800,
											cursor: creatingLabId !== null ? "wait" : "pointer",
										}}
									>
										{isCreatingThisLab ? "Creating session..." : "Launch lab"}
									</button>
								</div>
							</article>
						);
					})}
				</div>
			)}

			{createError && (
				<p style={{ margin: "12px 0 0", color: "#ffd0df" }}>
					Session launch error: {createError}
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
			onOpenSession={(sessionId, labName) => {
				navigate(`/sessions/${sessionId}`, { state: { labName } });
			}}
		/>
	);
}
