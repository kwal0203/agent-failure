export type SessionMetadata = {
	id: string;
	lab_id: string | null;
	lab_version_id: string | null;
	state: string;
	runtime_substate: string | null;
	resume_mode: string;
	interactive: boolean;
	created_at: string;
	started_at: string | null;
	ended_at: string | null;
};

export type GetSessionMetadataResponse = {
	session: SessionMetadata;
};

export type TranscriptRole = "user" | "agent" | "policy" | "system";

export type TranscriptEntry = {
	role: TranscriptRole;
	content: string;
	timestamp: string;
};

export type LearnerFeedbackStatus =
	| "learned"
	| "progress"
	| "no_progress"
	| "session_terminal";

export type LearnerFeedbackItem = {
	status: LearnerFeedbackStatus;
	reason_code: string;
	evidence_snippet: string;
};

export type GetFeedbackResponse = {
	feedback: LearnerFeedbackItem[];
};

export type InjectSessionEmailResponse = {
	session_id: string;
	email_id: string | null;
	accepted: boolean;
};

export type ToolKey = "email" | "files" | "payloads" | "notes" | "recon";

export type SessionWorkspaceState = {
	selectedTool: ToolKey | null;
	toolPaneOpen: boolean;
	transcriptAutoScrollEnabled: boolean;
	feedbackPanelVisible: boolean;
};
