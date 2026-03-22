import { useShellBootstrap } from "../shell/context";

export default function TracePage() {
  const bootstrap = useShellBootstrap();

  return (
    <section>
      <h1 style={{ margin: "0 0 12px" }}>Trace</h1>
      <p style={{ margin: 0 }}>
        Trace viewer scaffold in {bootstrap.mode} mode. Cursor/replay and event rendering are
        implemented by P1 trace tickets.
      </p>
    </section>
  );
}
