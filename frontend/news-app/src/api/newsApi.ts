import axios from 'axios';
import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Article {
  id: number;
  title: string;
  link: string;
  published: string;
  source: string;
  summary?: string;
  keywords?: string;
  created_at?: string;
  is_favorite: boolean;
}

export interface KeywordStats {
  keyword: string;
  count: number;
}

export interface NetworkData {
  nodes: Array<{
    id: string;
    label: string;
    value: number;
  }>;
  edges: Array<{
    from: string;
    to: string;
    value: number;
  }>;
}

export interface Stats {
  total_articles: number;
  total_sources: number;
  total_favorites: number;
  daily_counts: Array<{
    date: string;
    count: number;
  }>;
}

export const newsApi = {
  getArticles: async (params?: {
    limit?: number;
    offset?: number;
    source?: string;
    search?: string;
    favorites_only?: boolean;
  }) => {
    const response = await api.get<Article[]>('/api/articles', { params });
    return response.data;
  },

  getSources: async () => {
    const response = await api.get<string[]>('/api/sources');
    return response.data;
  },

  getKeywordStats: async (limit = 50) => {
    const response = await api.get<KeywordStats[]>('/api/keywords/stats', {
      params: { limit },
    });
    return response.data;
  },

  getKeywordNetwork: async (limit = 30) => {
    const response = await api.get<NetworkData>('/api/keywords/network', {
      params: { limit },
    });
    return response.data;
  },

  getFavorites: async () => {
    const response = await api.get<Article[]>('/api/favorites');
    return response.data;
  },

  addFavorite: async (articleId: number) => {
    const response = await api.post('/api/favorites/add', {
      article_id: articleId,
    });
    return response.data;
  },

  removeFavorite: async (articleId: number) => {
    const response = await api.delete(`/api/favorites/${articleId}`);
    return response.data;
  },

  getStats: async () => {
    const response = await api.get<Stats>('/api/stats');
    return response.data;
  },
};