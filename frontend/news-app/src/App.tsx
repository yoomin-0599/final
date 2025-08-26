import React, { useState, useEffect, useRef } from 'react';
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
  Tooltip,
  Badge,
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
  DarkMode,
  LightMode,
  AccessTime,
  Keyboard,
  Visibility,
} from '@mui/icons-material';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import { newsService } from './services/newsService';
import type { Article, KeywordStats } from './services/newsService';
import { KeywordCloud } from './components/KeywordCloud';
import { KeywordNetwork } from './components/KeywordNetwork';
import { useThemeProvider } from './hooks/useTheme';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import { calculateReadingTime, formatReadingTime } from './utils/readingTime';


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

// 개별 기사 카드 컴포넌트 (개선된 디자인)
interface ArticleCardProps {
  article: Article;
  onToggleFavorite: (id: number) => void;
}

function ArticleCard({ article, onToggleFavorite }: ArticleCardProps) {
  const readingTime = calculateReadingTime((article.title || '') + (article.summary || ''));
  
  return (
    <Card sx={{ 
      mb: 2.5, 
      transition: 'all 0.3s ease-in-out', 
      '&:hover': { 
        transform: 'translateY(-2px)',
        boxShadow: '0 8px 25px rgba(0, 0, 0, 0.15)'
      },
      borderRadius: 3,
      overflow: 'hidden'
    }}>
      <CardContent sx={{ p: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={11}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ 
                  fontWeight: 700, 
                  mb: 1.5,
                  lineHeight: 1.4,
                  fontSize: { xs: '1.05rem', md: '1.15rem' }
                }}>
                  <a href={article.link} target="_blank" rel="noopener noreferrer" 
                     style={{ 
                       textDecoration: 'none', 
                       color: 'inherit'
                     }}>
                    {article.title}
                    <OpenInNew fontSize="small" sx={{ ml: 1, verticalAlign: 'middle', opacity: 0.7 }} />
                  </a>
                </Typography>
              </Box>
            </Box>
            
            <Stack direction="row" spacing={{ xs: 1, md: 2 }} sx={{ mb: 2, flexWrap: 'wrap', gap: 1 }}>
              <Chip
                icon={<ArticleIcon fontSize="small" />}
                label={article.source}
                variant="outlined"
                size="small"
                color="primary"
              />
              <Chip
                icon={<AccessTime fontSize="small" />}
                label={new Date(article.published).toLocaleDateString('ko-KR')}
                variant="outlined"
                size="small"
              />
              <Chip
                icon={<Visibility fontSize="small" />}
                label={formatReadingTime(readingTime)}
                variant="outlined"
                size="small"
                color="secondary"
              />
            </Stack>

            {article.summary && (
              <Typography variant="body1" sx={{ 
                mb: 2, 
                lineHeight: 1.7,
                color: 'text.secondary',
                fontSize: '0.95rem'
              }}>
                {article.summary.length > 200 
                  ? `${article.summary.substring(0, 200)}...` 
                  : article.summary}
              </Typography>
            )}

            {article.keywords && article.keywords.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" component="div" sx={{ mb: 1, fontWeight: 600 }}>
                  🏷️ 키워드
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {article.keywords.slice(0, 8).map((keyword, index) => (
                    <Chip 
                      key={index} 
                      label={keyword} 
                      size="small"
                      variant="outlined"
                      sx={{ 
                        fontSize: '0.75rem',
                        height: 24,
                        borderRadius: 3,
                        '&:hover': {
                          backgroundColor: 'primary.main',
                          color: 'primary.contrastText',
                          borderColor: 'primary.main'
                        }
                      }} 
                    />
                  ))}
                  {article.keywords.length > 8 && (
                    <Chip 
                      label={`+${article.keywords.length - 8}`}
                      size="small"
                      variant="filled"
                      color="default"
                      sx={{ fontSize: '0.75rem', height: 24 }}
                    />
                  )}
                </Box>
              </Box>
            )}
          </Grid>
          
          <Grid item xs={12} sm={1} sx={{ display: 'flex', justifyContent: { xs: 'flex-end', sm: 'center' } }}>
            <Stack spacing={1} alignItems="center">
              <Tooltip title={article.is_favorite ? '즐겨찾기 해제' : '즐겨찾기 추가'}>
                <IconButton 
                  onClick={() => onToggleFavorite(article.id)}
                  color={article.is_favorite ? "secondary" : "default"}
                  sx={{
                    transition: 'all 0.2s',
                    '&:hover': {
                      transform: 'scale(1.1)'
                    }
                  }}
                >
                  {article.is_favorite ? <Favorite /> : <FavoriteBorder />}
                </IconButton>
              </Tooltip>
              <Typography variant="caption" color="text.secondary">
                #{article.id}
              </Typography>
            </Stack>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

// 키보드 단축키 도움말 컴포넌트
function KeyboardShortcutsHelp() {
  return (
    <Paper sx={{ p: 2, mb: 2, bgcolor: 'action.hover' }}>
      <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
        ⌨️ 키보드 단축키
      </Typography>
      <Stack spacing={0.5}>
        <Typography variant="body2">• Ctrl/Cmd + R: 뉴스 새로고침</Typography>
        <Typography variant="body2">• Ctrl/Cmd + D: 다크모드 토글</Typography>
        <Typography variant="body2">• Ctrl/Cmd + K: 검색 포커스</Typography>
        <Typography variant="body2">• Ctrl/Cmd + ←/→: 탭 전환</Typography>
      </Stack>
    </Paper>
  );
}

// 메인 App 컴포넌트
export default function App() {
  const { isDarkMode, toggleTheme, theme, ThemeContext } = useThemeProvider();
  const [tabValue, setTabValue] = useState(0);
  const searchInputRef = useRef<HTMLInputElement>(null);
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
  
  // 사이드바 - 데스크톱에서는 항상 고정
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false);
  const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 1024);

  // 화면 크기 감지
  useEffect(() => {
    const handleResize = () => {
      const desktop = window.innerWidth >= 1024;
      setIsDesktop(desktop);
      // 데스크톱에서는 사이드바 항상 열기, 모바일에서는 기본으로 닫기
      if (desktop && !drawerOpen) {
        setDrawerOpen(true);
      } else if (!desktop && drawerOpen) {
        setDrawerOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // 초기 실행

    return () => window.removeEventListener('resize', handleResize);
  }, [drawerOpen]);

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

  // 검색 포커스
  const focusSearch = () => {
    searchInputRef.current?.focus();
  };

  // 키보드 단축키 설정
  useKeyboardShortcuts({
    onRefresh: collectNews,
    onToggleTheme: toggleTheme,
    onSearch: () => searchInputRef.current?.focus(),
    onNextTab: () => setTabValue(prev => (prev + 1) % 4),
    onPrevTab: () => setTabValue(prev => (prev - 1 + 4) % 4),
  });

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
    <ThemeContext.Provider value={{ isDarkMode, toggleTheme, theme }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
      
      {/* 상단 앱바 */}
      <AppBar position="fixed" sx={{ zIndex: theme => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h5" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            🗞️ 뉴스있슈~(News IT's Issue)
          </Typography>
          
          <Stack direction="row" spacing={1} sx={{ display: { xs: 'none', sm: 'flex' } }}>
            <Tooltip title="새로고침">
              <IconButton 
                color="inherit" 
                onClick={collectNews}
                disabled={collecting}
              >
                <Refresh />
              </IconButton>
            </Tooltip>
            
            <Tooltip title={isDesktop ? "사이드바 토글" : "필터 메뉴"}>
              <IconButton color="inherit" onClick={() => setDrawerOpen(!drawerOpen)}>
                <FilterList />
              </IconButton>
            </Tooltip>
          </Stack>
          
          {/* 모바일용 축약 버튼 */}
          <Stack direction="row" spacing={1} sx={{ display: { xs: 'flex', sm: 'none' } }}>
            <Tooltip title={isDarkMode ? '라이트 모드' : '다크 모드'}>
              <IconButton color="inherit" onClick={toggleTheme}>
                {isDarkMode ? <LightMode /> : <DarkMode />}
              </IconButton>
            </Tooltip>
            
            <Tooltip title="새로고침">
              <IconButton 
                color="inherit" 
                onClick={collectNews}
                disabled={collecting}
              >
                <Refresh />
              </IconButton>
            </Tooltip>
            
            <Tooltip title="필터 메뉴">
              <IconButton color="inherit" onClick={() => setDrawerOpen(!drawerOpen)}>
                <FilterList />
              </IconButton>
            </Tooltip>
          </Stack>
        </Toolbar>
      </AppBar>
      
      {/* 사이드바 (필터) */}
      <Drawer
        variant={isDesktop ? "persistent" : "temporary"}
        open={drawerOpen}
        onClose={() => !isDesktop && setDrawerOpen(false)}
        sx={{
          width: 300,
          flexShrink: 0,
          '& .MuiDrawer-paper': { 
            width: 300, 
            boxSizing: 'border-box', 
            pt: 8,
            ...(isDesktop && {
              position: 'fixed',
              height: '100vh',
            })
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          {showShortcutsHelp && <KeyboardShortcutsHelp />}
          
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
            inputRef={searchInputRef}
            label="키워드 검색"
            placeholder="예: AI, 반도체, 5G (Ctrl+K)"
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
          <Paper sx={{ 
            p: 2, 
            bgcolor: theme => theme.palette.mode === 'dark' ? 'grey.800' : 'grey.50',
            border: theme => theme.palette.mode === 'dark' ? '1px solid rgba(255, 255, 255, 0.12)' : 'none'
          }}>
            <Typography variant="body2" sx={{ 
              color: theme => theme.palette.mode === 'dark' ? 'grey.300' : 'text.primary'
            }}>
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
        p: { xs: 2, md: 3 }, 
        pt: { xs: 10, md: 12 },
        ml: (isDesktop && drawerOpen) ? '300px' : 0,
        transition: 'margin-left 0.3s',
        minHeight: '100vh'
      }}>
        <Typography variant="body1" sx={{ mb: 2, color: 'text.secondary' }}>
          **IT/공학 뉴스 수집, 분석, 시각화 대시보드**
        </Typography>

        {/* 탭 */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange}
            variant={isDesktop ? "standard" : "scrollable"}
            scrollButtons={isDesktop ? false : "auto"}
            sx={{
              '& .MuiTab-root': {
                minWidth: isDesktop ? 120 : 80,
                fontSize: { xs: '0.8rem', md: '0.875rem' }
              }
            }}
          >
            <Tab icon={<ArticleIcon />} label={isDesktop ? "📰 뉴스 목록" : "뉴스"} />
            <Tab icon={<Analytics />} label={isDesktop ? "📊 키워드 분석" : "분석"} />
            <Tab icon={<Cloud />} label={isDesktop ? "☁️ 워드클라우드" : "워드클라우드"} />
            <Tab icon={<Favorite />} label={isDesktop ? "⭐ 즐겨찾기" : "즐겨찾기"} />
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
    </ThemeContext.Provider>
  );
}