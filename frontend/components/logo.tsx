import { cn } from "@/lib/utils";

export function Logo({ size = "md", className }: { size?: "md" | "lg"; className?: string }) {
  const box = size === "lg" ? "size-8 rounded-[8px]" : "size-7 rounded-[7px]";
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <span className={cn("flex items-center justify-center bg-primary", box)}>
        <svg
          aria-hidden="true"
          width={size === "lg" ? 18 : 16}
          height={size === "lg" ? 18 : 16}
          viewBox="0 0 24 24"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 19V9" />
          <path d="M10 19V5" />
          <path d="M16 19v-7" />
          <path d="M22 19H2" />
        </svg>
      </span>
      <span className={cn("font-semibold tracking-tight", size === "lg" ? "text-base" : "text-[15px]")}>
        ACME Salary
      </span>
    </span>
  );
}
