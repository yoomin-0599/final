import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import type { KeywordStats } from '../api/newsApi';

interface KeywordCloudProps {
  keywords: KeywordStats[];
}

export const KeywordCloud: React.FC<KeywordCloudProps> = ({ keywords }) => {
  const maxCount = Math.max(...keywords.map(k => k.count));
  const minCount = Math.min(...keywords.map(k => k.count));
  
  const getFontSize = (count: number) => {
    const normalized = (count - minCount) / (maxCount - minCount || 1);
    return 12 + normalized * 24; // 12px to 36px
  };

  const getOpacity = (count: number) => {
    const normalized = (count - minCount) / (maxCount - minCount || 1);
    return 0.5 + normalized * 0.5; // 0.5 to 1 opacity
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        키워드 클라우드
      </Typography>
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 2,
          justifyContent: 'center',
          p: 2,
        }}
      >
        {keywords.map((keyword, index) => (
          <Typography
            key={index}
            component="span"
            sx={{
              fontSize: `${getFontSize(keyword.count)}px`,
              opacity: getOpacity(keyword.count),
              fontWeight: keyword.count > (maxCount * 0.7) ? 'bold' : 'normal',
              color: 'primary.main',
              cursor: 'pointer',
              transition: 'all 0.3s',
              '&:hover': {
                transform: 'scale(1.1)',
                color: 'secondary.main',
              },
            }}
          >
            {keyword.keyword}
          </Typography>
        ))}
      </Box>
    </Paper>
  );
};