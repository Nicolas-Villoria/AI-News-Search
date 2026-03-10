'use client';

import styles from './TabNavigation.module.css';

export type TabId = 'news' | 'overview' | 'earnings' | 'watchlist' | 'portfolio';

interface TabNavigationProps {
    activeTab: TabId;
    onTabChange: (tab: TabId) => void;
}

const TABS: { id: TabId; label: string }[] = [
    { id: 'news', label: 'NEWS' },
    { id: 'overview', label: 'OVERVIEW' },
    { id: 'earnings', label: 'EARNINGS' },
    { id: 'watchlist', label: 'WATCHLIST' },
    { id: 'portfolio', label: 'PORTFOLIO' },
];

export default function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
    return (
        <nav className={styles.tabs}>
            {TABS.map((tab) => (
                <button
                    key={tab.id}
                    className={`${styles.tab} ${activeTab === tab.id ? styles.active : ''}`}
                    onClick={() => onTabChange(tab.id)}
                >
                    {tab.label}
                </button>
            ))}
        </nav>
    );
}
