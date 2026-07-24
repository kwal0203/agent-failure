import { useOutletContext } from "react-router";

export type ShellBootstrap = {
  mode: "demo" | "debug";
  learnerLabel: string;
  apiBaseUrl: string;
};

export function useShellBootstrap() {
  return useOutletContext<ShellBootstrap>();
}
