export function money(value: number | string, decimals = 2): string {
  return Number(value).toLocaleString('en-AU', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function shortTime(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit', hour12: false });
}
