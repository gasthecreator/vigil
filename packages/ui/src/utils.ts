/**
 * packages/ui/src/utils.ts
 *
 * Lightweight, zero-dependency classname merger.
 */

export function clsx(...inputs: (string | boolean | undefined | null | Record<string, boolean>)[]): string {
  const classes: string[] = [];

  for (const input of inputs) {
    if (!input) continue;
    if (typeof input === "string") {
      classes.push(input);
    } else if (typeof input === "object") {
      for (const [key, value] of Object.entries(input)) {
        if (value) classes.push(key);
      }
    }
  }

  return classes.join(" ");
}
