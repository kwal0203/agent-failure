import { useMemo, useState } from "react";
import type { EventGranularity, EventType, TimelineEvent } from "../types";
import { DEMO_H2_STYLE } from "../ui";

type FeedbackColumnProps = {
	feedbackLoading: boolean;
	feedbackError: string | null;
	timelineEvents: TimelineEvent[];
};

const EVENT_TYPE_FILTERS: Array<{ label: string; value: "all" | EventType }> = [
	{ label: "All", value: "all" },
	{ label: "Important", value: "important" },
	{ label: "Attacker actions", value: "attacker_action" },
	{ label: "Agent actions", value: "agent_action" },
	{ label: "Tool calls", value: "tool_call" },
	{ label: "System", value: "system" },
	{ label: "Learning explanations", value: "explanation" },
];

const GRANULARITY_FILTERS: Array<{ label: string; value: EventGranularity }> = [
	{ label: "High-level", value: "high" },
	{ label: "Detailed", value: "detailed" },
	{ label: "Full trace", value: "full" },
];

const GRANULARITY_RANK: Record<EventGranularity, number> = {
	high: 1,
	detailed: 2,
	full: 3,
};

const EVENT_TYPE_BADGE: Record<EventType, string> = {
	important: "important",
	attacker_action: "attacker",
	agent_action: "agent",
	tool_call: "tool",
	system: "system",
	explanation: "learning",
};

function isTokenExposureEvent(event: TimelineEvent): boolean {
	const haystack =
		`${event.title} ${event.description} ${event.details ?? ""}`.toLowerCase();
	return (
		haystack.includes("token exposed") ||
		haystack.includes("system_token") ||
		haystack.includes("orch-7429")
	);
}

function eventTone(event: TimelineEvent): {
	border: string;
	background: string;
	titleColor: string;
	bodyColor: string;
} {
	if (isTokenExposureEvent(event)) {
		return {
			border: "1px solid #d14c4c",
			background: "rgba(93, 21, 21, 0.35)",
			titleColor: "#ffd7d7",
			bodyColor: "#ffe9e9",
		};
	}

	switch (event.type) {
		case "important":
			return {
				border: "1px solid #d18a3e",
				background: "rgba(94, 60, 20, 0.3)",
				titleColor: "#ffe4c0",
				bodyColor: "#ffefda",
			};
		case "attacker_action":
			return {
				border: "1px solid #8a4fd1",
				background: "rgba(63, 32, 96, 0.28)",
				titleColor: "#eadbff",
				bodyColor: "#f2e9ff",
			};
		case "agent_action":
			return {
				border: "1px solid #3e9a72",
				background: "rgba(24, 70, 52, 0.3)",
				titleColor: "#d8ffe8",
				bodyColor: "#e9fff2",
			};
		case "tool_call":
			return {
				border: "1px solid #3a8ec2",
				background: "rgba(22, 56, 82, 0.3)",
				titleColor: "#d6efff",
				bodyColor: "#e8f6ff",
			};
		case "system":
			return {
				border: "1px solid #8a95a1",
				background: "rgba(41, 49, 56, 0.3)",
				titleColor: "#e5ebf2",
				bodyColor: "#f1f5f9",
			};
		case "explanation":
			return {
				border: "1px solid #4a86c6",
				background: "rgba(20, 50, 78, 0.3)",
				titleColor: "#d6ecff",
				bodyColor: "#e9f4ff",
			};
		default:
			return {
				border: "1px solid #8ea1b4",
				background: "rgba(26, 38, 49, 0.18)",
				titleColor: "#e6edf3",
				bodyColor: "#f2f5f7",
			};
	}
}

function formatTimestamp(isoTs: string): string {
	const date = new Date(isoTs);
	if (Number.isNaN(date.getTime())) return isoTs;
	return date.toLocaleTimeString();
}

function eventIcon(type: EventType): string {
	switch (type) {
		case "important":
			return "!";
		case "attacker_action":
			return "A";
		case "agent_action":
			return "G";
		case "tool_call":
			return "T";
		case "system":
			return "S";
		case "explanation":
			return "L";
		default:
			return "E";
	}
}

