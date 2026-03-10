'use client';

import { useState, useCallback } from 'react';
import TopBar from '@/components/TopBar';
import TickerStrip from '@/components/TickerStrip';
import SearchBar from '@/components/SearchBar';
import TabNavigation, { TabId } from '@/components/TabNavigation';
import BottomBar from '@/components/BottomBar';
import NewsFeedPanel from '@/components/panels/NewsFeedPanel';
import OverviewPanel from '@/components/panels/OverviewPanel';
import EarningsPanel from '@/components/panels/EarningsPanel';
import WatchlistPanel from '@/components/panels/WatchlistPanel';
import PortfolioPanel from '@/components/panels/PortfolioPanel';

const DEFAULT_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'JPM', 'V', 'WMT'];

export default function Home() {
  const [selectedTicker, setSelectedTicker] = useState<string>('AAPL');
  const [activeTab, setActiveTab] = useState<TabId>('news');
  const [watchlistTickers, setWatchlistTickers] = useState<string[]>(DEFAULT_TICKERS);

  const handleSelectTicker = useCallback((ticker: string) => {
    setSelectedTicker(ticker);
    // Auto-switch to news tab when clicking a ticker
    if (activeTab === 'watchlist' || activeTab === 'portfolio') {
      // Don't switch from these tabs
    } else {
      setActiveTab('news');
    }
  }, [activeTab]);

  const handleAddTicker = useCallback((ticker: string) => {
    setWatchlistTickers((prev) => {
      if (prev.includes(ticker)) return prev;
      return [...prev, ticker];
    });
  }, []);

  const handleRemoveTicker = useCallback((ticker: string) => {
    setWatchlistTickers((prev) => prev.filter((t) => t !== ticker));
  }, []);

  const renderPanel = () => {
    switch (activeTab) {
      case 'news':
        return <NewsFeedPanel ticker={selectedTicker} />;
      case 'overview':
        return <OverviewPanel ticker={selectedTicker} />;
      case 'earnings':
        return <EarningsPanel />;
      case 'watchlist':
        return (
          <WatchlistPanel
            tickers={watchlistTickers}
            onAddTicker={handleAddTicker}
            onRemoveTicker={handleRemoveTicker}
          />
        );
      case 'portfolio':
        return <PortfolioPanel />;
      default:
        return <NewsFeedPanel ticker={selectedTicker} />;
    }
  };

  return (
    <div className="app-shell">
      <TopBar selectedTicker={selectedTicker} />

      <div style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid var(--border-light)' }}>
        <div style={{ padding: '0 var(--space-lg)' }}>
          <SearchBar onSelectTicker={(t) => {
            handleSelectTicker(t);
            handleAddTicker(t);
          }} />
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <TickerStrip
            tickers={watchlistTickers}
            selectedTicker={selectedTicker}
            onSelectTicker={handleSelectTicker}
          />
        </div>
      </div>

      <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="main-content">
        {renderPanel()}
      </main>

      <BottomBar />
    </div>
  );
}
