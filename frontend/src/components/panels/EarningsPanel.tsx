'use client';

import { useEarningsCalendar } from '@/lib/hooks';
import { formatDate, formatCurrency, getChangeClass } from '@/lib/utils';
import styles from './panels.module.css';

export default function EarningsPanel() {
    const { data: earnings } = useEarningsCalendar(30);

    return (
        <div className={styles.panel}>
            <div className={styles.panelHeader}>
                <span className={styles.panelTitle}>EARNINGS CALENDAR</span>
                <span className={styles.headerSub}>Next 30 days</span>
            </div>

            <div className={styles.tableWrapper}>
                <table className={styles.table}>
                    <thead>
                        <tr>
                            <th>DATE</th>
                            <th>TICKER</th>
                            <th>TIME</th>
                            <th>EPS EST</th>
                            <th>REV EST</th>
                            <th>EPS ACT</th>
                            <th>REV ACT</th>
                            <th>SURPRISE</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(earnings || []).map((e, i) => {
                            const epsSurprise = e.eps_actual && e.eps_estimate
                                ? e.eps_actual - e.eps_estimate
                                : null;
                            return (
                                <tr key={i}>
                                    <td>{formatDate(e.report_date)}</td>
                                    <td className={styles.tickerCol}>{e.ticker}</td>
                                    <td className={styles.timeCol}>
                                        {e.time === 'bmo' ? '🌅 BMO' : e.time === 'amc' ? '🌙 AMC' : e.time || '—'}
                                    </td>
                                    <td>{e.eps_estimate != null ? `$${e.eps_estimate.toFixed(2)}` : '—'}</td>
                                    <td>{e.revenue_estimate != null ? formatCurrency(e.revenue_estimate, true) : '—'}</td>
                                    <td>{e.eps_actual != null ? `$${e.eps_actual.toFixed(2)}` : '—'}</td>
                                    <td>{e.revenue_actual != null ? formatCurrency(e.revenue_actual, true) : '—'}</td>
                                    <td className={epsSurprise != null ? getChangeClass(epsSurprise) : ''}>
                                        {epsSurprise != null ? `${epsSurprise >= 0 ? '+' : ''}$${epsSurprise.toFixed(2)}` : '—'}
                                    </td>
                                </tr>
                            );
                        })}
                        {earnings && earnings.length === 0 && (
                            <tr>
                                <td colSpan={8} className={styles.empty}>No upcoming earnings found</td>
                            </tr>
                        )}
                        {!earnings && (
                            <tr>
                                <td colSpan={8} className={styles.loading}>Loading earnings calendar...</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
