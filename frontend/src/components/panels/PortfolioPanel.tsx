'use client';

import { useState, useEffect } from 'react';
import { portfolioAPI } from '@/lib/api';
import type { AlpacaStatus, AlpacaAccount, AlpacaPosition } from '@/lib/api';
import { formatCurrency, formatPercent, getChangeClass } from '@/lib/utils';
import styles from './panels.module.css';

export default function PortfolioPanel() {
    const [status, setStatus] = useState<AlpacaStatus | null>(null);
    const [account, setAccount] = useState<AlpacaAccount | null>(null);
    const [positions, setPositions] = useState<AlpacaPosition[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadData() {
            try {
                const s = await portfolioAPI.getAlpacaStatus();
                setStatus(s);
                if (s.connected) {
                    const [acc, pos] = await Promise.all([
                        portfolioAPI.getAlpacaAccount(),
                        portfolioAPI.getAlpacaPositions(),
                    ]);
                    setAccount(acc);
                    setPositions(pos);
                }
            } catch {
                setStatus({ connected: false, message: 'Failed to connect to backend' });
            }
            setLoading(false);
        }
        loadData();
        const interval = setInterval(loadData, 30000);
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className={styles.panel}>
                <div className={styles.loading}>Loading portfolio...</div>
            </div>
        );
    }

    if (!status?.connected) {
        return (
            <div className={styles.panel}>
                <div className={styles.panelHeader}>
                    <span className={styles.panelTitle}>PORTFOLIO</span>
                </div>
                <div className={styles.disconnected}>
                    <div className={styles.disconnectedIcon}>⚠</div>
                    <div className={styles.disconnectedTitle}>Alpaca Not Connected</div>
                    <div className={styles.disconnectedMsg}>
                        {status?.message || 'Configure ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env file to connect your brokerage account.'}
                    </div>
                </div>
            </div>
        );
    }

    const totalPnL = positions.reduce((sum, p) => sum + p.unrealized_pl, 0);
    const totalValue = positions.reduce((sum, p) => sum + p.market_value, 0);

    return (
        <div className={styles.panel}>
            <div className={styles.panelHeader}>
                <span className={styles.panelTitle}>PORTFOLIO — ALPACA</span>
                <span className={styles.headerSub}>{positions.length} positions</span>
            </div>

            {/* Account Summary */}
            {account && (
                <div className={styles.accountSummary}>
                    <div className={styles.accountCard}>
                        <span className={styles.accountLabel}>EQUITY</span>
                        <span className={styles.accountValue}>{formatCurrency(account.equity)}</span>
                    </div>
                    <div className={styles.accountCard}>
                        <span className={styles.accountLabel}>BUYING POWER</span>
                        <span className={styles.accountValue}>{formatCurrency(account.buying_power)}</span>
                    </div>
                    <div className={styles.accountCard}>
                        <span className={styles.accountLabel}>CASH</span>
                        <span className={styles.accountValue}>{formatCurrency(account.cash)}</span>
                    </div>
                    <div className={styles.accountCard}>
                        <span className={styles.accountLabel}>UNREALIZED P&L</span>
                        <span className={`${styles.accountValue} ${getChangeClass(totalPnL)}`}>
                            {formatCurrency(totalPnL)}
                        </span>
                    </div>
                </div>
            )}

            {/* Positions Table */}
            <div className={styles.tableWrapper}>
                <table className={styles.table}>
                    <thead>
                        <tr>
                            <th>TICKER</th>
                            <th>QTY</th>
                            <th>AVG COST</th>
                            <th>PRICE</th>
                            <th>MKT VALUE</th>
                            <th>P&L</th>
                            <th>P&L %</th>
                            <th>TODAY</th>
                        </tr>
                    </thead>
                    <tbody>
                        {positions.map((p) => (
                            <tr key={p.ticker}>
                                <td className={styles.tickerCol}>{p.ticker}</td>
                                <td>{p.qty}</td>
                                <td>{formatCurrency(p.avg_entry_price)}</td>
                                <td>{formatCurrency(p.current_price)}</td>
                                <td>{formatCurrency(p.market_value)}</td>
                                <td className={getChangeClass(p.unrealized_pl)}>
                                    {formatCurrency(p.unrealized_pl)}
                                </td>
                                <td className={getChangeClass(p.unrealized_plpc)}>
                                    {formatPercent(p.unrealized_plpc * 100)}
                                </td>
                                <td className={getChangeClass(p.change_today)}>
                                    {formatPercent(p.change_today * 100)}
                                </td>
                            </tr>
                        ))}
                        {positions.length === 0 && (
                            <tr>
                                <td colSpan={8} className={styles.empty}>No open positions</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
