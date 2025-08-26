export const calculateReadingTime = (text: string): number => {
  // 한글: 평균 200자/분, 영어: 평균 250단어/분
  const koreanChars = (text.match(/[가-힣]/g) || []).length;
  const englishWords = (text.match(/[a-zA-Z]+/g) || []).length;
  const otherChars = text.length - koreanChars - englishWords;
  
  const koreanTime = koreanChars / 200;
  const englishTime = englishWords / 250;
  const otherTime = otherChars / 300;
  
  const totalMinutes = koreanTime + englishTime + otherTime;
  return Math.max(1, Math.ceil(totalMinutes));
};

export const formatReadingTime = (minutes: number): string => {
  return `${minutes}분 읽기`;
};
