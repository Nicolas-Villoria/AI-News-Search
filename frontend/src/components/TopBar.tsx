'use client';

import { useState, useEffect } from 'react';
import { useQuote } from '@/lib/hooks';
import { formatCurrency, formatChange, formatPercent, getChangeClass, isMarketOpen, getCurrentTime } from '@/lib/utils';
import styles from './TopBar.module.css';

interface TopBarProps {
    selectedTicker: string | null;
}

export default function TopBar({ selectedTicker }: TopBarProps) {
    const { data: quote } = useQuote(selectedTicker);
    const [clock, setClock] = useState('');
    const [marketOpen, setMarketOpen] = useState(false);

    useEffect(() => {
        const update = () => {
            setClock(getCurrentTime());
            setMarketOpen(isMarketOpen());
        };
        update();
        const interval = setInterval(update, 1000);
        return () => clearInterval(interval);
    }, []);

    return (
        <header className={styles.topbar}>
            <div className={styles.left}>
                <span className={styles.brand}>FINHAUS.</span>
                <span className={styles.version}>FINANCIAL TERMINAL v1.0</span>
            </div>

            <div className={styles.center}>
                {selectedTicker && quote && (
                    <>
                        <span className={styles.tickerLabel}>{quote.ticker}</span>
                        <span className={styles.companyName}>{quote.name}</span>
                        <span className={styles.price}>{formatCurrency(quote.price)}</span>
                        <span className={`${styles.change} ${getChangeClass(quote.change)}`}>
                            {formatChange(quote.change)} ({formatPercent(quote.change_pct)})
                        </span>
                    </>
                )}
            </div>

            <div className={styles.right}>
                <span className={`${styles.marketStatus} ${marketOpen ? styles.open : styles.closed}`}>
                    {marketOpen ? '● MKT OPEN' : '● MKT CLOSED'}
                </span>
                <span className={styles.clock}>{clock} EST</span>
            </div>
        </header>
    );
}
