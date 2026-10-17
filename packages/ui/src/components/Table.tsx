"use client";

import React from "react";
import { clsx } from "../utils";

export const Table: React.FC<React.TableHTMLAttributes<HTMLTableElement>> = ({ className, ...props }) => (
  <div className="relative w-full overflow-auto">
    <table className={clsx("w-full caption-bottom text-sm", className)} {...props} />
  </div>
);

export const TableHeader: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({ className, ...props }) => (
  <thead className={clsx("[&_tr]:border-b bg-slate-50 border-slate-200", className)} {...props} />
);

export const TableBody: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({ className, ...props }) => (
  <tbody className={clsx("[&_tr:last-child]:border-0 divide-y divide-slate-100", className)} {...props} />
);

export const TableRow: React.FC<React.HTMLAttributes<HTMLTableRowElement>> = ({ className, ...props }) => (
  <tr
    className={clsx(
      "border-b transition-colors hover:bg-slate-50/80 data-[state=selected]:bg-slate-100",
      className
    )}
    {...props}
  />
);

export const TableHead: React.FC<React.ThHTMLAttributes<HTMLTableCellElement>> = ({ className, ...props }) => (
  <th
    scope="col"
    className={clsx(
      "h-11 px-4 text-left align-middle font-semibold text-slate-700 [&:has([role=checkbox])]:pr-0",
      className
    )}
    {...props}
  />
);

export const TableCell: React.FC<React.TdHTMLAttributes<HTMLTableCellElement>> = ({ className, ...props }) => (
  <td className={clsx("p-4 align-middle [&:has([role=checkbox])]:pr-0 text-slate-800", className)} {...props} />
);
