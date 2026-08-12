import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import jsxA11y from 'eslint-plugin-jsx-a11y'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      // `configs.flat.recommended` EMAS: u eslint-plugin-react-hooks 5.2.0 da
      // mavjud emas va `undefined` bo'lgani uchun butun konfig yiqilardi
      // ("Cannot read properties of undefined"). Flat config uchun to'g'ri
      // kalit — 'recommended-latest'.
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
      // Accessibility — bu loyihaning ANIQ talabi.
      // Plugin JSX'dagi eng ko'p uchraydigan a11y xatolarini KOD YOZILAYOTGANDA
      // ushlaydi: yorliqsiz input, alt'siz rasm, onClick osilgan <div>,
      // klaviatura bilan yetib bo'lmaydigan element va h.k.
      jsxA11y.flatConfigs.recommended,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // `data-tip` — loyihaning o'z CSS tooltip'i. Uning YONIDA doim
      // aria-label bo'lishi kerak; plugin buni bilmaydi, shuning uchun
      // tekshiruvni o'zimiz qo'lda bajaramiz.
      'jsx-a11y/no-static-element-interactions': 'warn',
      'jsx-a11y/click-events-have-key-events': 'warn',
    },
  },
])
