/**
 * Entry point for the Blind Assistant Learning Platform.
 *
 * Audio-primary design: after any route change, focus moves to the <h1>
 * so screen readers announce the new page immediately without requiring
 * user navigation. All interactive elements have accessible names.
 *
 * HashRouter is used instead of BrowserRouter so the site works correctly
 * on GitHub Pages (and any static host) without server-side rewrite rules.
 * URLs become /#/course/getting-started etc. — still fully bookmarkable
 * and accessible; NVDA/VoiceOver read the page content, not the URL.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import App from './App';
import './styles/global.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element #root not found in index.html');
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>
);
