import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const dossierRacine = path.dirname(fileURLToPath(import.meta.url));

/** Évite le conflit ?vue= (onglet SPA) avec le query SFC du plugin Vue. */
function eviterConflitQueryVue() {
  return {
    name: "eviter-conflit-query-vue",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const url = req.url || "";
        if (
          /[?&]vue=/.test(url) &&
          !url.includes(".vue") &&
          !url.startsWith("/@") &&
          !url.startsWith("/src/") &&
          !url.startsWith("/node_modules/")
        ) {
          req.url = url.replace(/([?&])vue=/g, "$1onglet=");
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [eviterConflitQueryVue(), vue()],
  resolve: {
    alias: {
      "@": path.resolve(dossierRacine, "src"),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8001",
      "/photos": "http://127.0.0.1:8001",
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.js"],
  },
});
