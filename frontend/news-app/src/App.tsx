import { useState, useEffect } from 'react';
import {
  Typography,
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
  Collections,
  Download,
  Translate,
  SmartToy,
} from '@mui/icons-material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import { newsApi } from './api/newsApi';
import type { Article, KeywordStats, NetworkData, Stats, Collection } from './api/newsApi';
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
  dateFrom: string;
  setDateFrom: (date: string) => void;
  dateTo: string;
  setDateTo: (date: string) => void;
}

function Sidebar({ 
  currentView, 
  onViewChange, 
  searchTerm, 
  setSearchTerm, 
  selectedSource, 
  setSelectedSource, 
  sources, 
  stats,
  dateFrom,
  setDateFrom,
  dateTo,
  setDateTo
}: SidebarProps) {
  const menuItems = [
    { id: 'articles', label: '기사 목록', icon: <ArticleIcon /> },
    { id: 'favorites', label: '즐겨찾기', icon: <Favorite /> },
    { id: 'collections', label: '컬렉션', icon: <Collections /> },
    { id: 'keywords', label: '키워드 분석', icon: <Cloud /> },
    { id: 'stats', label: '통계', icon: <Analytics /> },
    { id: 'tools', label: '도구', icon: <SmartToy /> },
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

          <TextField
            size="small"
            label="시작 날짜"
            type="date"
            variant="outlined"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            fullWidth
            InputLabelProps={{ shrink: true }}
          />

          <TextField
            size="small"
            label="종료 날짜"
            type="date"
            variant="outlined"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            fullWidth
            InputLabelProps={{ shrink: true }}
          />
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
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSource, setSelectedSource] = useState<string>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Load initial data
  useEffect(() => {
    loadArticles();
    loadSources();
    loadKeywords();
    loadNetworkData();
    loadStats();
    loadCollections();
  }, []);

  const loadArticles = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await newsApi.getArticles({
        search: searchTerm || undefined,
        source: selectedSource || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
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

  const loadCollections = async () => {
    try {
      const data = await newsApi.getCollections();
      setCollections(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCollectNews = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await newsApi.collectNews(30, 5);
      setSuccess('뉴스 수집을 시작했습니다. 완료되면 새로고침하세요.');
    } catch (err) {
      setError('뉴스 수집에 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExtractKeywords = async (articleId: number) => {
    try {
      const result = await newsApi.extractKeywords(articleId);
      setSuccess(`키워드가 추출되었습니다: ${result.keywords.join(', ')}`);
      loadArticles(); // 새로고침
    } catch (err) {
      setError('키워드 추출에 실패했습니다.');
      console.error(err);
    }
  };

  const handleTranslateArticle = async (articleId: number) => {
    try {
      const result = await newsApi.translateArticle(articleId);
      setSuccess('번역이 완료되었습니다.');
      loadArticles(); // 새로고침
    } catch (err) {
      setError('번역에 실패했습니다.');
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
    } else if (view === 'collections') {
      loadCollections();
    }
  };

  useEffect(() => {
    if (searchTerm !== '' || selectedSource !== '' || dateFrom !== '' || dateTo !== '') {
      loadArticles();
    }
  }, [searchTerm, selectedSource, dateFrom, dateTo]);

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

      case 'collections':
        return (
          <Box>
            <Typography variant="h4" sx={{ mb: 3 }}>
              📁 테마별 컬렉션
            </Typography>
            
            {collections.length === 0 ? (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="h6" color="text.secondary">
                  컬렉션이 없습니다.
                </Typography>
              </Paper>
            ) : (
              <Stack spacing={3}>
                {collections.map((collection) => (
                  <Card key={collection.name}>
                    <CardContent>
                      <Typography variant="h5" gutterBottom>
                        {collection.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {collection.count}개 기사
                      </Typography>
                      
                      {collection.articles.length > 0 && (
                        <Stack spacing={1}>
                          {collection.articles.slice(0, 5).map((article: any) => (
                            <Box key={article.id} sx={{ p: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
                              <Typography variant="body2">{article.title}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {article.source} - {new Date(article.published).toLocaleDateString('ko-KR')}
                              </Typography>
                            </Box>
                          ))}
                          {collection.articles.length > 5 && (
                            <Typography variant="caption" color="text.secondary">
                              +{collection.articles.length - 5}개 더
                            </Typography>
                          )}
                        </Stack>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            )}
          </Box>
        );

      case 'tools':
        return (
          <Box>
            <Typography variant="h4" sx={{ mb: 3 }}>
              🛠️ 도구
            </Typography>
            
            <Stack spacing={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    <Download sx={{ mr: 1, verticalAlign: 'middle' }} />
                    뉴스 수집
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    RSS 피드에서 최신 뉴스를 수집합니다.
                  </Typography>
                  <Button 
                    variant="contained" 
                    onClick={handleCollectNews}
                    disabled={loading}
                  >
                    뉴스 수집 시작
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    <SmartToy sx={{ mr: 1, verticalAlign: 'middle' }} />
                    AI 분석 도구
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    기사의 키워드를 추출하고 번역합니다. (개별 기사에서 사용 가능)
                  </Typography>
                  <Stack direction="row" spacing={1}>
                    <Button variant="outlined" size="small">
                      키워드 추출
                    </Button>
                    <Button variant="outlined" size="small">
                      <Translate sx={{ mr: 0.5 }} fontSize="small" />
                      번역
                    </Button>
                  </Stack>
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
          dateFrom={dateFrom}
          setDateFrom={setDateFrom}
          dateTo={dateTo}
          setDateTo={setDateTo}
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

          {success && (
            <Alert 
              severity="success" 
              sx={{ mb: 3 }} 
              onClose={() => setSuccess(null)}
            >
              {success}
            </Alert>
          )}

          {renderMainContent()}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App