import { Crown, Leaf } from "lucide-react";

export function TierBadge({ tier = "basic", compact = false }) {
  const isPro = tier.toLowerCase() === "pro";
  const Icon = isPro ? Crown : Leaf;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-semibold uppercase tracking-normal ${
        compact ? "text-[10px]" : "text-xs"
      } ${
        isPro
          ? "border-sun/50 bg-yellow-50 text-yellow-800"
          : "border-green-100 bg-green-50 text-green-700"
      }`}
    >
      <Icon size={compact ? 11 : 13} strokeWidth={2.2} />
      {tier}
    </span>
  );
}
