import { useCallback, useEffect, useRef, useState } from "react";
import type { TranscriptEntry } from "../types";

export function useTranscriptStreamView() {
  const [transcriptEntries, setTranscriptEntries] = useState<TranscriptEntry[]>(
    [],
  );
  const [activeEntry, setActiveEntry] = useState("");
  const [isAwaitingResponse, setIsAwaitingResponse] = useState(false);
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);
  const transcriptContentSnapshotRef = useRef({ entries: 0, activeLength: 0 });
  const [transcriptAutoScrollEnabled, setTranscriptAutoScrollEnabled] =
    useState(true);

  const transcriptViewportRef = useRef<HTMLDivElement | null>(null);
  const activeEntryTsRef = useRef<string | null>(null);
  const displayedEntryRef = useRef("");
  const pendingBufferRef = useRef("");
  const finalizePendingRef = useRef(false);
  const animationFrameRef = useRef<number | null>(null);
  const lastRevealAtMsRef = useRef(0);

  const resetActiveStream = useCallback(() => {
    displayedEntryRef.current = "";
    pendingBufferRef.current = "";
    finalizePendingRef.current = false;
    activeEntryTsRef.current = null;
    setActiveEntry("");
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  }, []);

  const drainRevealFrame = useCallback(() => {
    const revealIntervalMs = 60;
    const now = performance.now();
    if (now - lastRevealAtMsRef.current < revealIntervalMs) {
      animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
      return;
    }

    if (pendingBufferRef.current.length > 0) {
      const buffer = pendingBufferRef.current;
      const match = buffer.match(/^(\s*\S+\s*)/);
      const reveal = match ? match[1] : buffer;
      pendingBufferRef.current = buffer.slice(reveal.length);
      displayedEntryRef.current += reveal;
      lastRevealAtMsRef.current = now;
      setActiveEntry(displayedEntryRef.current);
      animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
      return;
    }

    if (finalizePendingRef.current) {
      const finalized = displayedEntryRef.current.trim();
      if (finalized) {
        setTranscriptEntries((entries) => {
          const last = entries.length > 0 ? entries[entries.length - 1] : null;
          if (
            last &&
            last.role === "agent" &&
            last.content === finalized &&
            last.timestamp ===
              (activeEntryTsRef.current ?? new Date().toISOString())
          ) {
            return entries;
          }
          return [
            ...entries,
            {
              role: "agent",
              content: finalized,
              timestamp: activeEntryTsRef.current ?? new Date().toISOString(),
            },
          ];
        });
      }

      resetActiveStream();
      setIsAwaitingResponse(false);
      return;
    }

    animationFrameRef.current = null;
  }, [resetActiveStream]);

  const ensureRevealLoop = useCallback(() => {
    if (animationFrameRef.current === null) {
      animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
    }
  }, [drainRevealFrame]);

  const scrollTranscriptToBottom = useCallback(() => {
    const viewport = transcriptViewportRef.current;
    if (!viewport) return;
    viewport.scrollTop = viewport.scrollHeight;
  }, []);

  const onTranscriptScroll = useCallback(() => {
    const viewport = transcriptViewportRef.current;
    if (!viewport) return;
    const remaining =
      viewport.scrollHeight - viewport.clientHeight - viewport.scrollTop;
    const nearBottom = remaining <= 48;

    setTranscriptAutoScrollEnabled(nearBottom);

    if (nearBottom) {
      setShowJumpToLatest(false);
    }
  }, []);

  const onJumpToLatest = useCallback(() => {
    scrollTranscriptToBottom();
    setTranscriptAutoScrollEnabled(true);
    setShowJumpToLatest(false);
  }, [scrollTranscriptToBottom]);

  // Keep transcript pinned to bottom when auto-scroll is enabled; otherwise show jump-to-latest affordance.
  useEffect(() => {
    const nextSnapshot = {
      entries: transcriptEntries.length,
      activeLength: activeEntry.length,
    };
    const previous = transcriptContentSnapshotRef.current;
    const hasNewTranscriptContent =
      nextSnapshot.entries > previous.entries ||
      nextSnapshot.activeLength > previous.activeLength;

    transcriptContentSnapshotRef.current = nextSnapshot;
    if (!hasNewTranscriptContent) return;

    if (transcriptAutoScrollEnabled) {
      scrollTranscriptToBottom();
      setShowJumpToLatest(false);
      return;
    }

    setShowJumpToLatest(true);
  }, [
    transcriptEntries,
    activeEntry,
    transcriptAutoScrollEnabled,
    scrollTranscriptToBottom,
  ]);

  // Ensure the transcript starts at latest content on initial mount.
  useEffect(() => {
    scrollTranscriptToBottom();
  }, [scrollTranscriptToBottom]);

  // Cleanup any pending animation frame on unmount to avoid leaks.
  useEffect(() => {
    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return {
    transcriptEntries,
    setTranscriptEntries,
    activeEntry,
    isAwaitingResponse,
    setIsAwaitingResponse,
    activeEntryTsRef,
    pendingBufferRef,
    finalizePendingRef,
    resetActiveStream,
    ensureRevealLoop,
    transcriptViewportRef,
    onTranscriptScroll,
    onJumpToLatest,
    showJumpToLatest,
  };
}
