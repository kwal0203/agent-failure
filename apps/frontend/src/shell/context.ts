import { useOutletContext } from "react-router-dom";

export type ShellBootstrap = {
  mode: "demo";
  learnerLabel: string;
  apiBaseUrl: string;
};

export function useShellBootstrap() {
  return useOutletContext<ShellBootstrap>();
}
