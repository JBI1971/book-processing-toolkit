/**
 * API client for backend communication
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Works API
export const worksAPI = {
  list: async (search = '') => {
    const params = search ? { search } : {};
    const response = await apiClient.get('/works', { params });
    return response.data;
  },

  get: async (workId) => {
    const response = await apiClient.get(`/works/${workId}`);
    return response.data;
  },

  save: async (workId, bookData, commitMessage = '') => {
    const response = await apiClient.post(`/works/${workId}/save`, {
      book: bookData,
      commit_message: commitMessage,
    });
    return response.data;
  },

  updateChapter: async (workId, chapterId, updates) => {
    const response = await apiClient.put(
      `/works/${workId}/chapters/${chapterId}`,
      updates
    );
    return response.data;
  },

  reorderChapter: async (workId, chapterId, newPosition) => {
    const response = await apiClient.post(`/works/${workId}/reorder`, {
      chapter_id: chapterId,
      new_position: newPosition,
    });
    return response.data;
  },
};

// Translation API
export const translateAPI = {
  translate: async (text, sourceLang = 'zh', targetLang = 'en') => {
    const response = await apiClient.post('/translate', {
      text,
      source_lang: sourceLang,
      target_lang: targetLang,
    });
    return response.data;
  },
};

// Analysis API
export const analysisAPI = {
  startAnalysis: async (workId) => {
    const response = await apiClient.post(`/analyze/${workId}`);
    return response.data;
  },

  getStatus: async (workId) => {
    const response = await apiClient.get(`/analyze/${workId}/status`);
    return response.data;
  },

  getResult: async (workId) => {
    const response = await apiClient.get(`/analyze/${workId}`);
    return response.data;
  },
};

export default apiClient;
