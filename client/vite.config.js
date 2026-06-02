import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'node:path';
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: { '@': path.resolve(__dirname, 'src') }
    },
    server: {
        host: true,
        port: 80,
        strictPort: true,
        // Vite 6 blocks hosts other than the bind address by default. Allow any —
        // nginx is our trust boundary in this stack.
        allowedHosts: true,
        watch: { usePolling: true },
        hmr: { clientPort: 8080 }
    }
});
