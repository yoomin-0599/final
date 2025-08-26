// 스트림릿 앱의 뉴스 수집 및 분석 기능을 React용으로 구현

export interface Article {
  id: number;
  title: string;
  link: string;
  published: string;
  source: string;
  summary?: string;
  keywords?: string[];
  is_favorite?: boolean;
}

export interface KeywordStats {
  keyword: string;
  count: number;
}

export interface NetworkNode {
  id: string;
  label: string;
  value: number;
}

export interface NetworkEdge {
  from: string;
  to: string;
  value: number;
}

// RSS 피드 소스 설정 (스트림릿 원본과 동일)
const FEEDS = [
  // Korean sources
  { feed_url: "https://it.donga.com/feeds/rss/", source: "IT동아", category: "IT", lang: "ko" },
  { feed_url: "https://rss.etnews.com/Section902.xml", source: "전자신문_속보", category: "IT", lang: "ko" },
  { feed_url: "https://zdnet.co.kr/news/news_xml.asp", source: "ZDNet Korea", category: "IT", lang: "ko" },
  { feed_url: "https://www.itworld.co.kr/rss/all.xml", source: "ITWorld Korea", category: "IT", lang: "ko" },
  { feed_url: "https://www.bloter.net/feed", source: "Bloter", category: "IT", lang: "ko" },
  { feed_url: "https://byline.network/feed/", source: "Byline Network", category: "IT", lang: "ko" },
  { feed_url: "https://platum.kr/feed", source: "Platum", category: "Startup", lang: "ko" },
  { feed_url: "https://www.boannews.com/media/news_rss.xml", source: "보안뉴스", category: "Security", lang: "ko" },
  
  // Global sources
  { feed_url: "https://techcrunch.com/feed/", source: "TechCrunch", category: "Tech", lang: "en" },
  { feed_url: "https://www.theverge.com/rss/index.xml", source: "The Verge", category: "Tech", lang: "en" },
  { feed_url: "https://venturebeat.com/category/ai/feed/", source: "VentureBeat AI", category: "AI", lang: "en" },
  { feed_url: "https://www.wired.com/feed/rss", source: "WIRED", category: "Tech", lang: "en" },
];

// 클라이언트 사이드에서 RSS를 직접 파싱할 수 없으므로, 
// RSS를 JSON으로 변환해주는 공개 API를 사용합니다
const RSS_TO_JSON_API = "https://api.rss2json.com/v1/api.json";

class NewsService {
  private articles: Article[] = [];
  private nextId = 1;
  private readonly STORAGE_KEY = 'news_articles';
  private readonly LAST_UPDATE_KEY = 'news_last_update';
  private readonly CACHE_DURATION = 30 * 60 * 1000; // 30분 캐시
  private autoRefreshInterval: number | null = null;

  constructor() {
    this.loadFromStorage();
    this.startAutoRefresh();
  }

  // 자동 새로고침 시작 (30분마다)
  private startAutoRefresh(): void {
    if (this.autoRefreshInterval) {
      clearInterval(this.autoRefreshInterval);
    }
    
    // 30분마다 백그라운드에서 자동 수집
    this.autoRefreshInterval = setInterval(async () => {
      if (!this.isCacheValid()) {
        console.log('🔄 자동 뉴스 업데이트 시작...');
        try {
          await this.collectNews(8); // 적은 수의 피드로 빠른 업데이트
          console.log('✅ 자동 뉴스 업데이트 완료');
        } catch (error) {
          console.warn('❌ 자동 뉴스 업데이트 실패:', error);
        }
      }
    }, this.CACHE_DURATION);
  }

  // 자동 새로고침 중지
  stopAutoRefresh(): void {
    if (this.autoRefreshInterval) {
      clearInterval(this.autoRefreshInterval);
      this.autoRefreshInterval = null;
    }
  }

  // 로컬스토리지에서 데이터 로드
  private loadFromStorage(): void {
    try {
      const storedArticles = localStorage.getItem(this.STORAGE_KEY);
      const lastUpdate = localStorage.getItem(this.LAST_UPDATE_KEY);
      
      if (storedArticles && lastUpdate) {
        const updateTime = parseInt(lastUpdate);
        const now = Date.now();
        
        // 캐시가 유효한 경우에만 로드
        if (now - updateTime < this.CACHE_DURATION) {
          this.articles = JSON.parse(storedArticles);
          this.nextId = Math.max(...this.articles.map(a => a.id), 0) + 1;
          console.log(`캐시에서 ${this.articles.length}개 기사 로드됨`);
          return;
        }
      }
    } catch (error) {
      console.warn('로컬스토리지 데이터 로드 실패:', error);
    }
  }

