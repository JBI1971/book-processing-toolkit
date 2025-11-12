import { useState, useEffect } from 'react';
import { translateAPI } from '../api/client';

// Translation cache using localStorage
const CACHE_PREFIX = 'translation_cache_';
const CACHE_VERSION = 'v1';

function TranslateButton({ text, onTranslated }) {
  const [translated, setTranslated] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showTranslated, setShowTranslated] = useState(false);
  const [error, setError] = useState(null);

  // Generate cache key for this text
  const getCacheKey = (text) => {
    return `${CACHE_PREFIX}${CACHE_VERSION}_${btoa(encodeURIComponent(text))}`;
  };

  // Load cached translation on mount
  useEffect(() => {
    const cacheKey = getCacheKey(text);
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        const cachedData = JSON.parse(cached);
        setTranslated(cachedData.translation);
        // Notify parent if callback provided
        if (onTranslated) {
          onTranslated(cachedData.translation);
        }
      } catch (e) {
        // Invalid cache entry, ignore
        localStorage.removeItem(cacheKey);
      }
    }
  }, [text]);

  const handleTranslate = async () => {
    // If already translated, just toggle display
    if (translated) {
      setShowTranslated(!showTranslated);
      return;
    }

    // Otherwise, translate
    try {
      setLoading(true);
      setError(null);
      const result = await translateAPI.translate(text, 'zh', 'en');
      setTranslated(result.translated);
      setShowTranslated(true);

      // Save to localStorage for future use
      const cacheKey = getCacheKey(text);
      const cacheData = {
        translation: result.translated,
        timestamp: Date.now(),
        original: text
      };
      localStorage.setItem(cacheKey, JSON.stringify(cacheData));

      // Notify parent component if callback provided
      if (onTranslated) {
        onTranslated(result.translated);
      }
    } catch (err) {
      setError(err.message || 'Translation failed');
      console.error('Translation error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="translate-button-container">
      <button
        onClick={handleTranslate}
        disabled={loading}
        className="translate-button"
        title={translated ? (showTranslated ? 'Show original' : 'Show translation') : 'Translate'}
      >
        {loading ? '...' : (translated ? (showTranslated ? 'ZH' : 'EN') : '译')}
      </button>

      {error && (
        <span className="translate-error" title={error}>!</span>
      )}

      {showTranslated && translated && (
        <span className="translated-text">{translated}</span>
      )}
    </div>
  );
}

export default TranslateButton;
