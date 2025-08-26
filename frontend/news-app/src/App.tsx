import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  AppBar,
  Toolbar,
  Tabs,
  Tab,
  Box,
  Grid,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Paper,
  Chip,
} from '@mui/material';
import {
  Article as ArticleIcon,
  Favorite,
  Analytics,
  Cloud,
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
  },
});

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function App() {
  const [tabValue, setTabValue] = useState(0);
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
    setLoading(true);
    setError(null);
    try {
      const data = await newsApi.getFavorites();
      setFavorites(data);
    } catch (err) {
      setError('즐겨찾기를 불러오는데 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(false);
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
      if (tabValue === 1) {
        loadFavorites();
      }
    } catch (err) {
      setError('즐겨찾기 업데이트에 실패했습니다.');
      console.error(err);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    if (newValue === 1) {
      loadFavorites();
    }
  };

  useEffect(() => {
    if (searchTerm !== '' || selectedSource !== '') {
      loadArticles();
    }
  }, [searchTerm, selectedSource]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            뉴스있슈~ (News IT's Issue)
          </Typography>
          {stats && (
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Chip
                icon={<ArticleIcon />}
                label={`총 ${stats.total_articles}개 기사`}
                color="primary"
                variant="outlined"
                sx={{ color: 'white', borderColor: 'white' }}
              />
              <Chip
                icon={<Favorite />}
                label={`즐겨찾기 ${stats.total_favorites}개`}
                color="primary"
                variant="outlined"
                sx={{ color: 'white', borderColor: 'white' }}
              />
            </Box>
          )}
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 3 }}>
        <Paper elevation={1}>
          <Tabs value={tabValue} onChange={handleTabChange} centered>
            <Tab icon={<ArticleIcon />} label="기사 목록" />
            <Tab icon={<Favorite />} label="즐겨찾기" />
            <Tab icon={<Cloud />} label="키워드 분석" />
            <Tab icon={<Analytics />} label="통계" />
          </Tabs>
        </Paper>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <TabPanel value={tabValue} index={0}>
          <Box sx={{ mb: 3 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="검색"
                  variant="outlined"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="제목, 요약, 키워드로 검색"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth variant="outlined">
                  <InputLabel>소스 필터</InputLabel>
                  <Select
                    value={selectedSource}
                    onChange={(e) => setSelectedSource(e.target.value)}
                    label="소스 필터"
                  >
                    <MenuItem value="">전체</MenuItem>
                    {sources.map((source) => (
                      <MenuItem key={source} value={source}>
                        {source}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </Box>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Grid container spacing={3}>
              {articles.map((article) => (
                <Grid item xs={12} md={6} lg={4} key={article.id}>
                  <ArticleCard
                    article={article}
                    onToggleFavorite={handleToggleFavorite}
                  />
                </Grid>
              ))}
            </Grid>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
              <CircularProgress />
            </Box>
          ) : favorites.length === 0 ? (
            <Typography variant="body1" sx={{ textAlign: 'center', p: 5 }}>
              즐겨찾기한 기사가 없습니다.
            </Typography>
          ) : (
            <Grid container spacing={3}>
              {favorites.map((article) => (
                <Grid item xs={12} md={6} lg={4} key={article.id}>
                  <ArticleCard
                    article={article}
                    onToggleFavorite={handleToggleFavorite}
                  />
                </Grid>
              ))}
            </Grid>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12} lg={6}>
              <KeywordCloud keywords={keywords} />
            </Grid>
            <Grid item xs={12} lg={6}>
              <KeywordNetwork data={networkData} />
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          {stats && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <StatsChart stats={stats} />
              </Grid>
              <Grid item xs={12}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    통계 요약
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        총 기사 수
                      </Typography>
                      <Typography variant="h4">
                        {stats.total_articles}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        소스 수
                      </Typography>
                      <Typography variant="h4">
                        {stats.total_sources}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        즐겨찾기 수
                      </Typography>
                      <Typography variant="h4">
                        {stats.total_favorites}
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            </Grid>
          )}
        </TabPanel>
      </Container>
    </ThemeProvider>
  );
}

export default App
