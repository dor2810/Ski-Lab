"use client";

import type { KeyboardEvent, MouseEvent, ReactNode } from "react";
import { CheckIcon } from "./icons";

/**
 * The clickable option row shared by FlightOptions, TransferOptions and
 * AccommodationOptions.
 *
 * WHY IT EXISTS: each list used to carry its own "Use this flight" /
 * "Use this leg" button. A button that only repeats what the row it
 * sits in already offers is a target to aim at, not information -- so
 * the whole row is the target now, and the only thing left in that
 * corner is the state ("Shown in your trip"), which IS information.
 *
 * The three lists had begun to drift (different rings, different
 * selected tints, only two of them selectable at all), so the
 * behaviour lives here once.
 *
 * ACCESSIBILITY: a list of mutually exclusive choices is a radiogroup,
 * so that is what it reports as -- roving tabindex, arrows to move,
 * Enter/Space to choose. The rows contain their own links ("Book",
 * the property name), and those must keep working as links: a click
 * that lands on any nested control is left alone rather than being
 * swallowed as a selection.
 */

const NESTED_CONTROL = "a, button, input, select, textarea, [role='button']";

export function OptionRadioGroup({
  label, children, className = "mt-2.5 space-y-1.5",
}: {
  /** Names the group for screen readers -- "Flight options", etc. */
  label: string;
  children: ReactNode;
  className?: string;
}) {
  function onKeyDown(event: KeyboardEvent<HTMLUListElement>) {
    const keys = ["ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft"];
    if (!keys.includes(event.key)) return;
    const rows = Array.from(
      event.currentTarget.querySelectorAll<HTMLElement>("[role='radio']")
    );
    const current = rows.findIndex((r) => r.contains(document.activeElement));
    if (current === -1) return;
    event.preventDefault();
    const forward = event.key === "ArrowDown" || event.key === "ArrowRight";
    const next = rows[(current + (forward ? 1 : -1) + rows.length) % rows.length];
    // Moving focus in a radiogroup moves the choice with it, which is
    // what the pattern (and every native radio list) does.
    next.focus();
    next.click();
  }

  return (
    <ul role="radiogroup" aria-label={label} className={className} onKeyDown={onKeyDown}>
      {children}
    </ul>
  );
}

export function SelectableOptionRow({
  selected, onSelect, selectedLabel, badges, tint, children,
}: {
  selected: boolean;
  /** Absent when the list is read-only -- the row then renders plain. */
  onSelect?: () => void;
  /** What to call the current choice, e.g. "Shown in your trip". */
  selectedLabel: string;
  /** Role chips ("Cheapest", "Best"), shown left of the state. */
  badges?: ReactNode;
  /** Optional resting tint for a row worth noticing when unselected. */
  tint?: string;
  children: ReactNode;
}) {
  function onClick(event: MouseEvent<HTMLLIElement>) {
    if (!onSelect) return;
    // A click on the row's own "Book" link is a click on that link.
    if ((event.target as HTMLElement).closest(NESTED_CONTROL)) return;
    onSelect();
  }

  function onKeyDown(event: KeyboardEvent<HTMLLIElement>) {
    if (!onSelect) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    if ((event.target as HTMLElement).closest(NESTED_CONTROL)) return;
    event.preventDefault();
    onSelect();
  }

  const hasHeader = Boolean(badges) || (Boolean(onSelect) && selected);

  return (
    <li
      role={onSelect ? "radio" : undefined}
      aria-checked={onSelect ? selected : undefined}
      tabIndex={onSelect ? (selected ? 0 : -1) : undefined}
      onClick={onClick}
      onKeyDown={onKeyDown}
      className={`rounded-lg px-2 py-1.5 ${
        onSelect ? "cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-signal" : ""
      } ${
        selected && onSelect
          ? "bg-signal-soft ring-2 ring-signal"
          : `${tint ?? ""} ${onSelect ? "hover:bg-sunken" : ""}`
      }`}
    >
      {hasHeader && (
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="flex flex-wrap items-center gap-1">{badges}</span>
          {onSelect && selected && (
            <span className="flex flex-none items-center gap-1 text-[10px] font-semibold text-signal">
              <CheckIcon size={11} aria-hidden="true" />
              {selectedLabel}
            </span>
          )}
        </div>
      )}
      {children}
    </li>
  );
}
