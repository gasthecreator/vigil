"use client";

import React, { forwardRef } from "react";
import { clsx } from "../utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", isLoading = false, disabled, children, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none rounded-md select-none";

    const sizeStyles = {
      sm: "h-9 px-3 text-xs min-w-[36px]",
      md: "h-11 px-4 text-sm min-w-[44px]", // 44px min touch target
      lg: "h-12 px-6 text-base min-w-[48px]",
    };

    const variantStyles = {
      primary: "bg-emerald-700 text-white hover:bg-emerald-800 focus:ring-emerald-600 shadow-sm",
      secondary: "bg-slate-100 text-slate-900 hover:bg-slate-200 focus:ring-slate-400 border border-slate-300",
      danger: "bg-red-700 text-white hover:bg-red-800 focus:ring-red-600 shadow-sm",
      outline: "border border-slate-300 bg-transparent text-slate-800 hover:bg-slate-50 focus:ring-emerald-600",
      ghost: "bg-transparent text-slate-700 hover:bg-slate-100 focus:ring-slate-400",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={clsx(baseStyles, sizeStyles[size], variantStyles[variant], className)}
        {...props}
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <svg
              className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            Processing...
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
