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
} from '@mui/material';
import {
  Favorite,
  FavoriteBorder,
  OpenInNew,
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

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Typography gutterBottom variant="h6" component="h2">
          {article.title}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {article.source} | {new Date(article.published).toLocaleDateString()}
        </Typography>
        {article.summary && (
          <Typography variant="body2" paragraph>
            {article.summary}
          </Typography>
        )}
        {keywords.length > 0 && (
          <Box sx={{ mt: 2 }}>
            {keywords.slice(0, 5).map((keyword, index) => (
              <Chip
                key={index}
                label={keyword.trim()}
                size="small"
                sx={{ mr: 0.5, mb: 0.5 }}
              />
            ))}
          </Box>
        )}
      </CardContent>
      <CardActions>
        <IconButton
          onClick={() => onToggleFavorite(article)}
          color="error"
        >
          {article.is_favorite ? <Favorite /> : <FavoriteBorder />}
        </IconButton>
        <Button
          size="small"
          endIcon={<OpenInNew />}
          href={article.link}
          target="_blank"
          rel="noopener noreferrer"
        >
          원문 보기
        </Button>
      </CardActions>
    </Card>
  );
};