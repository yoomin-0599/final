import React, { useState, useEffect } from 'react';
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
  Tabs,
  Tab,
  IconButton,
  Grid,
  Container,
  AppBar,
  Toolbar,
  Drawer,
  Switch,
  FormControlLabel,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Pagination,
} from '@mui/material';
import {
  Article as ArticleIcon,
  Favorite,
  FavoriteBorder,
  Analytics,
  Cloud,
  Search,
  Refresh,
  FilterList,
  TrendingUp,
  OpenInNew,
} from '@mui/icons-material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import { newsService } from './services/newsService';
import type { Article, KeywordStats } from './services/newsService';
import { KeywordCloud } from './components/KeywordCloud';
import { KeywordNetwork } from './components/KeywordNetwork';

const theme = createTheme({
  palette: {
    primary: { main: '#1976d2' },
    secondary: { main: '#dc004e' },
    background: { default: '#f5f5f5', paper: '#ffffff' },
  },
  typography: {
    h4: { fontWeight: 600, marginBottom: '16px' },
    h5: { fontWeight: 500, marginBottom: '12px' },
    h6: { fontWeight: 500, marginBottom: '8px' },
  },
});

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

// 개별 기사 카드 컴포넌트 (스트림릿 스타일)
interface ArticleCardProps {
  article: Article;
  onToggleFavorite: (id: number) => void;
}

