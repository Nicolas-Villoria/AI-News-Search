'use client';

import styles from './panels.module.css';

interface WatchlistPanelProps {
    tickers: string[];
    onAddTicker: (ticker: string) => void;
    onRemoveTicker: (ticker: string) => void;
}

export default function WatchlistPanel({ tickers, onAddTicker, onRemoveTicker }: WatchlistPanelProps) {
    return (
        <div className={styles.panel}>
            <div className={styles.panelHeader}>
                <span className={styles.panelTitle}>WATCHLIST</span>
                <span className={styles.headerSub}>{tickers.length} tickers</span>
            </div>

            <div className={styles.watchlistControls}>
                <form
                    className={styles.addForm}
                    onSubmit={(e) => {
                        e.preventDefault();
                        const input = (e.target as HTMLFormElement).elements.namedItem('ticker') as HTMLInputElement;
                        if (input.value.trim()) {
                            onAddTicker(input.value.trim().toUpperCase());
                            input.value = '';
                        }
                    }}
                >
                    <input
                        name="ticker"
                        className={styles.addInput}
                        placeholder="ADD TICKER..."
                        autoComplete="off"
                    />
                    <button type="submit" className={styles.addBtn}>+ ADD</button>
                </form>
            </div>

            <div className={styles.watchlistGrid}>
                {tickers.map((t) => (
                    <div key={t} className={styles.watchlistItem}>
                        <span className={styles.watchlistTicker}>{t}</span>
                        <button
                            className={styles.removeBtn}
                            onClick={() => onRemoveTicker(t)}
                            title={`Remove ${t}`}
                        >
                            ×
                        </button>
                    </div>
                ))}
                {tickers.length === 0 && (
                    <div className={styles.empty}>No tickers in watchlist. Add one above.</div>
                )}
            </div>
        </div>
    );
}
