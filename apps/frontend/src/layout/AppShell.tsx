import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { BookOpen, FileText, Shield } from "lucide-react";
import { useMemo } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router";
import type { AuthUser } from "../auth/authContext";
import { useAuth } from "../auth/useAuth";
import { readFrontendConfig } from "../config";
import type { ShellBootstrap } from "../shell/context";

const frontendConfig = readFrontendConfig();
const bootstrap: ShellBootstrap = {
  mode: frontendConfig.uiMode,
  learnerLabel: "Demo Learner",
  apiBaseUrl: frontendConfig.apiBaseUrl,
};

const catalogNavItems = [
  { label: "Catalog", icon: BookOpen, to: "/labs" },
  { label: "Reports", icon: FileText, to: "/reports" },
];

function canViewPilotRequests(user: AuthUser | null): boolean {
  const groups = user?.groups?.map((group) => group.toLowerCase()) ?? [];
  return groups.includes("admin") || groups.includes("staff");
}

type ViewerProfile = {
  displayName: string;
  initials: string;
  roleLabel: string;
};

function deriveViewerProfile(user: AuthUser | null): ViewerProfile {
  const defaultProfile: ViewerProfile = {
    displayName: "User",
    initials: "US",
    roleLabel: "Student",
  };
  if (!user) return defaultProfile;

  const displayName =
    user.name?.trim() ||
    user.label.trim() ||
    user.email.split("@")[0]?.trim() ||
    user.username?.trim() ||
    defaultProfile.displayName;
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2);

  const normalizedGroups =
    user.groups?.map((group) => group.toLowerCase()) ?? [];
  const roleLabel = normalizedGroups.includes("admin")
    ? "Admin"
    : normalizedGroups.includes("staff") ||
        normalizedGroups.includes("instructor")
      ? "Instructor"
      : defaultProfile.roleLabel;

  return {
    displayName,
    initials: initials || defaultProfile.initials,
    roleLabel,
  };
}

