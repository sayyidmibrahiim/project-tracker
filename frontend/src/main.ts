import { mount } from "svelte";
import App from "./App.svelte";
import "./styles.css";

function start() {
  mount(App, { target: document.getElementById("app")! });
}

// DEV-only browser preview: `?preview` installs a mock pywebview bridge so the
// UI renders with sample data outside the desktop shell. Tree-shaken from the
// production build (guarded by import.meta.env.DEV).
if (import.meta.env.DEV && new URLSearchParams(window.location.search).has("preview")) {
  // Force a desktop-width viewport so phones render the full desktop layout
  // (the app targets a ~1540px desktop table; device-width would cram it).
  const vp = document.querySelector('meta[name="viewport"]');
  if (vp) vp.setAttribute("content", "width=1600, initial-scale=0.2");
  import("./lib/devMockBridge").then(({ installMockBridge }) => {
    installMockBridge();
    start();
  });
} else {
  start();
}
