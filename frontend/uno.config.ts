import { defineConfig, presetUno, presetIcons } from 'unocss'

export default defineConfig({
    presets: [
        presetUno(), // 提供與 Tailwind 完全兼容的語法
        presetIcons({
            scale: 1, // 預設圖示大小
            warn: true, // 找不到圖示時在終端機警告
            autoInstall: true, // 開啟自動安裝
        }),
    ],
    content: {
        pipeline: {
            include: [
                /\.(vue|svelte|[jt]sx|mdx?|astro|elm|php|phtml|html)($|\?)/,
                'src/router/**/*.{js,ts}'
            ]
        }
    }
})