  // 로컬스토리지에 데이터 저장
  private saveToStorage(): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.articles));
      localStorage.setItem(this.LAST_UPDATE_KEY, Date.now().toString());
      console.log(`${this.articles.length}개 기사 캐시 저장 완료`);
    } catch (error) {
      console.warn('로컬스토리지 저장 실패:', error);
    }
  }

  // 캐시가 유효한지 확인
  isCacheValid(): boolean {
    const lastUpdate = localStorage.getItem(this.LAST_UPDATE_KEY);
    if (!lastUpdate) return false;
    
    const updateTime = parseInt(lastUpdate);
    const now = Date.now();
    return now - updateTime < this.CACHE_DURATION;
  }

  // RSS 피드에서 뉴스 수집 (개선된 버전)
  async collectNews(maxFeeds: number = 12): Promise<Article[]> {
    const allArticles: Article[] = [];
    const successfulFeeds: string[] = [];
    const failedFeeds: string[] = [];
    
    // 프로미스 배치 처리로 동시 수집
    const feedPromises = FEEDS.slice(0, maxFeeds).map(async (feed) => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10초 타임아웃
        
        const response = await fetch(
          `${RSS_TO_JSON_API}?rss_url=${encodeURIComponent(feed.feed_url)}&api_key=YOUR_API_KEY`, // API 키 추가 가능
          { 
            signal: controller.signal,
            headers: {
              'User-Agent': 'NewsIssue-WebApp/1.0'
            }
          }
        );
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'ok' && data.items && data.items.length > 0) {
          const articles = data.items.slice(0, 15).map((item: any) => ({
            id: this.nextId++,
            title: this.cleanTitle(item.title || ''),
            link: item.link || '',
            published: this.parseDate(item.pubDate) || new Date().toISOString(),
            source: feed.source,
            summary: this.cleanSummary(item.description || item.content || ''),
            keywords: this.extractKeywords(
              (item.title || '') + ' ' + 
              (item.description || '') + ' ' + 
              (item.categories?.join(' ') || '')
            ),
            is_favorite: false,
            category: feed.category,
            language: feed.lang
          }));
          
          successfulFeeds.push(feed.source);
          return articles;
        } else {
          throw new Error(`Invalid data structure: ${data.status || 'unknown'}`);
        }
      } catch (error) {
        failedFeeds.push(feed.source);
        console.warn(`❌ ${feed.source} 수집 실패:`, error instanceof Error ? error.message : error);
        return [];
      }
    });

    // 모든 피드 수집 완료까지 대기
    const results = await Promise.allSettled(feedPromises);
    
    results.forEach((result) => {
      if (result.status === 'fulfilled' && result.value.length > 0) {
        allArticles.push(...result.value);
      }
    });

    // 중복 제거 (URL 기준)
    const uniqueArticles = allArticles.filter((article, index, self) => 
      index === self.findIndex(a => a.link === article.link)
    );

    console.log(`📊 RSS 수집 완료: ${uniqueArticles.length}건 (성공: ${successfulFeeds.length}, 실패: ${failedFeeds.length})`);
    console.log(`✅ 성공 소스: ${successfulFeeds.join(', ')}`);
    if (failedFeeds.length > 0) {
      console.log(`❌ 실패 소스: ${failedFeeds.join(', ')}`);
    }

    this.articles = uniqueArticles;
    this.saveToStorage(); // 로컬스토리지에 저장
    return uniqueArticles;
  }

  // 제목 정리
  private cleanTitle(title: string): string {
    return title.replace(/&[^;]+;/g, ' ')
                .replace(/<[^>]*>/g, '')
                .replace(/\s+/g, ' ')
                .trim()
                .substring(0, 200);
  }

  // 날짜 파싱 개선
  private parseDate(dateStr: string): string | null {
    if (!dateStr) return null;
    
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return null;
      return date.toISOString();
    } catch {
      return null;
    }
  }

  // 한국어+영어 키워드 추출 (대폭 개선)
  private extractKeywords(text: string): string[] {
    if (!text) return [];
    
    const keywords: string[] = [];
    const textLower = text.toLowerCase();
    const cleanText = text.replace(/<[^>]*>/g, ' ').replace(/[^\w가-힣\s]/g, ' ');

    // 1. 기술 키워드 사전 (한국어+영어)
    const techKeywords = [
      // AI/ML
      'AI', '인공지능', 'Machine Learning', '머신러닝', 'Deep Learning', '딥러닝', 
      'ChatGPT', 'GPT', 'LLM', '생성형AI', 'Generative AI', '신경망', 'Neural Network',
      
      // 반도체/하드웨어  
      '반도체', 'Semiconductor', '메모리', 'Memory', 'DRAM', 'NAND', 'HBM', 
      'GPU', 'CPU', 'NPU', 'TPU', 'FPGA', 'ASIC', '칩셋', 'Chipset',
      '삼성전자', 'Samsung', 'SK하이닉스', 'TSMC', '엔비디아', 'NVIDIA',
      
      // 통신/네트워크
      '5G', '6G', 'LTE', '와이파이', 'WiFi', '블루투스', 'Bluetooth',
      '클라우드', 'Cloud', '데이터센터', 'Data Center', '서버', 'Server',
      '네트워크', 'Network', 'CDN', 'API', 'SDK',
      
      // 블록체인/핀테크
      '블록체인', 'Blockchain', '암호화폐', 'Cryptocurrency', 'Bitcoin', '비트코인',
      'Ethereum', '이더리움', 'NFT', 'DeFi', '메타버스', 'Metaverse',
      
      // 자동차/에너지
      '자율주행', 'Autonomous', '전기차', 'Electric Vehicle', 'EV', 'Tesla', '테슬라',
      '배터리', 'Battery', '리튬', 'Lithium', '수소', 'Hydrogen',
      
      // 기업/투자
      '스타트업', 'Startup', '유니콘', 'Unicorn', '투자', 'Investment', '펀딩', 'Funding',
      'IPO', '상장', '벤처캐피탈', 'VC', 'M&A', 'Apple', '애플', 'Google', '구글',
      'Microsoft', '마이크로소프트', 'Meta', '메타', 'Amazon', '아마존',
      
      // 보안/프라이버시
      '보안', 'Security', '해킹', 'Hacking', '사이버', 'Cyber', '랜섬웨어', 'Ransomware',
      '개인정보', 'Privacy', '데이터보호', 'GDPR', '제로트러스트', 'Zero Trust',
      
      // 소프트웨어/개발
      '오픈소스', 'Open Source', '개발자', 'Developer', '프로그래밍', 'Programming',
      'Python', 'JavaScript', 'React', 'Node.js', 'Docker', 'Kubernetes',
      'DevOps', 'CI/CD', '마이크로서비스', 'Microservices'
    ];

    // 2. 사전 키워드 매칭
    techKeywords.forEach(keyword => {
      const keywordLower = keyword.toLowerCase();
      if (textLower.includes(keywordLower) && !keywords.includes(keyword)) {
        keywords.push(keyword);
      }
    });

    // 3. 패턴 기반 추출
    const patterns = [
      // 대문자 약어 (AI, GPU, API 등)
      /\b[A-Z]{2,5}\b/g,
      // 회사명/브랜드명 패턴
      /\b[A-Z][a-z]+(?:[A-Z][a-z]*)*\b/g,
      // 한글 기술 용어 (2-6글자)
      /[가-힣]{2,6}(?:기술|시스템|플랫폼|서비스|솔루션)/g,
      // 숫자+단위 패턴 (5G, 128GB 등)
      /\b\d+[A-Za-z]{1,3}\b/g
    ];

    patterns.forEach(pattern => {
      const matches = cleanText.match(pattern);
      if (matches) {
        matches.forEach(match => {
          const trimmed = match.trim();
          if (trimmed.length >= 2 && 
              !keywords.includes(trimmed) && 
              !this.isCommonWord(trimmed)) {
            keywords.push(trimmed);
          }
        });
      }
    });

    // 4. 중복 제거 및 정렬 (빈도순)
    const uniqueKeywords = [...new Set(keywords)];
    
    // 5. 관련성 점수 계산 및 상위 키워드 선택
    const scoredKeywords = uniqueKeywords.map(keyword => ({
      keyword,
      score: this.calculateKeywordRelevance(keyword, text)
    })).sort((a, b) => b.score - a.score);

    return scoredKeywords.slice(0, 12).map(item => item.keyword);
  }

  // 일반적인 단어 필터
  private isCommonWord(word: string): boolean {
    const commonWords = new Set([
      'The', 'And', 'For', 'Are', 'But', 'Not', 'You', 'All', 'Can', 'Had', 'Her', 'Was', 'One', 'Our', 'Out', 'Day', 'Has', 'His', 'How', 'Man', 'New', 'Now', 'Old', 'See', 'Two', 'Way', 'Who', 'Boy', 'Did', 'Its', 'Let', 'Put', 'Say', 'She', 'Too', 'Use',
      '그는', '그의', '이는', '이를', '있는', '있다', '한다', '한국', '우리', '때문', '통해', '대한', '위해', '경우', '때문에', '이번', '지난', '올해', '내년'
    ]);
    return commonWords.has(word) || word.length < 2;
  }

  // 키워드 관련성 점수 계산
  private calculateKeywordRelevance(keyword: string, text: string): number {
    const keywordLower = keyword.toLowerCase();
    const textLower = text.toLowerCase();
    
    let score = 0;
    
    // 제목에 포함되면 가산점
    const titleEnd = Math.min(text.length, 100);
    if (text.substring(0, titleEnd).toLowerCase().includes(keywordLower)) {
      score += 3;
    }
    
    // 출현 빈도
    const occurrences = (textLower.match(new RegExp(keywordLower, 'g')) || []).length;
    score += occurrences;
    
    // 길이 보정 (너무 짧거나 긴 키워드 패널티)
    if (keyword.length >= 3 && keyword.length <= 10) {
      score += 1;
    }
    
    // 기술 용어 가산점
    if (/^[A-Z]{2,5}$/.test(keyword) || // 약어
        keyword.includes('AI') || keyword.includes('인공지능') ||
        keyword.includes('반도체') || keyword.includes('클라우드')) {
      score += 2;
    }
    
    return score;
  }

  // HTML 태그 제거 및 요약 정리
  private cleanSummary(html: string): string {
    const text = html.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, ' ');
    const sentences = text.split(/[.!?]/).filter(s => s.trim().length > 10);
    return sentences.slice(0, 2).join('. ').substring(0, 200) + '...';
  }

  // 키워드 통계 생성
  getKeywordStats(): KeywordStats[] {
    const keywordCount: { [key: string]: number } = {};
    
    this.articles.forEach(article => {
      article.keywords?.forEach(keyword => {
        keywordCount[keyword] = (keywordCount[keyword] || 0) + 1;
      });
    });

    return Object.entries(keywordCount)
      .map(([keyword, count]) => ({ keyword, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 30);
  }

  // 키워드 네트워크 데이터 생성
  getKeywordNetwork(): { nodes: NetworkNode[], edges: NetworkEdge[] } {
    const keywordStats = this.getKeywordStats();
    const topKeywords = keywordStats.slice(0, 15);
    
    const nodes: NetworkNode[] = topKeywords.map(stat => ({
      id: stat.keyword,
      label: stat.keyword,
      value: stat.count * 2
    }));

    const edges: NetworkEdge[] = [];
    const keywordPairs: { [key: string]: number } = {};

    // 같은 기사에 나타나는 키워드 쌍 찾기
    this.articles.forEach(article => {
      const keywords = article.keywords || [];
      for (let i = 0; i < keywords.length; i++) {
        for (let j = i + 1; j < keywords.length; j++) {
          const pair = [keywords[i], keywords[j]].sort().join('|');
          keywordPairs[pair] = (keywordPairs[pair] || 0) + 1;
        }
      }
    });

    // 상위 키워드들 간의 연결만 생성
    const topKeywordSet = new Set(topKeywords.map(k => k.keyword));
    Object.entries(keywordPairs)
      .filter(([_, count]) => count > 1)
      .slice(0, 20)
      .forEach(([pair, count]) => {
        const [from, to] = pair.split('|');
        if (topKeywordSet.has(from) && topKeywordSet.has(to)) {
          edges.push({ from, to, value: count });
        }
      });

    return { nodes, edges };
  }

  // 필터링된 기사 조회
  getFilteredArticles(filters: {
    search?: string;
    source?: string;
    dateFrom?: Date;
    dateTo?: Date;
    favoritesOnly?: boolean;
  }): Article[] {
    let filtered = [...this.articles];

    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(article => 
        article.title.toLowerCase().includes(searchLower) ||
        article.summary?.toLowerCase().includes(searchLower) ||
        article.keywords?.some(k => k.toLowerCase().includes(searchLower))
      );
    }

    if (filters.source && filters.source !== 'all') {
      filtered = filtered.filter(article => article.source === filters.source);
    }

    if (filters.dateFrom) {
      filtered = filtered.filter(article => 
        new Date(article.published) >= filters.dateFrom!
      );
    }

    if (filters.dateTo) {
      filtered = filtered.filter(article => 
        new Date(article.published) <= filters.dateTo!
      );
    }

    if (filters.favoritesOnly) {
      filtered = filtered.filter(article => article.is_favorite);
    }

    return filtered.sort((a, b) => 
      new Date(b.published).getTime() - new Date(a.published).getTime()
    );
  }

  // 즐겨찾기 토글
  toggleFavorite(articleId: number): void {
    const article = this.articles.find(a => a.id === articleId);
    if (article) {
      article.is_favorite = !article.is_favorite;
    }
  }

  // 모든 소스 목록 조회
  getSources(): string[] {
    const sources = [...new Set(this.articles.map(a => a.source))];
    return sources.sort();
  }

  // 통계 정보
  getStats() {
    const totalArticles = this.articles.length;
    const totalSources = new Set(this.articles.map(a => a.source)).size;
    const totalFavorites = this.articles.filter(a => a.is_favorite).length;
    
    // 최근 7일간 기사 수
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    const recentArticles = this.articles.filter(a => 
      new Date(a.published) >= weekAgo
    ).length;

    return {
      totalArticles,
      totalSources, 
      totalFavorites,
      recentArticles
    };
  }
}

export const newsService = new NewsService();