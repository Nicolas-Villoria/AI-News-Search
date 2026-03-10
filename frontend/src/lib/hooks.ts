/**
 * Finhaus — SWR Data Hooks
 *
 * Auto-revalidating data hooks for all terminal panels.
 */

import useSWR from 'swr';
import { marketAPI, companyAPI, feedAPI, earningsAPI, portfolioAPI } from './api';
import type { Quote, IndexQuote, NewsItem, SearchResult, CompanyDeepDive, EarningsItem, AlpacaPosition, AlpacaAccount, PortfolioHistory, ChartBar } from './api';

// ── Market Data Hooks ───────────────────────────────────────────────────────

export function useQuote(ticker: string | null) {
    return useSWR<Quote>(
        ticker ? `quote-${ticker}` : null,
        () => marketAPI.getQuote(ticker!),
        { refreshInterval: 30000, revalidateOnFocus: false }
    );
}

export function useBatchQuotes(tickers: string[]) {
    return useSWR<Quote[]>(
        tickers.length > 0 ? `batch-${tickers.join(',')}` : null,
        () => marketAPI.getBatchQuotes(tickers),
        { refreshInterval: 30000, revalidateOnFocus: false }
    );
}

export function useIndices() {
    return useSWR<IndexQuote[]>(
        'indices',
        () => marketAPI.getIndices(),
        { refreshInterval: 60000, revalidateOnFocus: false }
    );
}

export function useChart(ticker: string | null, period: string = '1M') {
    return useSWR<ChartBar[]>(
        ticker ? `chart-${ticker}-${period}` : null,
        () => marketAPI.getChart(ticker!, period),
        { refreshInterval: 300000, revalidateOnFocus: false }
    );
}

export function useTickerSearch(query: string) {
    return useSWR<SearchResult[]>(
        query.length >= 1 ? `search-${query}` : null,
        () => marketAPI.searchTicker(query),
        { revalidateOnFocus: false, dedupingInterval: 300 }
    );
}

// ── Company Hooks ───────────────────────────────────────────────────────────

export function useCompanyProfile(ticker: string | null) {
    return useSWR<CompanyDeepDive>(
        ticker ? `company-${ticker}` : null,
        () => companyAPI.getProfile(ticker!),
        { refreshInterval: 300000, revalidateOnFocus: false }
    );
}

// ── News Hooks ──────────────────────────────────────────────────────────────

export function useNewsFeed(ticker: string | null, limit: number = 20) {
    return useSWR<NewsItem[]>(
        ticker ? `news-${ticker}` : null,
        () => marketAPI.getNews(ticker!, limit),
        { refreshInterval: 30000, revalidateOnFocus: false }
    );
}

// ── Earnings Hooks ──────────────────────────────────────────────────────────

export function useEarningsCalendar(days: number = 14) {
    return useSWR<EarningsItem[]>(
        `earnings-${days}`,
        () => earningsAPI.getUpcoming(days),
        { refreshInterval: 300000, revalidateOnFocus: false }
    );
}

// ── Portfolio Hooks ─────────────────────────────────────────────────────────

export function useAlpacaAccount() {
    return useSWR<AlpacaAccount>(
        'alpaca-account',
        () => portfolioAPI.getAlpacaAccount(),
        { refreshInterval: 60000, revalidateOnFocus: false }
    );
}

export function useAlpacaPositions() {
    return useSWR<AlpacaPosition[]>(
        'alpaca-positions',
        () => portfolioAPI.getAlpacaPositions(),
        { refreshInterval: 30000, revalidateOnFocus: false }
    );
}

export function useAlpacaHistory(period: string = '1M') {
    return useSWR<PortfolioHistory>(
        `alpaca-history-${period}`,
        () => portfolioAPI.getAlpacaHistory(period),
        { refreshInterval: 300000, revalidateOnFocus: false }
    );
}