export default function AppShell() {
  const { logout, user } = useAuth();
  const currentYear = new Date().getFullYear();
  const navigate = useNavigate();
  const location = useLocation();
  const showPilotRequestsLink = useMemo(
    () => canViewPilotRequests(user),
    [user],
  );
  const viewerProfile = useMemo(() => deriveViewerProfile(user), [user]);

  const isSessionRoute = /^\/sessions\/[^/]+/.test(location.pathname);
  const isPreLabRoute = /^\/labs\/[^/]+\/pre-lab$/.test(location.pathname);
  const isSessionReportRoute = /^\/sessions\/[^/]+\/report$/.test(
    location.pathname,
  );
  const hideLegacyHeader = isSessionRoute || isPreLabRoute;
  const isWideContentRoute = isSessionRoute || isPreLabRoute;
  const isPilotRequestsRoute =
    location.pathname === "/pilot-requests" ||
    location.pathname === "/admin/pilot-requests";
  const showCatalogShell =
    location.pathname === "/labs" ||
    location.pathname === "/reports" ||
    isPreLabRoute ||
    isSessionReportRoute;

  const activeCatalogLabel =
    location.pathname === "/labs" || isPreLabRoute
      ? "Catalog"
      : location.pathname === "/reports" || isSessionReportRoute
        ? "Reports"
        : null;

  if (showCatalogShell) {
    return (
      <div className="h-screen overflow-hidden bg-black font-sans text-slate-100 antialiased">
        <div className="relative flex h-full overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(132,204,22,0.12),transparent_30%),radial-gradient(circle_at_top_right,rgba(34,197,94,0.10),transparent_28%),linear-gradient(180deg,#020617_0%,#020617_40%,#000_100%)]" />

          <div className="pointer-events-none absolute top-0 right-8 hidden h-80 w-96 opacity-20 lg:block">
            <div className="h-full w-full bg-[linear-gradient(180deg,rgba(132,204,22,0.35)_1px,transparent_1px)] bg-[size:18px_18px]" />
          </div>

          <aside className="relative z-20 flex w-64 min-w-64 shrink-0 flex-col border-r border-lime-500/20 bg-black/80">
            <div className="flex h-20 items-center gap-3 border-b border-lime-500/20 px-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-lime-500/15 text-lime-300 ring-1 ring-lime-400/40 shadow-[0_0_22px_rgba(132,204,22,0.25)]">
                <Shield className="h-6 w-6" />
              </div>
              <span className="text-xl font-extrabold tracking-tight text-slate-100">
                Agent Failure
              </span>
            </div>

            <nav className="space-y-1 px-4 py-4">
              {catalogNavItems.map((item) => {
                const Icon = item.icon;
                const isActive = item.label === activeCatalogLabel;

                return (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => {
                      if (item.to) navigate(item.to);
                    }}
                    className={[
                      "relative flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition",
                      isActive
                        ? "border border-lime-400/40 bg-lime-500/10 text-lime-200 shadow-[0_0_18px_rgba(132,204,22,0.18)] before:absolute before:left-0 before:top-1/2 before:h-8 before:w-1 before:-translate-y-1/2 before:rounded-full before:bg-lime-400 before:shadow-[0_0_16px_rgba(132,204,22,0.9)]"
                        : "text-slate-300 hover:bg-lime-500/5 hover:text-lime-200",
                      item.to ? "" : "cursor-default opacity-70",
                    ].join(" ")}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </button>
                );
              })}
            </nav>
          </aside>

          <main className="relative flex min-w-0 flex-1 flex-col">
            <header className="sticky top-0 z-10 h-20 border-b border-lime-500/20 bg-black/55 px-5 backdrop-blur md:px-8 lg:px-10">
              <div className="flex h-full items-center justify-between">
                <div />

                <div className="ml-auto flex items-center gap-4">
                  <div className="pl-1">
                    <DropdownMenu.Root>
                      <DropdownMenu.Trigger asChild>
                        <button
                          type="button"
                          className="flex items-center gap-2 rounded-lg px-2 py-1 text-left transition hover:bg-lime-500/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lime-400"
                        >
                          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-xs font-extrabold text-slate-100 ring-1 ring-lime-500/20">
                            {viewerProfile.initials}
                          </div>
                          <span className="hidden text-sm font-semibold text-slate-300 sm:inline">
                            {viewerProfile.displayName}
                          </span>
                          <span className="hidden rounded-md border border-lime-500/30 bg-lime-500/10 px-2 py-0.5 text-xs font-bold uppercase tracking-wide text-lime-200 md:inline">
                            {viewerProfile.roleLabel}
                          </span>
                        </button>
                      </DropdownMenu.Trigger>
                      <DropdownMenu.Portal>
                        <DropdownMenu.Content
                          align="end"
                          sideOffset={8}
                          className="z-30 w-40 rounded-lg border border-lime-500/30 bg-black/95 p-1 shadow-[0_0_20px_rgba(132,204,22,0.18)] backdrop-blur"
                        >
                          {showPilotRequestsLink ? (
                            <DropdownMenu.Item
                              onSelect={() => {
                                navigate("/pilot-requests");
                              }}
                              className="flex cursor-pointer select-none items-center rounded-md px-3 py-2 text-sm font-semibold text-slate-200 outline-none transition data-[highlighted]:bg-lime-500/10 data-[highlighted]:text-lime-100"
                            >
                              Pilot Requests
                            </DropdownMenu.Item>
                          ) : null}
                          <DropdownMenu.Item
                            onSelect={() => {
                              void logout();
                            }}
                            className="flex cursor-pointer select-none items-center rounded-md px-3 py-2 text-sm font-semibold text-slate-200 outline-none transition data-[highlighted]:bg-lime-500/10 data-[highlighted]:text-lime-100"
                          >
                            Log Out
                          </DropdownMenu.Item>
                        </DropdownMenu.Content>
                      </DropdownMenu.Portal>
                    </DropdownMenu.Root>
                  </div>
                </div>
              </div>
            </header>

            <div className="flex-1 overflow-y-auto">
              <Outlet context={bootstrap} />
            </div>
            <footer className="border-t border-lime-500/20 bg-black/55 px-5 py-3 text-xs text-slate-400 backdrop-blur md:px-8 lg:px-10">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span>© {currentYear} Agent Failure</span>
                <nav
                  aria-label="Footer links"
                  className="flex flex-wrap items-center gap-3"
                >
                  <Link
                    to="/privacy"
                    className="transition hover:text-lime-200"
                  >
                    Privacy
                  </Link>
                  <Link to="/terms" className="transition hover:text-lime-200">
                    Terms
                  </Link>
                  <Link
                    to="/contact"
                    className="transition hover:text-lime-200"
                  >
                    Contact
                  </Link>
                </nav>
              </div>
            </footer>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-[radial-gradient(1200px_680px_at_8%_-2%,rgba(60,200,100,0.16),transparent_50%),radial-gradient(900px_540px_at_95%_-6%,rgba(46,125,50,0.2),transparent_52%),linear-gradient(180deg,#040704_0%,#071007_52%,#081108_100%)] font-sans text-[#d7ffd7] antialiased">
      {!hideLegacyHeader ? (
        <header className="sticky top-0 z-[3] border-b border-[#1b5e20] bg-[linear-gradient(180deg,rgba(10,18,10,0.95),rgba(6,12,6,0.9))] backdrop-blur-[6px]">
          <div
            className={[
              "flex items-center justify-between",
              isWideContentRoute
                ? "px-4 py-3.5"
                : "mx-auto max-w-[1240px] px-6 py-3.5",
            ].join(" ")}
          >
            <div>
              <div className="font-['Orbitron','Space_Grotesk','Avenir_Next_Condensed',sans-serif] text-[22px] font-bold tracking-[0.4px] text-[#8bff8f] uppercase">
                Agent Failure
              </div>
              <div className="text-xs tracking-[0.3px] text-[#7ea683]">
                Cyberrange Demo Surface
              </div>
            </div>
            {isWideContentRoute ? (
              <div />
            ) : (
              <div className="flex items-center gap-2.5">
                {isPreLabRoute || isPilotRequestsRoute ? (
                  <button
                    type="button"
                    onClick={() => navigate("/labs")}
                    className="cursor-pointer rounded-lg border border-[#2e7d32] bg-[#102810] px-2.5 py-[7px] text-xs font-bold text-[#b6ffb9]"
                  >
                    Back to Labs
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => void logout()}
                  className="cursor-pointer rounded-lg border border-[#7a2f3a] bg-[#3a1118] px-2.5 py-[7px] text-xs font-bold text-[#ffd7de]"
                >
                  Log Out
                </button>
              </div>
            )}
          </div>
        </header>
      ) : null}
      <main
        className={[
          "min-h-0 w-full flex-1",
          isWideContentRoute
            ? "flex flex-col"
            : "mx-auto max-w-[1240px] px-6 pt-7 pb-[34px]",
        ].join(" ")}
      >
        <Outlet context={bootstrap} />
      </main>
      <footer className="border-t border-lime-800/70 bg-[rgba(6,12,6,0.9)] px-6 py-2.5 text-xs text-lime-200/70">
        <div
          className={[
            "flex flex-wrap items-center justify-between gap-3",
            isWideContentRoute ? "" : "mx-auto max-w-[1240px]",
          ].join(" ")}
        >
          <span>© {currentYear} Agent Failure</span>
          <nav aria-label="Footer links" className="flex flex-wrap gap-3">
            <Link to="/privacy" className="transition hover:text-lime-200">
              Privacy
            </Link>
            <Link to="/terms" className="transition hover:text-lime-200">
              Terms
            </Link>
            <Link to="/contact" className="transition hover:text-lime-200">
              Contact
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
