'use client';

import { useEffect, useRef, useState } from 'react';
import { useCompanyProfile, useQuote, useChart } from '@/lib/hooks';
import { formatCurrency, formatPercent, formatNumber, getChangeClass } from '@/lib/utils';
import styles from './panels.module.css';

interface OverviewPanelProps {
    ticker: string | null;
}

export default function OverviewPanel({ ticker }: OverviewPanelProps) {
    const { data: profile } = useCompanyProfile(ticker);
    const { data: quote } = useQuote(ticker);
    const [chartPeriod, setChartPeriod] = useState('1M');
    const { data: chartData } = useChart(ticker, chartPeriod);
    const chartRef = useRef<HTMLDivElement>(null);
    const chartInstanceRef = useRef<any>(null);

    // Chart rendering
    useEffect(() => {
        if (!chartRef.current || !chartData || chartData.length === 0) return;

        let cancelled = false;

        async function renderChart() {
            const { createChart, LineSeries } = await import('lightweight-charts');

            if (cancelled || !chartRef.current || !chartData) return;

            // Clear previous chart
            if (chartInstanceRef.current) {
                chartInstanceRef.current.remove();
            }

            const chart = createChart(chartRef.current, {
                width: chartRef.current.clientWidth,
                height: 300,
                layout: {
                    background: { color: '#0d1117' },
                    textColor: '#8b949e',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                },
                grid: {
                    vertLines: { color: '#21262d' },
                    horzLines: { color: '#21262d' },
                },
                crosshair: {
                    vertLine: { color: '#FF6E00', width: 1, style: 2 },
                    horzLine: { color: '#FF6E00', width: 1, style: 2 },
                },
                timeScale: {
                    borderColor: '#30363d',
                    timeVisible: chartPeriod === '1D',
                },
                rightPriceScale: {
                    borderColor: '#30363d',
                },
            });

            chartInstanceRef.current = chart;

            const isPositive = chartData.length > 1 &&
                chartData[chartData.length - 1].close >= chartData[0].close;

            const lineSeries = chart.addSeries(LineSeries, {
                color: isPositive ? '#3FB950' : '#F85149',
                lineWidth: 2,
                crosshairMarkerVisible: true,
                crosshairMarkerRadius: 4,
                crosshairMarkerBackgroundColor: '#FF6E00',
                priceLineVisible: true,
                priceLineColor: '#30363d',
            });

            lineSeries.setData(
                chartData.map((bar) => ({
                    time: bar.date,
                    value: bar.close,
                }))
            );

            chart.timeScale().fitContent();

            // Resize observer
            const resizeObserver = new ResizeObserver(() => {
                if (chartRef.current) {
                    chart.applyOptions({ width: chartRef.current.clientWidth });
                }
            });
            resizeObserver.observe(chartRef.current);

            return () => {
                resizeObserver.disconnect();
                chart.remove();
            };
        }

        renderChart();
        return () => { cancelled = true; };
    }, [chartData, chartPeriod]);

    if (!ticker) {
        return (
            <div className={styles.panel}>
                <div className={styles.empty}>Select a ticker to view overview</div>
            </div>
        );
    }

    const company = profile?.company;
    const periods = ['1D', '1W', '1M', '3M', '1Y', '5Y'];

    return (
        <div className={styles.panel}>
            <div className={styles.panelHeader}>
                <span className={styles.panelTitle}>OVERVIEW — {ticker}</span>
            </div>

            {/* Chart */}
            <div className={styles.chartSection}>
                <div className={styles.chartPeriods}>
                    {periods.map((p) => (
                        <button
                            key={p}
                            className={`${styles.periodBtn} ${chartPeriod === p ? styles.periodActive : ''}`}
                            onClick={() => setChartPeriod(p)}
                        >
                            {p}
                        </button>
                    ))}
                </div>
                <div ref={chartRef} className={styles.chartContainer} />
            </div>

            {/* Key Stats */}
            {quote && (
                <div className={styles.statsGrid}>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>OPEN</span>
                        <span className={styles.statValue}>{formatCurrency(quote.open)}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>PREV CLOSE</span>
                        <span className={styles.statValue}>{formatCurrency(quote.prev_close)}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>DAY HIGH</span>
                        <span className={styles.statValue}>{formatCurrency(quote.day_high)}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>DAY LOW</span>
                        <span className={styles.statValue}>{formatCurrency(quote.day_low)}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>52W HIGH</span>
                        <span className={styles.statValue}>{formatCurrency(quote.year_high)}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>52W LOW</span>
                        <span className={styles.statValue}>{formatCurrency(quote.year_low)}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>VOLUME</span>
                        <span className={styles.statValue}>{formatNumber(quote.volume)}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>MKT CAP</span>
                        <span className={styles.statValue}>{formatCurrency(quote.market_cap, true)}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>P/E</span>
                        <span className={styles.statValue}>{quote.pe ? quote.pe.toFixed(2) : '—'}</span>
                    </div>
                    <div className={styles.statItem}>
                        <span className={styles.statLabel}>EPS</span>
                        <span className={styles.statValue}>{quote.eps ? `$${quote.eps.toFixed(2)}` : '—'}</span>
                    </div>
                </div>
            )}

            {/* Company Info */}
            {company && (
                <div className={styles.companyInfo}>
                    <div className={styles.companyHeader}>
                        <span className={styles.companyName}>{company.name}</span>
                        <span className={styles.companySector}>{company.sector} · {company.industry}</span>
                    </div>
                    {company.description && (
                        <p className={styles.companyDesc}>{company.description.slice(0, 400)}...</p>
                    )}
                </div>
            )}
        </div>
    );
}
