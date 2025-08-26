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

// RSS 피드 소스 설정 (실제 수집 가능한 소스 중심)
const FEEDS = [
  // 한국 소스 (실제 작동하는 RSS 피드)
  { feed_url: "https://www.bloter.net/feed", source: "Bloter", category: "IT", lang: "ko" },
  { feed_url: "https://byline.network/feed/", source: "Byline Network", category: "IT", lang: "ko" },
  { feed_url: "https://platum.kr/feed", source: "Platum", category: "Startup", lang: "ko" },
  { feed_url: "https://www.yna.co.kr/rss/technology.xml", source: "연합뉴스_기술", category: "Tech", lang: "ko" },
  { feed_url: "https://feeds.feedburner.com/hankyung-it", source: "한경_IT", category: "IT", lang: "ko" },
  { feed_url: "https://www.yonhapnews.co.kr/rss/tech.xml", source: "연합뉴스_과학IT", category: "Science", lang: "ko" },
  
  // 글로벌 소스 (안정적인 RSS 피드)
  { feed_url: "https://techcrunch.com/feed/", source: "TechCrunch", category: "Tech", lang: "en" },
  { feed_url: "https://www.theverge.com/rss/index.xml", source: "The Verge", category: "Tech", lang: "en" },
  { feed_url: "https://venturebeat.com/category/ai/feed/", source: "VentureBeat AI", category: "AI", lang: "en" },
  { feed_url: "https://www.wired.com/feed/rss", source: "WIRED", category: "Tech", lang: "en" },
  { feed_url: "https://feeds.feedburner.com/oreilly/radar", source: "O'Reilly Radar", category: "Tech", lang: "en" },
  { feed_url: "https://www.engadget.com/rss.xml", source: "Engadget", category: "Tech", lang: "en" },
  
  // 추가 안정 소스
  { feed_url: "https://rss.cnn.com/rss/edition_technology.rss", source: "CNN Tech", category: "Tech", lang: "en" },
  { feed_url: "https://feeds.bbci.co.uk/news/technology/rss.xml", source: "BBC Technology", category: "Tech", lang: "en" },
  { feed_url: "https://www.reuters.com/technology/feed/", source: "Reuters Tech", category: "Tech", lang: "en" },
];

