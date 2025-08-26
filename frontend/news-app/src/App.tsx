import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  AppBar,
  Toolbar,
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Paper,
  Chip,
  Card,
  CardContent,
  Stack,
  Divider,
  Button,
} from '@mui/material';
import {
  Article as ArticleIcon,
  Favorite,
  Analytics,
  Cloud,
  Search,
  FilterList,
} from '@mui/icons-material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import { newsApi } from './api/newsApi';
import type { Article, KeywordStats, NetworkData, Stats } from './api/newsApi';
import { ArticleCard } from './components/ArticleCard';
import { KeywordCloud } from './components/KeywordCloud';
import { KeywordNetwork } from './components/KeywordNetwork';
import { StatsChart } from './components/StatsChart';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    h4: {
      fontWeight: 600,
      marginBottom: '16px',
    },
    h5: {
      fontWeight: 500,
      marginBottom: '12px',
    },
    h6: {
      fontWeight: 500,
      marginBottom: '8px',
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          transition: 'box-shadow 0.3s ease',
          '&:hover': {
            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
          },
        },
      },
    },
  },
});

// Streamlit-like sidebar component
interface SidebarProps {
  currentView: string;
  onViewChange: (view: string) => void;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  selectedSource: string;
  setSelectedSource: (source: string) => void;
  sources: string[];
  stats: Stats | null;
}

