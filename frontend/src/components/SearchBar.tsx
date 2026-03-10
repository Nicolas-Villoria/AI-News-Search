'use client';

import { useState, useRef, useEffect } from 'react';
import { useTickerSearch } from '@/lib/hooks';
import styles from './SearchBar.module.css';

interface SearchBarProps {
    onSelectTicker: (ticker: string) => void;
}

export default function SearchBar({ onSelectTicker }: SearchBarProps) {
    const [query, setQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const { data: results } = useTickerSearch(query);
    const wrapperRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelect = (ticker: string) => {
        onSelectTicker(ticker);
        setQuery('');
        setIsOpen(false);
    };

    return (
        <div className={styles.wrapper} ref={wrapperRef}>
            <div className={styles.inputWrapper}>
                <span className={styles.icon}>⌕</span>
                <input
                    type="text"
                    className={styles.input}
                    placeholder="SEARCH TICKER..."
                    value={query}
                    onChange={(e) => {
                        setQuery(e.target.value.toUpperCase());
                        setIsOpen(true);
                    }}
                    onFocus={() => setIsOpen(true)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && results && results.length > 0) {
                            handleSelect(results[0].ticker);
                        }
                        if (e.key === 'Escape') {
                            setIsOpen(false);
                            setQuery('');
                        }
                    }}
                />
            </div>

            {isOpen && results && results.length > 0 && (
                <div className={styles.dropdown}>
                    {results.map((r) => (
                        <button
                            key={r.ticker}
                            className={styles.result}
                            onClick={() => handleSelect(r.ticker)}
                        >
                            <span className={styles.resultTicker}>{r.ticker}</span>
                            <span className={styles.resultName}>{r.name}</span>
                            <span className={styles.resultExchange}>{r.exchange}</span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
