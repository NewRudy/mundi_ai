import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { init } from '@mundi/ee';
import App from './App';

// Set Cesium Base URL to CDN to fix missing assets (Workers, etc.)
// This avoids the need for vite-plugin-cesium or manual asset copying
(window as any).CESIUM_BASE_URL = 'https://unpkg.com/cesium@1.122.0/Build/Cesium/';

init()
  .then(() => {
    createRoot(document.getElementById('root')!).render(
      <StrictMode>
        <App />
      </StrictMode>,
    );
  })
  .catch((e: unknown) => {
    // eslint-disable-next-line no-console
    console.error('[EE] init failed', e);
    const rootEl = document.getElementById('root')!;
    createRoot(rootEl).render(
      <StrictMode>
        <div style={{ padding: 24 }}>
          <h1>Initialization error</h1>
          <p>Authentication/EE initialization failed. Please refresh the page. If the issue persists, contact support.</p>
        </div>
      </StrictMode>,
    );
  });
