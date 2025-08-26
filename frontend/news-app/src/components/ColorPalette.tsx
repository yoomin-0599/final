import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  Chip,
  Stack,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';

export const ColorPalette: React.FC = () => {
  const theme = useTheme();

  const ColorCard = ({ title, colors, description }: {
    title: string;
    colors: { name: string; value: string; textColor?: string }[];
    description?: string;
  }) => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        {description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {description}
          </Typography>
        )}
        <Grid container spacing={1}>
          {colors.map((color) => (
            <Grid item xs={6} sm={4} md={3} key={color.name}>
              <Box
                sx={{
                  backgroundColor: color.value,
                  height: 80,
                  borderRadius: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  border: '1px solid',
                  borderColor: 'divider',
                  position: 'relative',
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    color: color.textColor || (theme.palette.mode === 'dark' ? '#fff' : '#000'),
                    fontWeight: 600,
                    textAlign: 'center',
                  }}
                >
                  {color.name}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    color: color.textColor || (theme.palette.mode === 'dark' ? '#fff' : '#000'),
                    fontSize: '0.6rem',
                    opacity: 0.8,
                  }}
                >
                  {color.value}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );

  const primaryColors = [
    { name: 'Primary', value: theme.palette.primary.main, textColor: '#fff' },
    { name: 'Primary Light', value: theme.palette.primary.light, textColor: '#fff' },
    { name: 'Primary Dark', value: theme.palette.primary.dark, textColor: '#fff' },
  ];

  const secondaryColors = [
    { name: 'Secondary', value: theme.palette.secondary.main, textColor: '#fff' },
    { name: 'Secondary Light', value: theme.palette.secondary.light, textColor: '#fff' },
    { name: 'Secondary Dark', value: theme.palette.secondary.dark, textColor: '#fff' },
  ];

  const backgroundColors = [
    { name: 'Default', value: theme.palette.background.default },
    { name: 'Paper', value: theme.palette.background.paper },
  ];

  const textColors = [
    { name: 'Primary Text', value: theme.palette.text.primary },
    { name: 'Secondary Text', value: theme.palette.text.secondary },
  ];

  // Custom colors from our enhanced theme
  const customColors = [
    { name: 'Accent', value: (theme.palette as any).accent?.main || '#059669', textColor: '#fff' },
    { name: 'Surface Primary', value: (theme.palette as any).surface?.primary || 'rgba(37, 99, 235, 0.08)' },
    { name: 'Surface Secondary', value: (theme.palette as any).surface?.secondary || 'rgba(220, 38, 38, 0.08)' },
    { name: 'Surface Accent', value: (theme.palette as any).surface?.accent || 'rgba(5, 150, 105, 0.08)' },
  ];

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        🎨 컬러 팔레트
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        현재 적용된 {theme.palette.mode === 'dark' ? '다크' : '라이트'} 테마의 컬러 팔레트입니다.
      </Typography>

      <Stack spacing={1} sx={{ mb: 3 }}>
        <Chip 
          label={`현재 모드: ${theme.palette.mode === 'dark' ? '다크 모드' : '라이트 모드'}`}
          color="primary"
          variant="filled"
        />
        <Chip 
          label={`테마 업데이트: ${new Date().toLocaleString()}`}
          variant="outlined"
        />
      </Stack>

      <ColorCard
        title="🔥 Primary Colors"
        description="주요 브랜드 색상으로 버튼, 링크 등에 사용됩니다."
        colors={primaryColors}
      />

      <ColorCard
        title="💖 Secondary Colors"
        description="보조 색상으로 강조 요소에 사용됩니다."
        colors={secondaryColors}
      />

      <ColorCard
        title="🌟 Custom Colors"
        description="사용자 정의 색상으로 특별한 UI 요소에 사용됩니다."
        colors={customColors}
      />

      <ColorCard
        title="📄 Background Colors"
        description="배경색으로 전체적인 톤을 설정합니다."
        colors={backgroundColors}
      />

      <ColorCard
        title="📝 Text Colors"
        description="텍스트 색상으로 가독성을 보장합니다."
        colors={textColors}
      />

      {/* Theme Details */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            🔧 테마 세부 정보
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                <strong>폰트 패밀리:</strong> {theme.typography.fontFamily}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                <strong>기본 반경:</strong> {theme.shape.borderRadius}px
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                <strong>모드:</strong> {theme.palette.mode}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                <strong>Spacing Unit:</strong> {theme.spacing(1)}px
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Paper>
  );
};