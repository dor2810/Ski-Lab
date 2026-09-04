"use client";

import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

/**
 * A modal that asks before something irreversible or paid happens.
 *
 * WHY MODAL AND NOT INLINE: the first version put this question in a
 * panel above the calendar, which pushed the whole grid down the
 * moment you clicked a day -- the page appeared to jump, and the
 * question read as another note among the legends rather than as
 * something waiting on an answer. A credit is the traveller's to
 * spend; asking for it has to interrupt, not annotate.
 *
 * Focus moves to the confirm button, Escape and the backdrop both
 * cancel, and the page behind is locked so the grid cannot scroll away
 * underneath the question.
 */
export function ConfirmDialog({
  title, children, confirmLabel, cancelLabel, onConfirm, onCancel,
}: {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    confirmRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") { onCancel(); return; }
      if (event.key !== "Tab" || !panelRef.current) return;
      // Keep focus inside: a dialog you can tab out of is a dialog the
      // keyboard can lose.
      const focusable = panelRef.current.querySelectorAll<HTMLElement>("button");
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onCancel]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      // The backdrop cancels, so a stray click never spends anything.
      onClick={onCancel}
    >
      <div aria-hidden="true" className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        onClick={(event) => event.stopPropagation()}
        className="relative w-full max-w-md rounded-2xl border border-line bg-surface p-5 shadow-2xl motion-safe:animate-rise-in sm:p-6"
      >
        <h2 id="confirm-dialog-title" className="text-lg font-bold text-ink">{title}</h2>
        <div className="mt-2 space-y-1.5 text-sm text-muted">{children}</div>
        <div className="mt-5 flex flex-wrap gap-2">
          <button
            ref={confirmRef}
            type="button"
            onClick={onConfirm}
            className="rounded-lg bg-signal px-4 py-2 text-sm font-semibold text-white hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-signal focus-visible:ring-offset-2"
          >
            {confirmLabel}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-line px-4 py-2 text-sm font-semibold text-muted hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
          >
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
