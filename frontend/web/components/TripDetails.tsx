"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { TripResult } from "@/lib/api";
import type { Dictionary } from "@/lib/i18n/languages";
import { useTranslation } from "@/lib/i18n/context";
import { FlightIcon, StayIcon, SnowIcon, ExternalLinkIcon } from "./icons";

/**
 * The card's EVIDENCE, behind one disclosure instead of five.
 *
 * WHY: the result card measured 2,662px tall at 1280px wide -- eight
 * peer blocks with no hierarchy, in which the cost breakdown (the
 * product's whole differentiator) was one eighth of the page. Two
 * consequences drove this rewrite: the thing we most want read was
 * buried, and comparing three trips side by side is impossible when
 * each is 2,600px tall.
 *
 * So the card splits: ANSWER above (where, when, how long, what it
 * costs), EVIDENCE here (which flights, which beds, what conditions).
 * Five peer disclosures collapse into three tabs, and each partner
 * hand-off link now sits inside the section it belongs to rather than
 * in a five-button cluster competing with the total.
 *
 * Tabs, not accordions: the three groups are alternatives, not a
 * checklist. Accordions invite opening everything, which is how the
 * card got long in the first place.
 */

export type TabKey = "getting" | "staying" | "conditions";

const TABS: { key: TabKey; label: keyof Dictionary; icon: typeof FlightIcon }[] = [
  { key: "getting", label: "tabGettingThere", icon: FlightIcon },
  { key: "staying", label: "tabStaying", icon: StayIcon },
  { key: "conditions", label: "tabConditions", icon: SnowIcon },
];

export function TripDetails({
  result, gettingThere, staying, conditions,
  open, onOpenChange, tab, onTabChange,
}: {
  result: TripResult;
  gettingThere: React.ReactNode;
  staying: React.ReactNode;
  conditions: React.ReactNode;
  // CONTROLLED: the cost breakdown above can open this straight to a
  // given tab, which is what makes the breakdown a table of contents
  // rather than a dead end.
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tab: TabKey;
  onTabChange: (tab: TabKey) => void;
}) {
  const { t } = useTranslation();
  const setOpen = (fn: (o: boolean) => boolean) => onOpenChange(fn(open));
  const setTab = onTabChange;
  const panelId = useId();

  const body = tab === "getting" ? gettingThere : tab === "staying" ? staying : conditions;

  return (
    <section className="mt-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full items-center justify-between gap-2 rounded-lg border border-line bg-surface px-3 py-2.5 text-sm font-semibold text-ink hover:text-signal"
      >
        <span>{t("tripDetailsTitle")}</span>
        <span aria-hidden="true" className="text-base leading-none text-subtle">
          {open ? "−" : "+"}
        </span>
      </button>

      {open && (
        <div id={panelId} className="mt-2 rounded-lg border border-line bg-surface">
          <div role="tablist" aria-label={t("tripDetailsTitle")} className="flex gap-1 border-b border-line p-1.5">
            {TABS.map(({ key, label, icon: Icon }) => {
              const selected = tab === key;
              return (
                <button
                  key={key}
                  role="tab"
                  type="button"
                  aria-selected={selected}
                  onClick={() => setTab(key)}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-signal ${
                    selected ? "bg-signal text-white" : "text-muted hover:bg-sunken"
                  }`}
                >
                  <Icon size={13} className="flex-none" />
                  <span className="truncate">{t(label)}</span>
                </button>
              );
            })}
          </div>
          <div role="tabpanel" className="p-3">
            {body}
            {/* The explanation is evidence, not headline: it justifies
                the ranking, which is something you read after you have
                decided the trip is interesting. */}
            {tab === "conditions" && (
              <p className="mt-3 text-sm leading-relaxed text-muted">{result.explanation}</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

/** A partner hand-off, now living inside the section it belongs to. */
export function HandoffLink({ href, label, flash = false }: {
  href: string | null;
  label: string;
  /**
   * Briefly call this link out because the traveller arrived here by
   * clicking the matching cost line. Opening the right tab answers
   * "where do I look"; it does not answer "what do I press", and for
   * kit hire and the lift pass the link IS the next step.
   */
  flash?: boolean;
}) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold text-sky transition-colors duration-500 hover:border-sky/60 hover:bg-sky/10 ${
        flash
          // Colour is not the only carrier -- the ring changes the
          // shape of the control too, so this reads without relying on
          // hue perception. Motion is opt-out; the ring is not.
          ? "border-signal bg-signal-soft ring-2 ring-signal motion-safe:animate-pulse"
          : "border-line"
      }`}
    >
      <ExternalLinkIcon size={12} />
      {label}
    </a>
  );
}
