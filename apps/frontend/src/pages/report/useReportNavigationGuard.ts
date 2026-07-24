import { useCallback, useEffect, useRef } from "react";
import { useBeforeUnload, useBlocker } from "react-router";

export function useReportNavigationGuard({
  flushSave,
  isDirty,
}: {
  flushSave: () => Promise<boolean>;
  isDirty: boolean;
}) {
  const isHandlingBlockedNavigationRef = useRef(false);

  useBeforeUnload(
    useCallback(
      (event) => {
        if (!isDirty) return;
        event.preventDefault();
        event.returnValue = "";
      },
      [isDirty],
    ),
  );

  const navigationBlocker = useBlocker(isDirty);
  useEffect(() => {
    if (
      navigationBlocker.state !== "blocked" ||
      isHandlingBlockedNavigationRef.current
    ) {
      return;
    }
    isHandlingBlockedNavigationRef.current = true;

    if (!window.confirm("Save your report changes and leave this page?")) {
      navigationBlocker.reset();
      isHandlingBlockedNavigationRef.current = false;
      return;
    }

    void flushSave().then((saved) => {
      if (saved) {
        navigationBlocker.proceed();
      } else {
        navigationBlocker.reset();
      }
      isHandlingBlockedNavigationRef.current = false;
    });
  }, [flushSave, navigationBlocker]);
}
