import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import { viteSingleFile } from "vite-plugin-singlefile"
import path from "path"

// Builds ONE self-contained dist/index.html (JS + CSS inlined) so Python can inject fresh data into it daily.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  build: {
    target: "es2020",
    cssCodeSplit: false,
    assetsInlineLimit: 100000000,
    chunkSizeWarningLimit: 4000,
  },
})
