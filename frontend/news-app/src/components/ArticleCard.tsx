import React from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  IconButton,
  Chip,
  Box,
  Stack,
  Divider,
} from '@mui/material';
import {
  Favorite,
  FavoriteBorder,
  OpenInNew,
  AccessTime,
  Source,
} from '@mui/icons-material';
import type { Article } from '../api/newsApi';

interface ArticleCardProps {
  article: Article;
  onToggleFavorite: (article: Article) => void;
}

export const ArticleCard: React.FC<ArticleCardProps> = ({
  article,
  onToggleFavorite,
}) => {
  const keywords = article.keywords?.split(',').filter(k => k.trim()) || [];
  const publishedDate = new Date(article.published);

  return (
    <Card 
      sx={{ 
        width: '100%',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: '0 8px 25px rgba(0,0,0,0.15)',
        }
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Stack spacing={2}>
          {/* Title */}
          <Typography variant="h6" component="h2" sx={{ 
            fontWeight: 600,
            lineHeight: 1.3,
            color: 'text.primary'
          }}>
            {article.title}
          </Typography>

          {/* Metadata */}
          <Stack direction="row" spacing={2} alignItems="center">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Source fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {article.source}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <AccessTime fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {publishedDate.toLocaleDateString('ko-KR')}
              </Typography>
            </Box>
          </Stack>

          {/* Summary */}
          {article.summary && (
            <>
              <Divider />
              <Typography 
                variant="body2" 
                sx={{ 
                  color: 'text.secondary',
                  lineHeight: 1.5,
                  fontSize: '14px'
                }}
              >
                {article.summary}
              </Typography>
            </>
          )}

          {/* Keywords */}
          {keywords.length > 0 && (
            <Box>
              <Stack direction="row" spacing={1} flexWrap="wrap" gap={0.5}>
                {keywords.slice(0, 6).map((keyword, index) => (
                  <Chip
                    key={index}
                    label={keyword.trim()}
                    size="small"
                    variant="outlined"
                    sx={{ 
                      fontSize: '11px',
                      height: '24px',
                      borderRadius: '12px',
                      '&:hover': {
                        backgroundColor: 'primary.main',
                        color: 'white',
                        borderColor: 'primary.main',
                      }
                    }}
                  />
                ))}
                {keywords.length > 6 && (
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                    +{keywords.length - 6}개 더
                  </Typography>
                )}
              </Stack>
            </Box>
          )}
        </Stack>
      </CardContent>
      
      <CardActions sx={{ px: 3, pb: 2, pt: 0, justifyContent: 'space-between' }}>
        <IconButton
          onClick={() => onToggleFavorite(article)}
          sx={{
            color: article.is_favorite ? 'error.main' : 'action.active',
            '&:hover': {
              backgroundColor: article.is_favorite ? 'error.light' : 'action.hover',
              color: article.is_favorite ? 'error.dark' : 'error.main',
            }
          }}
        >
          {article.is_favorite ? <Favorite /> : <FavoriteBorder />}
        </IconButton>
        
        <Button
          variant="contained"
          size="small"
          endIcon={<OpenInNew />}
          href={article.link}
          target="_blank"
          rel="noopener noreferrer"
          sx={{ 
            textTransform: 'none',
            borderRadius: 2,
            px: 2,
          }}
        >
          원문 보기
        </Button>
      </CardActions>
    </Card>
  );
};