export function FeedbackColumn({
	feedbackLoading,
	feedbackError,
	timelineEvents,
}: FeedbackColumnProps) {
	const [selectedType, setSelectedType] = useState<"all" | EventType>("all");
	const [selectedGranularity, setSelectedGranularity] =
		useState<EventGranularity>("detailed");

	const sortedEvents = useMemo(
		() =>
			[...timelineEvents].sort(
				(a, b) =>
					new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
			),
		[timelineEvents],
	);

	const filteredEvents = useMemo(() => {
		const maxGranularity = GRANULARITY_RANK[selectedGranularity];
		return sortedEvents.filter((event) => {
			const typeMatches = selectedType === "all" || event.type === selectedType;
			const granularityMatches =
				GRANULARITY_RANK[event.granularity] <= maxGranularity;
			return typeMatches && granularityMatches;
		});
	}, [sortedEvents, selectedType, selectedGranularity]);

	return (
		<section
			style={{
				border: "1px solid #ddd",
				borderRadius: 8,
				padding: 16,
				textAlign: "left",
				display: "grid",
				gridTemplateRows: "auto minmax(0, 1fr) auto auto",
				flex: "1 1 auto",
				gap: 12,
				height: "100%",
				minHeight: 0,
				maxHeight: "100%",
				boxSizing: "border-box",
				overflow: "hidden",
			}}
		>
			<h2 style={DEMO_H2_STYLE}>Event Timeline</h2>

			{feedbackLoading && (
				<p style={{ margin: 0 }}>Loading learner feedback...</p>
			)}
			{feedbackError && (
				<p style={{ color: "red", margin: 0 }}>Error: {feedbackError}</p>
			)}

			<div style={{ flex: "1 1 0%", minHeight: 0, overflowY: "auto" }}>
				{filteredEvents.length === 0 ? (
					<p style={{ margin: 0, opacity: 0.85 }}>
						No events for current filters.
					</p>
				) : (
					<div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
						{filteredEvents.map((event) => {
							const tone = eventTone(event);
							return (
								<div
									key={event.id}
									style={{
										border: tone.border,
										background: tone.background,
										borderRadius: 8,
										padding: 10,
									}}
								>
									<div
										style={{
											display: "flex",
											justifyContent: "space-between",
											gap: 8,
											alignItems: "center",
										}}
									>
										<p
											style={{
												margin: 0,
												fontWeight: 600,
												color: tone.titleColor,
											}}
										>
											[{eventIcon(event.type)}] {event.title}
										</p>
										<span
											style={{
												fontSize: 11,
												opacity: 0.9,
												color: tone.bodyColor,
											}}
										>
											{EVENT_TYPE_BADGE[event.type]} •{" "}
											{formatTimestamp(event.timestamp)}
										</span>
									</div>
									<p
										style={{
											margin: "6px 0 0 0",
											fontSize: 13,
											color: tone.bodyColor,
										}}
									>
										{event.description}
									</p>
									{event.details && (
										<details style={{ marginTop: 6, color: tone.bodyColor }}>
											<summary>Details</summary>
											<p style={{ margin: "6px 0 0 0", fontSize: 13 }}>
												{event.details}
											</p>
										</details>
									)}
								</div>
							);
						})}
					</div>
				)}
			</div>

			<div>
				<p style={{ margin: "0 0 8px 0", fontWeight: 600 }}>Event type</p>
				<div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
					{EVENT_TYPE_FILTERS.map((filter) => {
						const isActive = selectedType === filter.value;
						return (
							<button
								key={filter.value}
								type="button"
								onClick={() => setSelectedType(filter.value)}
								aria-pressed={isActive}
								style={{
									padding: "4px 8px",
									fontSize: 12,
									borderRadius: 999,
									border: isActive ? "1px solid #4ea4d9" : "1px solid #9aa7b3",
									background: isActive ? "rgba(26, 76, 107, 0.55)" : "#fff",
									color: isActive ? "#d6f1ff" : "#203040",
									cursor: "pointer",
								}}
							>
								{filter.label}
							</button>
						);
					})}
				</div>
			</div>

			<div>
				<p style={{ margin: "0 0 8px 0", fontWeight: 600 }}>Granularity</p>
				<div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
					{GRANULARITY_FILTERS.map((filter) => {
						const isActive = selectedGranularity === filter.value;
						return (
							<button
								key={filter.value}
								type="button"
								onClick={() => setSelectedGranularity(filter.value)}
								aria-pressed={isActive}
								style={{
									padding: "4px 8px",
									fontSize: 12,
									borderRadius: 999,
									border: isActive ? "1px solid #4ea4d9" : "1px solid #9aa7b3",
									background: isActive ? "rgba(26, 76, 107, 0.55)" : "#fff",
									color: isActive ? "#d6f1ff" : "#203040",
									cursor: "pointer",
								}}
							>
								{filter.label}
							</button>
						);
					})}
				</div>
			</div>
		</section>
	);
}
