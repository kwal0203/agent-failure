import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "./App";

function renderAt(path: string) {
	return render(
		<MemoryRouter initialEntries={[path]}>
			<App />
		</MemoryRouter>,
	);
}

describe("App shell routing", () => {
	it("routes root path to labs page", async () => {
		renderAt("/");

		expect(
			await screen.findByRole("heading", { name: "Labs" }),
		).toBeInTheDocument();
		expect(screen.getByText(/Cyberrange Demo Surface/i)).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Back to Labs" }),
		).toBeInTheDocument();
	});

	it("renders history page in demo mode without top nav links", async () => {
		renderAt("/history");

		expect(
			await screen.findByRole("heading", { name: "History" }),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("link", { name: "Labs" }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("link", { name: "Trace" }),
		).not.toBeInTheDocument();
	});

	it("redirects unknown route to labs", async () => {
		renderAt("/missing/path");

		expect(
			await screen.findByRole("heading", { name: "Labs" }),
		).toBeInTheDocument();
	});
});
