import { defineConfig, presetUno, presetIcons } from 'unocss'

export default defineConfig({
    presets: [
        presetUno(), // 提供與 Tailwind 完全兼容的語法
        presetIcons({
            scale: 1.2, // 預設圖示大小
            warn: true, // 找不到圖示時在終端機警告
        }),
    ],
})
