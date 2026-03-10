/**
 * Finhaus — API Client
 *
 * Centralized API client for communicating with the FastAPI backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

async function fetchAPI<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { params, ...fetchOpts } = options;

  let url = `${API_BASE_URL}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    });
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const response = await fetch(url, {
    ...fetchOpts,
    headers: {
      'Content-Type': 'application/json',
      ...fetchOpts.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// ── Market Data ──────────────────────────────────────────────────────────────

export const marketAPI = {
  getQuote: (ticker: string) =>
    fetchAPI<Quote>(`/market/quote/${ticker}`),

  getBatchQuotes: (tickers: string[]) =>
    fetchAPI<Quote[]>(`/market/quotes`, { params: { tickers: tickers.join(',') } }),

  getIndices: () =>
    fetchAPI<IndexQuote[]>(`/market/indices`),

  getChart: (ticker: string, period: string = '1M') =>
    fetchAPI<ChartBar[]>(`/market/chart/${ticker}`, { params: { period } }),

  searchTicker: (query: string, limit: number = 10) =>
    fetchAPI<SearchResult[]>(`/market/search`, { params: { q: query, limit } }),

  getProfile: (ticker: string) =>
    fetchAPI<CompanyProfile>(`/market/profile/${ticker}`),

  getNews: (ticker?: string, limit: number = 20) =>
    fetchAPI<NewsItem[]>(`/market/news`, { params: { ticker, limit } }),

  getEarningsCalendar: (fromDate?: string, toDate?: string) =>
    fetchAPI<EarningsItem[]>(`/market/earnings-calendar`, { params: { from_date: fromDate, to_date: toDate } }),
};

// ── Company ──────────────────────────────────────────────────────────────────

export const companyAPI = {
  getProfile: (ticker: string) =>
    fetchAPI<CompanyDeepDive>(`/company/${ticker}`),
};

// ── Feed ─────────────────────────────────────────────────────────────────────

export const feedAPI = {
  getFeed: (page: number = 1, pageSize: number = 20, sourceType?: string) =>
    fetchAPI<FeedResponse>(`/feed/`, { params: { page, page_size: pageSize, source_type: sourceType } }),

  getLiveNews: (ticker: string, limit: number = 20) =>
    fetchAPI<NewsItem[]>(`/feed/news/${ticker}`, { params: { limit } }),
};

// ── Earnings ─────────────────────────────────────────────────────────────────

export const earningsAPI = {
  getUpcoming: (days: number = 14) =>
    fetchAPI<EarningsItem[]>(`/earnings/upcoming`, { params: { days } }),
};

// ── Watchlist ────────────────────────────────────────────────────────────────

export const watchlistAPI = {
  getAll: () =>
    fetchAPI<WatchlistData[]>(`/watchlist/`),

  create: (name: string, tickers: string[] = []) =>
    fetchAPI<WatchlistData>(`/watchlist/`, { method: 'POST', body: JSON.stringify({ name, tickers }) }),

  addTicker: (watchlistId: number, ticker: string) =>
    fetchAPI(`/watchlist/${watchlistId}/tickers`, { method: 'POST', body: JSON.stringify({ ticker }) }),

  removeTicker: (watchlistId: number, ticker: string) =>
    fetchAPI(`/watchlist/${watchlistId}/tickers/${ticker}`, { method: 'DELETE' }),

  deleteWatchlist: (watchlistId: number) =>
    fetchAPI(`/watchlist/${watchlistId}`, { method: 'DELETE' }),
};

// ── Portfolio ────────────────────────────────────────────────────────────────

export const portfolioAPI = {
  getAlpacaStatus: () =>
    fetchAPI<AlpacaStatus>(`/portfolio/alpaca/status`),

  getAlpacaAccount: () =>
    fetchAPI<AlpacaAccount>(`/portfolio/alpaca/account`),

  getAlpacaPositions: () =>
    fetchAPI<AlpacaPosition[]>(`/portfolio/alpaca/positions`),

  getAlpacaHistory: (period: string = '1M', timeframe: string = '1D') =>
    fetchAPI<PortfolioHistory>(`/portfolio/alpaca/history`, { params: { period, timeframe } }),
};

// ── Types ────────────────────────────────────────────────────────────────────

export interface Quote {
  ticker: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  market_cap: number;
  day_high: number;
  day_low: number;
  year_high: number;
  year_low: number;
  open: number;
  prev_close: number;
  pe: number | null;
  eps: number | null;
  exchange: string;
  timestamp: number;
}

export interface IndexQuote {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
}

export interface ChartBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface SearchResult {
  ticker: string;
  name: string;
  exchange: string;
  type: string;
}

export interface CompanyProfile {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  description: string;
  logo_url: string;
  market_cap: number;
  exchange: string;
  website: string;
  ceo: string;
  employees: string;
  country: string;
  ipo_date: string;
}

export interface NewsItem {
  headline: string;
  summary: string;
  source: string;
  url: string;
  image_url: string;
  ticker: string;
  published_at: string;
}

export interface EarningsItem {
  ticker: string;
  company_name: string;
  report_date: string;
  fiscal_period: string;
  eps_estimate: number | null;
  revenue_estimate: number | null;
  eps_actual: number | null;
  revenue_actual: number | null;
  time: string;
}

export interface CompanyDeepDive {
  company: {
    id: number;
    ticker: string;
    name: string;
    sector: string;
    industry: string;
    market_cap: number;
    logo_url: string;
    description: string;
    exchange?: string;
    website?: string;
    ceo?: string;
    employees?: string;
    country?: string;
  };
  quote?: Quote;
  recent_earnings: unknown[];
  recent_ratings: unknown[];
  recent_news: NewsItem[];
  latest_intelligence: unknown[];
}

export interface FeedResponse {
  items: unknown[];
  total: number;
  page: number;
  page_size: number;
}

export interface WatchlistData {
  id: number;
  name: string;
  tickers: { ticker: string; name: string }[];
  created_at: string;
}

export interface AlpacaStatus {
  connected: boolean;
  message?: string;
  account_status?: string;
  equity?: number;
}

export interface AlpacaAccount {
  account_id: string;
  status: string;
  equity: number;
  buying_power: number;
  cash: number;
  portfolio_value: number;
  last_equity: number;
  long_market_value: number;
  currency: string;
}

export interface AlpacaPosition {
  ticker: string;
  qty: number;
  side: string;
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  cost_basis: number;
  unrealized_pl: number;
  unrealized_plpc: number;
  change_today: number;
}

export interface PortfolioHistory {
  timestamps: number[];
  equity: number[];
  profit_loss: number[];
  profit_loss_pct: number[];
  base_value: number;
  timeframe: string;
}
