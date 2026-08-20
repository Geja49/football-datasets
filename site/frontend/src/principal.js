import { createApp } from "vue";
import Application from "./Application.vue";
import routeur from "./routeur.js";
import "./styles.css";

createApp(Application).use(routeur).mount("#app");
