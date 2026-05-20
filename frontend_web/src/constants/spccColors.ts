export const SPCC_COLORS = {
  green: { main: '#3B6D11', light: '#EAF3DE', text: '#27500A' },
  purple: { main: '#534AB7', light: '#EEEDFE', text: '#3C3489' },
  red: { main: '#A32D2D', light: '#FCEBEB', text: '#791F1F' },
  amber: { main: '#BA7517', light: '#FAEEDA', text: '#633806' },
  gray: { main: '#5F5E5A', light: '#F1EFE8', text: '#444441' },
  teal: { main: '#0F6E56', light: '#E1F5EE', text: '#085041' },
  blue: { main: '#0C447C', light: '#E6F1FB', text: '#0C447C' },
} as const;

export const EMOTION_LINE_COLORS = {
  cu_agent_score: SPCC_COLORS.green.main,
  op_agent_score: SPCC_COLORS.purple.main,
  cu_dissatisfied: '#E24B4A',
  cu_anger: SPCC_COLORS.red.main,
  cu_positive: SPCC_COLORS.teal.main,
} as const;

export const GRADE_COLORS: Record<
  'S' | 'A' | 'B' | 'C',
  { bg: string; text: string }
> = {
  S: { bg: SPCC_COLORS.green.light, text: SPCC_COLORS.green.text },
  A: { bg: SPCC_COLORS.blue.light, text: SPCC_COLORS.blue.text },
  B: { bg: SPCC_COLORS.amber.light, text: SPCC_COLORS.amber.text },
  C: { bg: SPCC_COLORS.red.light, text: SPCC_COLORS.red.text },
};
