"use client";

import React from "react";
import { clsx } from "../utils";
import { colors } from "../tokens";

export type BadgeVariant =
  | "escalate"
  | "needs_repeat"
  | "explained"
  | "urgent"
  | "review"
  | "watch"
  | "synthetic"
  | "default"
  | "success"
  | "warning"
  | "danger";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = "default",
  size = "md",
  children,
  ...props
}) => {
  const baseStyles = "inline-flex items-center font-medium rounded-full border px-2.5 py-0.5 text-xs transition-colors";

  const sizeStyles = {
    sm: "px-2 py-0.2 text-[10px]",
    md: "px-2.5 py-0.5 text-xs font-semibold",
  };

  const variantStyles: Record<BadgeVariant, string> = {
    escalate: colors.plausibility.escalate.badge,
    needs_repeat: colors.plausibility.needs_repeat.badge,
    explained: colors.plausibility.explained.badge,
    urgent: colors.alertTiers.urgent.badge,
    review: colors.alertTiers.review.badge,
    watch: colors.alertTiers.watch.badge,
    synthetic: "bg-yellow-200 text-yellow-950 border border-yellow-500 font-bold tracking-wider",
    default: "bg-slate-100 text-slate-800 border-slate-300",
    success: "bg-emerald-100 text-emerald-800 border-emerald-300",
    warning: "bg-amber-100 text-amber-800 border-amber-300",
    danger: "bg-red-100 text-red-900 border border-red-400 font-bold",
  };

  return (
    <span className={clsx(baseStyles, sizeStyles[size], variantStyles[variant], className)} {...props}>
      {children}
    </span>
  );
};
