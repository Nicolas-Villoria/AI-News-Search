'use client';

import { useState, useEffect } from 'react';
import { useNewsFeed } from '@/lib/hooks';
import { formatTime, getSourceLabel } from '@/lib/utils';
import styles from './panels.module.css';

interface NewsFeedPanelProps {
    ticker: string | null;
}

export default function NewsFeedPanel({ ticker }: NewsFeedPanelProps) {
    const { data: news, mutate } = useNewsFeed(ticker);
    const [countdown, setCountdown] = useState(30);

    useEffect(() => {
        setCountdown(30);
        const interval = setInterval(() => {
            setCountdown((prev) => {
                if (prev <= 1) {
                    mutate();
                    return 30;
                }
                return prev - 1;
            });
        }, 1000);
        return () => clearInterval(interval);
    }, [ticker, mutate]);

    if (!ticker) {
        return (
            <div className={styles.panel}>
                <div className={styles.empty}>Select a ticker to view news</div>
            </div>
        );
    }

    return (
        <div className={styles.panel}>
            <div className={styles.panelHeader}>
                <span className={styles.panelTitle}>NEWS FEED — {ticker}</span>
                <span className={styles.refreshTimer}>↻ {countdown}s</span>
            </div>
            <div className={styles.newsList}>
                {(news || []).map((item, i) => (
                    <a
                        key={i}
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.newsItem}
                    >
                        <span className={styles.newsSource}>{getSourceLabel(item.source)}</span>
                        <span className={styles.newsTime}>{formatTime(item.published_at)}</span>
                        <span className={styles.newsHeadline}>{item.headline}</span>
                    </a>
                ))}
                {news && news.length === 0 && (
                    <div className={styles.empty}>No news available for {ticker}</div>
                )}
                {!news && (
                    <div className={styles.loading}>Loading news...</div>
                )}
            </div>
        </div>
    );
}