function ArticleCard({ article, onToggleFavorite }: ArticleCardProps) {
  return (
    <Card sx={{ mb: 2, transition: 'all 0.2s', '&:hover': { elevation: 4 } }}>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={11}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
              <a href={article.link} target="_blank" rel="noopener noreferrer" 
                 style={{ textDecoration: 'none', color: 'inherit' }}>
                {article.title}
                <OpenInNew fontSize="small" sx={{ ml: 0.5, verticalAlign: 'top' }} />
              </a>
            </Typography>
            
            <Stack direction="row" spacing={2} sx={{ mb: 1 }}>
              <Typography variant="body2" color="primary" fontWeight="bold">
                📰 {article.source}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                📅 {new Date(article.published).toLocaleString()}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                🔗 ID: {article.id}
              </Typography>
            </Stack>

            {article.summary && (
              <Typography variant="body2" sx={{ mb: 1, lineHeight: 1.6 }}>
                {article.summary}
              </Typography>
            )}

            {article.keywords && article.keywords.length > 0 && (
              <Box>
                <Typography variant="body2" component="span" fontWeight="bold">
                  🏷️ 키워드:{' '}
                </Typography>
                {article.keywords.slice(0, 10).map((keyword, index) => (
                  <Chip 
                    key={index} 
                    label={keyword} 
                    size="small" 
                    sx={{ mr: 0.5, mb: 0.5 }} 
                  />
                ))}
              </Box>
            )}
          </Grid>
          
          <Grid item xs={1}>
            <IconButton 
              onClick={() => onToggleFavorite(article.id)}
              color={article.is_favorite ? "secondary" : "default"}
            >
              {article.is_favorite ? <Favorite /> : <FavoriteBorder />}
            </IconButton>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

// 메인 App 컴포넌트
export default function App() {
  const [tabValue, setTabValue] = useState(0);
  const [articles, setArticles] = useState<Article[]>([]);
  const [filteredArticles, setFilteredArticles] = useState<Article[]>([]);
  const [keywordStats, setKeywordStats] = useState<KeywordStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [collecting, setCollecting] = useState(false);
  
  // 필터 상태
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [dateFrom, setDateFrom] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 7);
    return date.toISOString().split('T')[0];
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().split('T')[0]);
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  
  // 페이지네이션
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  
  // 사이드바
  const [drawerOpen, setDrawerOpen] = useState(false);

  // 초기 데이터 로드
  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      try {
        // 기존에 수집된 데이터가 있는지 확인
        const existingArticles = newsService.getFilteredArticles({});
        if (existingArticles.length === 0) {
          // 데이터가 없으면 자동으로 수집
          await collectNews();
        } else {
          setArticles(existingArticles);
          updateKeywordStats();
        }
      } catch (error) {
        console.error('Failed to load initial data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, []);

  // 필터 적용
  useEffect(() => {
    const filtered = newsService.getFilteredArticles({
      search: searchTerm,
      source: selectedSource === 'all' ? undefined : selectedSource,
      dateFrom: new Date(dateFrom),
      dateTo: new Date(dateTo),
      favoritesOnly,
    });
    setFilteredArticles(filtered);
    setCurrentPage(1);
  }, [articles, searchTerm, selectedSource, dateFrom, dateTo, favoritesOnly]);

  // 뉴스 수집
  const collectNews = async () => {
    setCollecting(true);
    try {
      const newArticles = await newsService.collectNews();
      setArticles(newArticles);
      updateKeywordStats();
    } catch (error) {
      console.error('Failed to collect news:', error);
    } finally {
      setCollecting(false);
    }
  };

  // 키워드 통계 업데이트
  const updateKeywordStats = () => {
    const stats = newsService.getKeywordStats();
    setKeywordStats(stats);
  };

  // 즐겨찾기 토글
  const handleToggleFavorite = (articleId: number) => {
    newsService.toggleFavorite(articleId);
    setArticles([...newsService.getFilteredArticles({})]);
  };

  // 탭 변경
  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // 페이지네이션 계산
  const totalPages = Math.ceil(filteredArticles.length / itemsPerPage);
  const currentArticles = filteredArticles.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // 소스 목록
  const sources = newsService.getSources();
  const stats = newsService.getStats();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      {/* 상단 앱바 */}
      <AppBar position="fixed" sx={{ zIndex: theme => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h5" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            🗞️ 뉴스있슈~(News IT's Issue)
          </Typography>
          <IconButton color="inherit" onClick={() => setDrawerOpen(!drawerOpen)}>
            <FilterList />
          </IconButton>
        </Toolbar>
      </AppBar>
      
      {/* 사이드바 (필터) */}
      <Drawer
        variant="persistent"
        open={drawerOpen}
        sx={{
          width: 300,
          flexShrink: 0,
          '& .MuiDrawer-paper': { width: 300, boxSizing: 'border-box', pt: 8 },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>🔧 필터링</Typography>
          
          {/* 뉴스 소스 */}
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>뉴스 소스</InputLabel>
            <Select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              label="뉴스 소스"
            >
              <MenuItem value="all">전체</MenuItem>
              {sources.map(source => (
                <MenuItem key={source} value={source}>{source}</MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* 키워드 검색 */}
          <TextField
            fullWidth
            label="키워드 검색"
            placeholder="예: AI, 반도체, 5G"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
            }}
          />

          {/* 기간 필터 */}
          <TextField
            fullWidth
            type="date"
            label="시작일"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            sx={{ mb: 2 }}
            InputLabelProps={{ shrink: true }}
          />
          
          <TextField
            fullWidth
            type="date"
            label="종료일"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            sx={{ mb: 2 }}
            InputLabelProps={{ shrink: true }}
          />

          {/* 즐겨찾기만 보기 */}
          <FormControlLabel
            control={
              <Switch
                checked={favoritesOnly}
                onChange={(e) => setFavoritesOnly(e.target.checked)}
              />
            }
            label="즐겨찾기만 보기"
            sx={{ mb: 2 }}
          />

          <Divider sx={{ my: 2 }} />
          
          {/* 데이터 관리 */}
          <Typography variant="h6" gutterBottom>📊 데이터 관리</Typography>
          
          <Button
            variant="contained"
            fullWidth
            startIcon={collecting ? <CircularProgress size={20} /> : <Refresh />}
            onClick={collectNews}
            disabled={collecting}
            sx={{ mb: 2 }}
          >
            {collecting ? '수집 중...' : '🔄 뉴스 수집'}
          </Button>

          {/* 통계 */}
          <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
            <Typography variant="body2">
              📊 총 {stats.totalArticles}건의 뉴스<br/>
              📰 {stats.totalSources}개 소스<br/>
              ⭐ {stats.totalFavorites}개 즐겨찾기<br/>
              📅 최근 7일: {stats.recentArticles}건
            </Typography>
          </Paper>
        </Box>
      </Drawer>

      {/* 메인 컨텐츠 */}
      <Box sx={{ 
        flexGrow: 1, 
        p: 3, 
        pt: 12,
        ml: drawerOpen ? '300px' : 0,
        transition: 'margin-left 0.3s'
      }}>
        <Typography variant="body1" sx={{ mb: 2, color: 'text.secondary' }}>
          **IT/공학 뉴스 수집, 분석, 시각화 대시보드**
        </Typography>

        {/* 탭 */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab icon={<ArticleIcon />} label="📰 뉴스 목록" />
            <Tab icon={<Analytics />} label="📊 키워드 분석" />
            <Tab icon={<Cloud />} label="☁️ 워드클라우드" />
            <Tab icon={<Favorite />} label="⭐ 즐겨찾기" />
          </Tabs>
        </Box>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* 뉴스 목록 탭 */}
        <TabPanel value={tabValue} index={0}>
          <Typography variant="h5" gutterBottom>📰 뉴스 목록</Typography>
          <Typography variant="body1" sx={{ mb: 2, fontWeight: 'bold' }}>
            **총 {filteredArticles.length}건의 뉴스**
          </Typography>

          {filteredArticles.length === 0 ? (
            <Alert severity="info">
              {articles.length === 0 ? 
                '데이터가 없습니다. 사이드바에서 "뉴스 수집" 버튼을 클릭하여 데이터를 수집하세요.' :
                '필터 조건에 맞는 뉴스가 없습니다.'
              }
            </Alert>
          ) : (
            <>
              {currentArticles.map(article => (
                <ArticleCard
                  key={article.id}
                  article={article}
                  onToggleFavorite={handleToggleFavorite}
                />
              ))}
              
              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                  <Pagination
                    count={totalPages}
                    page={currentPage}
                    onChange={(_, page) => setCurrentPage(page)}
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
        </TabPanel>

        {/* 키워드 분석 탭 */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h5" gutterBottom>📊 키워드 네트워크 분석</Typography>
          
          {keywordStats.length === 0 ? (
            <Alert severity="info">분석할 데이터가 없습니다.</Alert>
          ) : (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>🔥 인기 키워드 TOP 20</Typography>
                <Paper sx={{ p: 2, maxHeight: 400, overflow: 'auto' }}>
                  <List dense>
                    {keywordStats.slice(0, 20).map((stat, index) => (
                      <ListItem key={stat.keyword}>
                        <ListItemText
                          primary={`${index + 1}. ${stat.keyword}`}
                          secondary={`${stat.count}회`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>📈 키워드 분포</Typography>
                <Paper sx={{ p: 2, height: 400 }}>
                  {keywordStats.length > 0 && (
                    <KeywordCloud keywords={keywordStats.slice(0, 50)} />
                  )}
                </Paper>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>🕸️ 키워드 관계 네트워크</Typography>
                <Paper sx={{ p: 2, height: 500 }}>
                  <KeywordNetwork data={newsService.getKeywordNetwork()} />
                </Paper>
              </Grid>
            </Grid>
          )}
        </TabPanel>

        {/* 워드클라우드 탭 */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h5" gutterBottom>☁️ 워드클라우드</Typography>
          
          {keywordStats.length === 0 ? (
            <Alert severity="info">워드클라우드를 생성할 데이터가 없습니다.</Alert>
          ) : (
            <Paper sx={{ p: 2, height: 600 }}>
              <KeywordCloud keywords={keywordStats} />
            </Paper>
          )}
        </TabPanel>

        {/* 즐겨찾기 탭 */}
        <TabPanel value={tabValue} index={3}>
          <Typography variant="h5" gutterBottom>⭐ 즐겨찾기</Typography>
          
          {(() => {
            const favorites = articles.filter(a => a.is_favorite);
            return favorites.length === 0 ? (
              <Alert severity="info">즐겨찾기한 뉴스가 없습니다.</Alert>
            ) : (
              <>
                <Typography variant="body1" sx={{ mb: 2, fontWeight: 'bold' }}>
                  **총 {favorites.length}건의 즐겨찾기**
                </Typography>
                {favorites.map(article => (
                  <ArticleCard
                    key={article.id}
                    article={article}
                    onToggleFavorite={handleToggleFavorite}
                  />
                ))}
              </>
            );
          })()}
        </TabPanel>
      </Box>
    </ThemeProvider>
  );
}