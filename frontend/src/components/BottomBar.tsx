'use client';

import { useIndices } from '@/lib/hooks';
import { formatCurrency, formatPercent, getChangeClass } from '@/lib/utils';
import styles from './BottomBar.module.css';

export default function BottomBar() {
    const { data: indices } = useIndices();

    const items = indices || [];

    return (
        <footer className={styles.bottombar}>
            <div className={styles.marquee}>
                <div className={styles.track}>
                    {items.map((idx, i) => (
                        <span key={`a-${i}`} className={styles.item}>
                            <span className={styles.symbol}>{idx.symbol}</span>
                            <span className={styles.indexPrice}>
                                {idx.price > 100 ? idx.price.toLocaleString('en-US', { maximumFractionDigits: 1 }) : idx.price.toFixed(2)}
                            </span>
                            <span className={`${styles.indexChange} ${getChangeClass(idx.change_pct)}`}>
                                {formatPercent(idx.change_pct)}
                            </span>
                        </span>
                    ))}
                    {/* Duplicate for seamless loop */}
                    {items.map((idx, i) => (
                        <span key={`b-${i}`} className={styles.item}>
                            <span className={styles.symbol}>{idx.symbol}</span>
                            <span className={styles.indexPrice}>
                                {idx.price > 100 ? idx.price.toLocaleString('en-US', { maximumFractionDigits: 1 }) : idx.price.toFixed(2)}
                            </span>
                            <span className={`${styles.indexChange} ${getChangeClass(idx.change_pct)}`}>
                                {formatPercent(idx.change_pct)}
                            </span>
                        </span>
                    ))}
                </div>
            </div>
        </footer>
    );
}
