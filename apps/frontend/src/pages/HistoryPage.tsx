import { useShellBootstrap } from "../shell/context";

export default function HistoryPage() {
  const bootstrap = useShellBootstrap();

  return (
    <section>
      <h1 style={{ margin: "0 0 12px" }}>History</h1>
      <p style={{ margin: 0 }}>
        History view placeholder for {bootstrap.mode} mode. Session timeline tickets fill this
        surface in follow-up P1 work.
      </p>
    </section>
  );
}