// 다양한 RSS 파싱 API를 사용하여 안정성 향상
const RSS_APIS = [
  {
    name: "RSS2JSON",
    url: "https://api.rss2json.com/v1/api.json",
  },
  {
    name: "AllOrigins", 
    url: "https://api.allorigins.win/get",
  },
  {
    name: "ThingProxy",
    url: "https://thingproxy.freeboard.io/fetch",
  }
];

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

  // 향상된 RSS XML 파싱 (다양한 RSS 형식 지원)
  private parseRSSFromXML(xmlContent: string, source: string): any[] {
    try {
      const items: any[] = [];
      
      // RSS 2.0 및 Atom 피드 모두 지원
      const itemRegex = /<(?:item|entry)[^>]*>([\s\S]*?)<\/(?:item|entry)>/gi;
      const titleRegex = /<title[^>]*>(?:<!\[CDATA\[([^\]]+)\]\]>|([^<]+))<\/title>/i;
      const linkRegex = /<link[^>]*(?:href=["']([^"']+)["'])?[^>]*>([^<]*)<\/link>|<link[^>]*>([^<]+)<\/link>/i;
      const pubDateRegex = /<(?:pubDate|published|updated)[^>]*>([^<]+)<\/(?:pubDate|published|updated)>/i;
      const descRegex = /<(?:description|summary|content)[^>]*>(?:<!\[CDATA\[([^\]]+)\]\]>|([^<]+))<\/(?:description|summary|content)>/i;
      const guidRegex = /<guid[^>]*>([^<]+)<\/guid>/i;
      
      let match;
      let count = 0;
      while ((match = itemRegex.exec(xmlContent)) !== null && count < 15) {
        const itemContent = match[1];
        
        const titleMatch = titleRegex.exec(itemContent);
        const linkMatch = linkRegex.exec(itemContent);
        const pubDateMatch = pubDateRegex.exec(itemContent);
        const descMatch = descRegex.exec(itemContent);
        const guidMatch = guidRegex.exec(itemContent);
        
        if (titleMatch) {
          const title = (titleMatch[1] || titleMatch[2] || '').trim();
          let link = '';
          
          if (linkMatch) {
            link = (linkMatch[1] || linkMatch[2] || linkMatch[3] || '').trim();
          }
          
          // GUID를 링크로 사용 (링크가 없는 경우)
          if (!link && guidMatch) {
            const guid = guidMatch[1].trim();
            if (guid.startsWith('http')) {
              link = guid;
            }
          }
          
          const pubDate = pubDateMatch ? pubDateMatch[1].trim() : new Date().toISOString();
          const description = descMatch ? (descMatch[1] || descMatch[2] || '').trim() : '';
          
          if (title && (link || count === 0)) { // 최소한 제목은 있어야 함
            items.push({
              title: this.decodeHtmlEntities(title),
              link: link || `#${source}-${count}`,
              pubDate: pubDate,
              description: this.decodeHtmlEntities(description)
            });
            count++;
          }
        }
      }
      
      console.log(`${source}에서 ${items.length}개 아이템 파싱 성공`);
      return items;
    } catch (error) {
      console.warn(`${source} RSS XML 파싱 실패:`, error);
      return [];
    }
  }

  // HTML 엔티티 디코딩
  private decodeHtmlEntities(text: string): string {
    const textarea = document.createElement('textarea');
    textarea.innerHTML = text;
    return textarea.value;
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
        
        // 여러 API를 순차적으로 시도 (강화된 오류 처리)
        let articles: any[] = [];
        let lastError = null;
        
        for (let apiIndex = 0; apiIndex < RSS_APIS.length; apiIndex++) {
          const api = RSS_APIS[apiIndex];
          try {
            console.log(`🔄 ${feed.source}: ${api.name} API 시도 중...`);
            
            let response;
            let data;
            
            if (api.name === 'RSS2JSON') {
              response = await fetch(
                `${api.url}?rss_url=${encodeURIComponent(feed.feed_url)}&count=15&api_key=`,
                { 
                  signal: controller.signal,
                  headers: {
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (compatible; NewsAggregator/1.0)'
                  }
                }
              );
              
              if (response.ok) {
                data = await response.json();
                if (data.status === 'ok' && data.items && data.items.length > 0) {
                  articles = data.items.slice(0, 15);
                  break; // 성공시 루프 탈출
                }
              }
            } else if (api.name === 'AllOrigins') {
              response = await fetch(
                `${api.url}?url=${encodeURIComponent(feed.feed_url)}`,
                { 
                  signal: controller.signal,
                  headers: {
                    'Accept': 'application/json'
                  }
                }
              );
              
              if (response.ok) {
                data = await response.json();
                if (data.contents) {
                  articles = this.parseRSSFromXML(data.contents, feed.source);
                  if (articles.length > 0) break;
                }
              }
            } else if (api.name === 'ThingProxy') {
              response = await fetch(
                `${api.url}/${encodeURIComponent(feed.feed_url)}`,
                { 
                  signal: controller.signal,
                  headers: {
                    'Accept': 'text/xml,application/xml,application/rss+xml'
                  }
                }
              );
              
              if (response.ok) {
                const xmlText = await response.text();
                articles = this.parseRSSFromXML(xmlText, feed.source);
                if (articles.length > 0) break;
              }
            }
            
          } catch (apiError) {
            lastError = apiError;
            console.warn(`${api.name} API 실패 (${feed.source}):`, apiError instanceof Error ? apiError.message : apiError);
            continue; // 다음 API 시도
          }
        }
        
        clearTimeout(timeoutId);
        
        // 마지막으로 수집된 기사 수 확인
        
        if (articles && articles.length > 0) {
          const processedArticles = articles.map((item: any) => ({
            id: this.nextId++,
            title: this.cleanTitle(item.title || ''),
            link: item.link || item.url || '',
            published: this.parseDate(item.pubDate || item.published) || new Date().toISOString(),
            source: feed.source,
            summary: this.cleanSummary(item.description || item.content || ''),
            keywords: this.extractKeywords(
              (item.title || '') + ' ' + 
              (item.description || item.content || '') + ' ' + 
              (item.categories?.join(' ') || '')
            ),
            is_favorite: false,
            category: feed.category,
            language: feed.lang
          }));
          
          console.log(`✅ ${feed.source}: ${processedArticles.length}개 기사 수집 성공`);
          successfulFeeds.push(feed.source);
          return processedArticles;
        } else {
          console.warn(`${feed.source}: 모든 API에서 데이터 수집 실패`);
          throw new Error(`No valid data from ${feed.source}`);
        }
      } catch (error) {
        failedFeeds.push(feed.source);
        const errorMsg = error instanceof Error ? error.message : String(error);
        console.warn(`❌ ${feed.source} 전체 실패:`, errorMsg);
        
        // 에러 유형 분류
        if (errorMsg.includes('CORS') || errorMsg.includes('blocked')) {
          console.warn(`🔄 ${feed.source}: CORS 정책으로 인한 차단`);
        } else if (errorMsg.includes('timeout') || errorMsg.includes('aborted')) {
          console.warn(`⏱️ ${feed.source}: 요청 시간 초과`);
        } else if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
          console.warn(`🌐 ${feed.source}: 네트워크 연결 오류`);
        }
        
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

    // 수집된 기사가 너무 적을 경우 샘플 데이터 추가
    if (uniqueArticles.length < 3) {
      console.log('⚠️ 수집된 기사가 부족하여 샘플 데이터를 추가합니다.');
      const sampleData = this.generateSampleData();
      uniqueArticles.push(...sampleData);
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
  
  // 샘플 데이터 생성 (RSS 수집이 실패할 경우 대비용)
  private generateSampleData(): Article[] {
    const sampleArticles = [
      {
        id: this.nextId++,
        title: "AI 기술의 새로운 돌파구, GPT-4 성능 향상 발표",
        link: "#sample-1",
        published: new Date(Date.now() - 3600000).toISOString(),
        source: "IT뉴스 샘플",
        summary: "최신 AI 모델의 성능 개선과 새로운 기능들이 발표되었습니다. 자연어 처리 능력이 크게 향상되었으며, 다양한 분야에서의 활용 가능성이 확대되고 있습니다.",
        keywords: ["AI", "GPT-4", "자연어처리", "인공지능", "기술발전"],
        is_favorite: false
      },
      {
        id: this.nextId++,
        title: "5G 네트워크 확산으로 IoT 시장 급성장 전망",
        link: "#sample-2",
        published: new Date(Date.now() - 7200000).toISOString(),
        source: "테크 샘플",
        summary: "5G 네트워크의 본격적인 상용화와 함께 IoT(사물인터넷) 시장이 급속도로 성장하고 있습니다. 스마트 시티, 자율주행차, 산업용 IoT 등 다양한 분야에서 혁신이 일어나고 있습니다.",
        keywords: ["5G", "IoT", "스마트시티", "자율주행", "네트워크"],
        is_favorite: false
      },
      {
        id: this.nextId++,
        title: "메타버스 플랫폼, 엔터프라이즈 시장 진출 가속화",
        link: "#sample-3",
        published: new Date(Date.now() - 10800000).toISOString(),
        source: "VR뉴스 샘플",
        summary: "메타버스 기술이 게임과 엔터테인먼트를 넘어 기업용 솔루션으로 확산되고 있습니다. 원격 회의, 교육 훈련, 제품 시연 등 다양한 비즈니스 활용 사례가 늘어나고 있습니다.",
        keywords: ["메타버스", "VR", "AR", "원격회의", "엔터프라이즈"],
        is_favorite: false
      },
      {
        id: this.nextId++,
        title: "양자 컴퓨팅 상용화 앞당기는 새로운 알고리즘 개발",
        link: "#sample-4",
        published: new Date(Date.now() - 14400000).toISOString(),
        source: "과학기술 샘플",
        summary: "양자 컴퓨팅의 상용화를 앞당길 수 있는 새로운 양자 알고리즘이 개발되었습니다. 기존 컴퓨터로는 해결하기 어려운 복잡한 문제들을 효율적으로 처리할 수 있을 것으로 기대됩니다.",
        keywords: ["양자컴퓨팅", "양자알고리즘", "슈퍼컴퓨터", "과학기술", "혁신"],
        is_favorite: false
      },
      {
        id: this.nextId++,
        title: "블록체인 기반 디지털 신원인증 시스템 도입 확대",
        link: "#sample-5",
        published: new Date(Date.now() - 18000000).toISOString(),
        source: "블록체인 샘플",
        summary: "블록체인 기술을 활용한 디지털 신원인증 시스템이 금융, 의료, 교육 등 다양한 분야에서 도입되고 있습니다. 개인정보 보호와 보안성을 크게 향상시킬 것으로 예상됩니다.",
        keywords: ["블록체인", "디지털신원", "보안", "개인정보보호", "핀테크"],
        is_favorite: false
      }
    ];
    
    return sampleArticles;
  }
}

export const newsService = new NewsService();