function Sidebar({ 
  currentView, 
  onViewChange, 
  searchTerm, 
  setSearchTerm, 
  selectedSource, 
  setSelectedSource, 
  sources, 
  stats 
}: SidebarProps) {
  const menuItems = [
    { id: 'articles', label: '기사 목록', icon: <ArticleIcon /> },
    { id: 'favorites', label: '즐겨찾기', icon: <Favorite /> },
    { id: 'keywords', label: '키워드 분석', icon: <Cloud /> },
    { id: 'stats', label: '통계', icon: <Analytics /> },
  ];

  return (
    <Paper 
      sx={{ 
        width: 320, 
        height: '100vh', 
        position: 'fixed', 
        left: 0, 
        top: 0, 
        borderRadius: 0,
        borderRight: '1px solid #e0e0e0',
        overflow: 'auto',
      }}
    >
      <Box sx={{ p: 3 }}>
        <Typography variant="h5" sx={{ mb: 3, fontWeight: 700, color: 'primary.main' }}>
          뉴스있슈~
        </Typography>
        
        {stats && (
          <Box sx={{ mb: 3 }}>
            <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
              <Chip 
                icon={<ArticleIcon fontSize="small" />} 
                label={`${stats.total_articles}개 기사`} 
                size="small"
                variant="outlined"
              />
              <Chip 
                icon={<Favorite fontSize="small" />} 
                label={`${stats.total_favorites}개 즐겨찾기`} 
                size="small"
                variant="outlined"
              />
            </Stack>
          </Box>
        )}

        <Divider sx={{ mb: 3 }} />

        {/* Navigation Menu */}
        <Stack spacing={1} sx={{ mb: 3 }}>
          {menuItems.map((item) => (
            <Button
              key={item.id}
              variant={currentView === item.id ? 'contained' : 'text'}
              startIcon={item.icon}
              onClick={() => onViewChange(item.id)}
              sx={{ 
                justifyContent: 'flex-start', 
                py: 1.5,
                borderRadius: 2,
                textTransform: 'none',
                fontSize: '14px',
              }}
              fullWidth
            >
              {item.label}
            </Button>
          ))}
        </Stack>

        <Divider sx={{ mb: 3 }} />

        {/* Search and Filter Controls */}
        <Typography variant="h6" sx={{ mb: 2 }}>
          <Search fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
          검색 및 필터
        </Typography>
        
        <Stack spacing={2}>
          <TextField
            size="small"
            label="검색어"
            variant="outlined"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="제목, 요약, 키워드로 검색"
            fullWidth
          />

          <FormControl size="small" variant="outlined" fullWidth>
            <InputLabel>뉴스 소스</InputLabel>
            <Select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              label="뉴스 소스"
            >
              <MenuItem value="">전체</MenuItem>
              {sources.map((source) => (
                <MenuItem key={source} value={source}>
                  {source}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>
      </Box>
    </Paper>
  );
}

function App() {
  const [currentView, setCurrentView] = useState('articles');
  const [articles, setArticles] = useState<Article[]>([]);
  const [favorites, setFavorites] = useState<Article[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [keywords, setKeywords] = useState<KeywordStats[]>([]);
  const [networkData, setNetworkData] = useState<NetworkData>({ nodes: [], edges: [] });
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSource, setSelectedSource] = useState<string>('');

  // Load initial data
  useEffect(() => {
    loadArticles();
    loadSources();
    loadKeywords();
    loadNetworkData();
    loadStats();
  }, []);

  const loadArticles = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await newsApi.getArticles({
        search: searchTerm || undefined,
        source: selectedSource || undefined,
        limit: 100,
      });
      setArticles(data);
    } catch (err) {
      setError('기사를 불러오는데 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadFavorites = async () => {
    try {
      const data = await newsApi.getFavorites();
      setFavorites(data);
    } catch (err) {
      setError('즐겨찾기를 불러오는데 실패했습니다.');
      console.error(err);
    }
  };

  const loadSources = async () => {
    try {
      const data = await newsApi.getSources();
      setSources(data);
    } catch (err) {
      console.error(err);
    }
  };

  const loadKeywords = async () => {
    try {
      const data = await newsApi.getKeywordStats(50);
      setKeywords(data);
    } catch (err) {
      console.error(err);
    }
  };

  const loadNetworkData = async () => {
    try {
      const data = await newsApi.getKeywordNetwork(30);
      setNetworkData(data);
    } catch (err) {
      console.error(err);
    }
  };

  const loadStats = async () => {
    try {
      const data = await newsApi.getStats();
      setStats(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleFavorite = async (article: Article) => {
    try {
      if (article.is_favorite) {
        await newsApi.removeFavorite(article.id);
      } else {
        await newsApi.addFavorite(article.id);
      }
      // Reload data
      loadArticles();
      if (currentView === 'favorites') {
        loadFavorites();
      }
    } catch (err) {
      setError('즐겨찾기 업데이트에 실패했습니다.');
      console.error(err);
    }
  };

  const handleViewChange = (view: string) => {
    setCurrentView(view);
    if (view === 'favorites') {
      loadFavorites();
    }
  };

  useEffect(() => {
    if (searchTerm !== '' || selectedSource !== '') {
      loadArticles();
    }
  }, [searchTerm, selectedSource]);

  const renderMainContent = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
          <CircularProgress size={48} />
        </Box>
      );
    }

    switch (currentView) {
      case 'articles':
        return (
          <Box>
            <Typography variant="h4" sx={{ mb: 3 }}>
              📰 기사 목록
            </Typography>
            
            {articles.length === 0 ? (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="h6" color="text.secondary">
                  검색 조건에 맞는 기사가 없습니다.
                </Typography>
              </Paper>
            ) : (
              <Stack spacing={2}>
                {articles.map((article) => (
                  <ArticleCard
                    key={article.id}
                    article={article}
                    onToggleFavorite={handleToggleFavorite}
                  />
                ))}
              </Stack>
            )}
          </Box>
        );

      case 'favorites':
        return (
          <Box>
            <Typography variant="h4" sx={{ mb: 3 }}>
              ⭐ 즐겨찾기
            </Typography>
            
            {favorites.length === 0 ? (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="h6" color="text.secondary">
                  즐겨찾기한 기사가 없습니다.
                </Typography>
              </Paper>
            ) : (
              <Stack spacing={2}>
                {favorites.map((article) => (
                  <ArticleCard
                    key={article.id}
                    article={article}
                    onToggleFavorite={handleToggleFavorite}
                  />
                ))}
              </Stack>
            )}
          </Box>
        );

      case 'keywords':
        return (
          <Box>
            <Typography variant="h4" sx={{ mb: 3 }}>
              🏷️ 키워드 분석
            </Typography>
            
            <Stack spacing={4}>
              <Card>
                <CardContent>
                  <KeywordCloud keywords={keywords} />
                </CardContent>
              </Card>
              
              <Card>
                <CardContent>
                  <KeywordNetwork data={networkData} />
                </CardContent>
              </Card>
            </Stack>
          </Box>
        );

      case 'stats':
        return (
          <Box>
            <Typography variant="h4" sx={{ mb: 3 }}>
              📊 통계
            </Typography>
            
            {stats && (
              <Stack spacing={4}>
                <Card>
                  <CardContent>
                    <StatsChart stats={stats} />
                  </CardContent>
                </Card>
                
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      📋 요약 통계
                    </Typography>
                    <Stack direction="row" spacing={4} sx={{ mt: 2 }}>
                      <Box textAlign="center">
                        <Typography variant="h3" color="primary.main" fontWeight="bold">
                          {stats.total_articles}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          총 기사 수
                        </Typography>
                      </Box>
                      <Box textAlign="center">
                        <Typography variant="h3" color="primary.main" fontWeight="bold">
                          {stats.total_sources}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          소스 수
                        </Typography>
                      </Box>
                      <Box textAlign="center">
                        <Typography variant="h3" color="secondary.main" fontWeight="bold">
                          {stats.total_favorites}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          즐겨찾기 수
                        </Typography>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              </Stack>
            )}
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      {/* Streamlit-style Layout */}
      <Box sx={{ display: 'flex', minHeight: '100vh' }}>
        {/* Sidebar */}
        <Sidebar
          currentView={currentView}
          onViewChange={handleViewChange}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          selectedSource={selectedSource}
          setSelectedSource={setSelectedSource}
          sources={sources}
          stats={stats}
        />

        {/* Main Content Area */}
        <Box 
          sx={{ 
            flex: 1, 
            ml: '320px', // Sidebar width
            p: 4,
            minHeight: '100vh',
            backgroundColor: 'background.default'
          }}
        >
          {error && (
            <Alert 
              severity="error" 
              sx={{ mb: 3 }} 
              onClose={() => setError(null)}
            >
              {error}
            </Alert>
          )}

          {renderMainContent()}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App
