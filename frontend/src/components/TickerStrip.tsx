'use client';

import { useBatchQuotes } from '@/lib/hooks';
import { formatPercent, getChangeClass } from '@/lib/utils';
import styles from './TickerStrip.module.css';

interface TickerStripProps {
    tickers: string[];
    selectedTicker: string | null;
    onSelectTicker: (ticker: string) => void;
}

export default function TickerStrip({ tickers, selectedTicker, onSelectTicker }: TickerStripProps) {
    const { data: quotes } = useBatchQuotes(tickers);

    return (
        <div className={styles.strip}>
            {(quotes || []).map((q) => (
                <button
                    key={q.ticker}
                    className={`${styles.ticker} ${q.ticker === selectedTicker ? styles.active : ''}`}
                    onClick={() => onSelectTicker(q.ticker)}
                >
                    <span className={styles.symbol}>{q.ticker}</span>
                    <span className={`${styles.change} ${getChangeClass(q.change_pct)}`}>
                        {formatPercent(q.change_pct)}
                    </span>
                </button>
            ))}
            {(!quotes || quotes.length === 0) && tickers.map((t) => (
                <button
                    key={t}
                    className={`${styles.ticker} ${t === selectedTicker ? styles.active : ''}`}
                    onClick={() => onSelectTicker(t)}
                >
                    <span className={styles.symbol}>{t}</span>
                    <span className={styles.change}>—</span>
                </button>
            ))}
        </div>
    );
}
