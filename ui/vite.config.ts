import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return;
          }

          if (id.includes("@ionic") || id.includes("ionicons")) {
            return "ionic-vendor";
          }

          if (id.includes("@tanstack")) {
            return "query-vendor";
          }

          if (
            id.includes("react") ||
            id.includes("scheduler") ||
            id.includes("history")
          ) {
            return "react-vendor";
          }
        },
      },
    },
  },
});
