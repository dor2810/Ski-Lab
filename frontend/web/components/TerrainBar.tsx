import type { TerrainMix } from "@/lib/api";

/**
 * Piste-grading colors are the ONE deliberate exception to the brand
 * palette (see brand spec section 2) -- a real-world standard skiers
 * already read instinctively. Colour is never the sole carrier of
 * meaning here: every segment also has a text label below the bar.
 */
export function TerrainBar({ terrain }: { terrain: TerrainMix | null }) {
  if (!terrain) {
    return <p className="text-xs text-ice/50">Terrain breakdown not available for this resort.</p>;
  }

  const beginner = Math.round(terrain.beginner * 100);
  const intermediate = Math.round(terrain.intermediate * 100);
  const advanced = Math.max(0, 100 - beginner - intermediate);

  return (
    <div>
      <div
        className="flex h-2.5 w-full overflow-hidden rounded-full"
        role="img"
        aria-label={`Terrain: ${beginner}% beginner, ${intermediate}% intermediate, ${advanced}% advanced`}
      >
        {/* Our data has 3 terrain tiers (beginner/intermediate/advanced),
            not the full 4-tier green/blue/red/black piste system -- so
            "blue/easy" is unused here; intermediate maps to red. */}
        <div style={{ width: `${beginner}%` }} className="bg-piste-beginner" />
        <div style={{ width: `${intermediate}%` }} className="bg-piste-intermediate" />
        <div style={{ width: `${advanced}%` }} className="bg-piste-advanced" />
      </div>
      <p className="mt-1.5 text-xs text-ice/60">
        {beginner}% beginner · {intermediate}% intermediate · {advanced}% advanced
        {terrain.quality === "estimated" && (
          <span className="text-ice/40"> (estimated)</span>
        )}
      </p>
    </div>
  );
}
