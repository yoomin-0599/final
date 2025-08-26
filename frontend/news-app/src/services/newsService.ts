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

  // RSS 피드에서 뉴스 수집
  async collectNews(): Promise<Article[]> {
    const allArticles: Article[] = [];
    
    for (const feed of FEEDS.slice(0, 8)) { // 처음 8개 피드만 테스트
      try {
        const response = await fetch(`${RSS_TO_JSON_API}?rss_url=${encodeURIComponent(feed.feed_url)}`);
        const data = await response.json();
        
        if (data.status === 'ok' && data.items) {
          const articles = data.items.slice(0, 10).map((item: any) => ({
            id: this.nextId++,
            title: item.title,
            link: item.link,
            published: item.pubDate || new Date().toISOString(),
            source: feed.source,
            summary: this.cleanSummary(item.description || item.content || ''),
            keywords: this.extractKeywords(item.title + ' ' + (item.description || '')),
            is_favorite: false
          }));
          
          allArticles.push(...articles);
        }
      } catch (error) {
        console.warn(`Failed to fetch from ${feed.source}:`, error);
      }
    }

    this.articles = allArticles;
    return allArticles;
  }

  // 스트림릿의 키워드 추출 로직을 간소화해서 구현
  private extractKeywords(text: string): string[] {
    // 기술 관련 키워드 패턴
    const techKeywords = [
      'AI', '인공지능', '머신러닝', '딥러닝', 'ChatGPT', '로봇',
      '반도체', '메모리', 'DRAM', 'NAND', 'GPU', 'CPU',
      '5G', '6G', '클라우드', '데이터센터', '서버',
      '블록체인', '암호화폐', 'NFT', 'DeFi',
      '자율주행', '전기차', '배터리', '테슬라',
      '스타트업', '투자', '펀딩', '상장',
      '보안', '해킹', '취약점', '개인정보'
    ];

    const keywords: string[] = [];
    const textLower = text.toLowerCase();

    techKeywords.forEach(keyword => {
      if (textLower.includes(keyword.toLowerCase())) {
        keywords.push(keyword);
      }
    });

    // 추가로 대문자로 된 단어들 (회사명, 기술명 등) 추출
    const matches = text.match(/\b[A-Z][A-Za-z]{2,}\b/g);
    if (matches) {
      matches.forEach(match => {
        if (match.length > 2 && !keywords.includes(match)) {
          keywords.push(match);
        }
      });
    }

    return keywords.slice(0, 10); // 최대 10개
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