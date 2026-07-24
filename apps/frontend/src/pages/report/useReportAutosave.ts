import { useCallback, useEffect, useRef, useState } from "react";
import { useSaveSessionReportDraftMutation } from "../../query/sessionReportDraft";
import type { PendingReportSave } from "./reportModel";

const AUTOSAVE_DEBOUNCE_MS = 1_500;

export function useReportAutosave({
  currentSave,
  hydratedSnapshot,
  sessionId,
}: {
  currentSave: PendingReportSave;
  hydratedSnapshot: string;
  sessionId: string;
}) {
  const saveMutation = useSaveSessionReportDraftMutation(sessionId);
  const [lastSavedSnapshot, setLastSavedSnapshot] = useState(hydratedSnapshot);
  const latestSaveRef = useRef<PendingReportSave>(currentSave);
  const lastSavedSnapshotRef = useRef(hydratedSnapshot);
  const failedSnapshotRef = useRef<string | null>(null);
  const saveInFlightRef = useRef<Promise<boolean> | null>(null);

  useEffect(() => {
    latestSaveRef.current = currentSave;
  }, [currentSave]);

  const {
    error: mutationError,
    isError: didSaveFail,
    isPending: isSaving,
    mutateAsync: saveReport,
    reset: resetSaveMutation,
  } = saveMutation;

  const performSave = useCallback(
    (pendingSave: PendingReportSave): Promise<boolean> => {
      if (saveInFlightRef.current) return saveInFlightRef.current;

      resetSaveMutation();
      const operation = saveReport(pendingSave.request)
        .then(() => {
          failedSnapshotRef.current = null;
          lastSavedSnapshotRef.current = pendingSave.snapshot;
          setLastSavedSnapshot(pendingSave.snapshot);
          return true;
        })
        .catch(() => {
          failedSnapshotRef.current = pendingSave.snapshot;
          return false;
        })
        .finally(() => {
          saveInFlightRef.current = null;
        });
      saveInFlightRef.current = operation;
      return operation;
    },
    [resetSaveMutation, saveReport],
  );

  const flushSave = useCallback(async (): Promise<boolean> => {
    while (true) {
      const inFlightSave = saveInFlightRef.current;
      if (inFlightSave) {
        if (!(await inFlightSave)) return false;
        continue;
      }

      const latestSave = latestSaveRef.current;
      if (latestSave.snapshot === lastSavedSnapshotRef.current) return true;
      if (!(await performSave(latestSave))) return false;
    }
  }, [performSave]);

  const isDirty = currentSave.snapshot !== lastSavedSnapshot;

  useEffect(() => {
    if (!isDirty || isSaving) return;
    if (failedSnapshotRef.current === currentSave.snapshot) return;
    const scheduledSnapshot = currentSave.snapshot;
    const timer = window.setTimeout(() => {
      if (latestSaveRef.current.snapshot !== scheduledSnapshot) return;
      void flushSave();
    }, AUTOSAVE_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [currentSave.snapshot, flushSave, isDirty, isSaving]);

  return {
    didSaveFail,
    flushSave,
    isDirty,
    isSaving,
    saveError: mutationError instanceof Error ? mutationError.message : null,
    saveStatus: isSaving
      ? "Saving..."
      : didSaveFail
        ? "Save failed"
        : isDirty
          ? "Unsaved changes"
          : "Saved",
  };
}
