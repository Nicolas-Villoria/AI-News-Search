/**
 * Finhaus — Shared utility functions
 */

/**
 * Format a number as currency (USD).
 */
export function formatCurrency(value: number, compact: boolean = false): string {
    if (compact && Math.abs(value) >= 1e12) {
        return `$${(value / 1e12).toFixed(2)}T`;
    }
    if (compact && Math.abs(value) >= 1e9) {
        return `$${(value / 1e9).toFixed(2)}B`;
    }
    if (compact && Math.abs(value) >= 1e6) {
        return `$${(value / 1e6).toFixed(2)}M`;
    }
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(value);
}

/**
 * Format a percentage value.
 */
export function formatPercent(value: number): string {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

/**
 * Format a change value with sign.
 */
export function formatChange(value: number): string {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}`;
}

/**
 * Format large numbers with commas.
 */
export function formatNumber(value: number): string {
    return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Format a timestamp or date string into a time string (HH:MM).
 */
export function formatTime(input: string | number): string {
    let date: Date;
    if (typeof input === 'number') {
        date = new Date(input * 1000);
    } else {
        date = new Date(input);
    }
    if (isNaN(date.getTime())) return '';
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
    });
}

/**
 * Format a date string into a short label (Mar 8).
 */
export function formatDate(input: string): string {
    const date = new Date(input);
    if (isNaN(date.getTime())) return input;
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
    });
}

/**
 * Get the CSS class for a positive/negative value.
 */
export function getChangeClass(value: number): string {
    if (value > 0) return 'text-positive';
    if (value < 0) return 'text-negative';
    return 'text-muted';
}

/**
 * Map news source names to short labels.
 */
export function getSourceLabel(source: string): string {
    const map: Record<string, string> = {
        'reuters': 'RTRS',
        'bloomberg': 'BBRG',
        'cnbc': 'CNBC',
        'wall street journal': 'WSJ',
        'wsj': 'WSJ',
        'financial times': 'FT',
        'ft': 'FT',
        'associated press': 'AP',
        'barrons': 'BRNS',
        'marketwatch': 'MW',
        'seeking alpha': 'SA',
        'yahoo finance': 'YHOO',
        'benzinga': 'BNZG',
        'investopedia': 'INVP',
    };
    const lower = source.toLowerCase();
    for (const [key, value] of Object.entries(map)) {
        if (lower.includes(key)) return value;
    }
    // Return first 4 chars uppercased as fallback
    return source.slice(0, 4).toUpperCase();
}

/**
 * Determine if US market is currently open.
 */
export function isMarketOpen(): boolean {
    const now = new Date();
    const est = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const day = est.getDay();
    const hours = est.getHours();
    const minutes = est.getMinutes();
    const timeMinutes = hours * 60 + minutes;

    // Weekdays 9:30 AM - 4:00 PM ET
    if (day >= 1 && day <= 5 && timeMinutes >= 570 && timeMinutes < 960) {
        return true;
    }
    return false;
}

/**
 * Get current time formatted as EST clock.
 */
export function getCurrentTime(): string {
    return new Date().toLocaleTimeString('en-US', {
        timeZone: 'America/New_York',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
    });
}
